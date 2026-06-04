# ⚠️ ANALISI: Stop Session con Trade Aperto

## 🔍 Cosa Succede Attualmente (COMPORTAMENTO ANALIZZATO)

Quando clicchi **STOP** con un trade aperto:

### 1. Backend (`POST /session` action="stop")
```python
elif action == "stop":
    # 1. Stop BinanceWSClient and pipeline
    asyncio.create_task(_stop_ws_broadcast(), name="scalping-ws-stop")
    
    # 2. Stop SupervisorScheduler
    if "supervisor_scheduler" in _execution_state:
        _execution_state["supervisor_scheduler"].stop()
        _execution_state["supervisor_scheduler"] = None
    
    # 3. Reset session state
    session["status"] = "idle"
    session["session_id"] = None
    session["started_at"] = None
    session["stopped_at"] = _now()
    
    # 4. Update DB
    supabase.table("scalping_sessions").update({
        "status": "stopped",
        "stopped_at": session["stopped_at"]
    }).eq("id", db_sid).execute()
```

### 2. _stop_ws_broadcast() Cleanup
```python
async def _stop_ws_broadcast():
    # Stop Binance WS client
    client.stop()
    _execution_state["ws_client"] = None
    
    # Stop execution loop
    loop.stop()
    _execution_state["loop"] = None
    
    # Stop signal engine
    _execution_state["signal_engine"] = None
    
    # Cancel all WS tasks (candle processor, trade processor, 
    # intelligence processor, position monitor)
    for task in _execution_state["ws_tasks"]:
        if not task.done():
            task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    _execution_state["ws_tasks"] = []
```

---

## ⚠️ PROBLEMA CRITICO

### ❌ LA POSIZIONE APERTA NON VIENE CHIUSA!

```
┌─────────────────────────────────────────────────────────────┐
│ User clicca STOP con trade aperto a +5%                     │
└────────────────┬─────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend esegue stop:                                         │
│  ✓ Ferma WS client (no più candles)                         │
│  ✓ Cancella ExecutionLoop                                   │
│  ✓ Cancella _position_monitor task                          │
│  ❌ NON chiude la posizione aperta nel PositionManager!     │
└────────────────┬─────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ RISULTATO:                                                   │
│  ❌ Posizione rimane OPEN in PositionManager                │
│  ❌ Position monitor non controlla più SL/TP                │
│  ❌ Trade NON si chiude automaticamente                     │
│  ❌ Frontend mostra ancora posizione aperta                 │
│  ❌ PnL "congelato" al momento dello stop                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Scenari Concreti

### Scenario 1: Trade in Profit (+5%)
```
1. User ha trade aperto: BUY BTCUSDT @ 95000
2. Prezzo attuale: 95475 (+0.5%, vicino a TP)
3. User clicca STOP (per paura di perdere profit)
4. Backend ferma tutto MA non chiude trade
5. Posizione rimane aperta in PositionManager
6. Prezzo crolla a 94000 (-1%)
7. User ri-apre dashboard → vede ancora posizione "aperta"
8. Trade in loss -1% invece del profit +0.5%
```

### Scenario 2: Trade in Loss (-0.2%)
```
1. User ha trade aperto: SELL ETHUSDT @ 3500
2. Prezzo attuale: 3507 (-0.2%, lontano da SL)
3. User clicca STOP per emergenza
4. Backend ferma tutto MA non chiude trade
5. Position monitor si stoppa → SL non più controllato
6. Prezzo sale a 3600 (loss -2.86%)
7. SL a -0.3% non scatta perché monitor disattivato
8. Loss peggiora senza protezione
```

### Scenario 3: Backend Restart con Trade Aperto
```
1. User ha trade aperto: BUY BTCUSDT @ 95000
2. Backend crasha/restart
3. Session recovery ripristina session metadata
4. MA PositionManager è in-memory → posizione PERSA
5. Position monitor ricreato ma non sa del trade
6. Frontend mostra "No open position" (SBAGLIATO)
7. Trade rimane "fantasma" in DB ma nessun monitor
```

---

## ✅ SOLUZIONE NECESSARIA

### Option A: Close Position on Stop (RACCOMANDATO)
**Comportamento**: Stop = Chiudi tutto immediatamente

```python
elif action == "stop":
    # NUOVO: Chiudi posizione aperta se presente
    pm = _execution_state["position_manager"]
    pos = pm.get_open()
    if pos:
        # Fetch current price from Binance
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as hx:
            resp = await hx.get(f"https://api.binance.com/api/v3/ticker/price?symbol={pos.symbol}")
            if resp.status_code == 200:
                current_price = Decimal(str(resp.json()["price"]))
                
                # Close position at market price
                pm.close_position(current_price)
                
                # Calculate final PnL
                entry = float(pos.entry_price)
                current = float(current_price)
                qty = float(pos.quantity)
                if pos.side == "BUY":
                    pnl = (current - entry) * qty
                    pnl_pct = (current - entry) / entry * 100
                else:
                    pnl = (entry - current) * qty
                    pnl_pct = (entry - current) / entry * 100
                
                # Save trade to DB + trade_history
                trade_record = {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": entry,
                    "exit_price": current,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "close_reason": "manual_stop",
                }
                _execution_state["trade_history"].append(trade_record)
                
                # Broadcast trade_closed event
                await broadcast_scalping_event("trade_closed", trade_record)
                
                # Save to DB
                db_sid = session.get("db_session_id")
                if db_sid:
                    supabase.table("scalping_trades").insert({
                        "session_id": db_sid,
                        "symbol": trade_record["symbol"],
                        "side": trade_record["side"],
                        "entry_price": trade_record["entry_price"],
                        "exit_price": trade_record["exit_price"],
                        "quantity": qty,
                        "pnl": trade_record["pnl"],
                        "pnl_pct": trade_record["pnl_pct"],
                        "strategy_type": session["strategy"],
                        "status": "closed",
                        "entry_time": pos.entry_time.isoformat(),
                        "exit_time": trade_record["timestamp"]
                    }).execute()
                
                logger.info(
                    f"{GREEN}Position closed on session stop: {pos.side} {pos.symbol} "
                    f"@ {current:.2f} | PnL: {pnl:.2f} ({pnl_pct:.2f}%){RESET}"
                )

    # Poi ferma tutto come prima
    asyncio.create_task(_stop_ws_broadcast(), name="scalping-ws-stop")
    # ... resto del codice stop
```

**Pro**:
- ✅ Nessuna posizione "orfana"
- ✅ PnL finale accurato
- ✅ Trade salvato in DB
- ✅ User protetto da perdite incontrollate
- ✅ Comportamento prevedibile

**Contro**:
- ⚠️ User potrebbe voler solo "pausare" non chiudere (usa PAUSE invece)

---

### Option B: Warning + Confirmation Dialog (ALTERNATIVE)
**Comportamento**: Frontend mostra warning prima di stop

```typescript
// Frontend: session-controls.component.ts
stopSession(): void {
  // Check if there's an open position
  this.positionApi.getPosition().subscribe((pos) => {
    if (pos) {
      // Show confirmation dialog
      const confirmed = confirm(
        `⚠️ HAI UNA POSIZIONE APERTA!\n\n` +
        `Simbolo: ${pos.symbol}\n` +
        `Side: ${pos.side}\n` +
        `PnL: ${pos.pnl_pct.toFixed(2)}%\n\n` +
        `Stoppando la session, la posizione verrà chiusa al prezzo di mercato.\n\n` +
        `Vuoi continuare?`
      );
      
      if (!confirmed) {
        return; // User cancels
      }
    }
    
    // Proceed with stop
    this.sessionApi.stop().subscribe(/*...*/);
  });
}
```

**Pro**:
- ✅ User consapevole prima di chiudere
- ✅ Può cancellare se non voleva

**Contro**:
- ⚠️ Posizione comunque chiusa (come Option A)
- ⚠️ Aggiunge friction all'UX

---

### Option C: Keep Position Open (NON RACCOMANDATO)
**Comportamento**: Stop ferma monitor ma posizione resta aperta

**Pro**:
- ⚠️ Nessuno (solo più complessità)

**Contro**:
- ❌ Posizione senza protezione SL/TP
- ❌ Risk management disabilitato
- ❌ User non sa che trade è ancora aperto
- ❌ Backend restart perde traccia del trade
- ❌ PnL non aggiornato
- ❌ Pericoloso e confuso

---

## ✅ RACCOMANDAZIONE FINALE

### Implementare Option A: Auto-Close on Stop

**Motivi**:
1. **Safety First**: Nessuna posizione senza protezione SL/TP
2. **Predictable**: User sa che STOP = chiude tutto
3. **Clean State**: Sessione stopped = nessuna posizione aperta
4. **DB Consistency**: Tutti i trade salvati correttamente
5. **UX Chiara**: Se vuoi pausare → usa PAUSE, se vuoi chiudere → usa STOP

**Distinzione PAUSE vs STOP**:
```
PAUSE:
- Ferma signal generation (no nuovi trade)
- Mantiene position monitor attivo (SL/TP protetti)
- Posizione aperta continua a essere monitorata
- Resume riprende esecuzione

STOP:
- Chiude posizione aperta al market price
- Ferma tutto (WS, monitor, loop)
- Salva trade finale in DB
- Session terminata completamente
```

---

## 🚀 Next Actions

1. **Implementare close-on-stop** in router.py (10 min)
2. **Aggiungere test** per verificare chiusura (5 min)
3. **Aggiungere warning toast** nel frontend (optional, 5 min)
4. **Documentare** comportamento PAUSE vs STOP in UI (2 min)

---

**Tempo Totale**: 15-20 min
**Priorità**: 🔴 ALTA (bug safety-critical)
**Risk**: User perde soldi se position monitor si ferma senza chiudere
