# Runbook OKX Live Readiness — TASK-1113

> Data: 2026-07-08
> Versione: 1.0
> Stato: Bozza per revisione

---

## 1. Panoramica

Questo runbook documenta il setup, la verifica e il go-live di SynthTrade con OKX come
exchange provider primario. Binance resta disponibile come legacy fallback.

**Provider attuale:** OKX (default in `.env.example`)
**Modalità corrente:** TEST (Demo Trading)
**Stato migrazione:** TASK-1100→1112 completati, TASK-1113 in corso

---

## 2. Setup API Key OKX

### 2.1 Demo Trading

1. Vai su [OKX Demo Trading](https://www.okx.com/demo-trading)
2. Crea API Key con permessi:
   - Trading: ✅
   - Lettura: ✅
   - Withdrawal: ❌ (mai abilitare)
3. Copia in `.env`:
   ```ini
   OKX_API_KEY=your_okx_demo_api_key
   OKX_SECRET_KEY=your_okx_demo_secret_key
   OKX_PASSPHRASE=your_okx_demo_passphrase
   OKX_BASE_URL=https://eea.okx.com
   ```

### 2.2 Live Trading (solo dopo conferma manuale)

1. Vai su [OKX Account > API](https://www.okx.com/account/my-api)
2. Crea API Key con permessi:
   - Trading: ✅ (spot, non margin/futures)
   - Lettura: ✅
   - Withdrawal: ❌
   - IP restriction: ✅ (whitelist IP server)
3. Copia in `.env`:
   ```ini
   EXCHANGE_PROVIDER=okx
   TRADING_MODE=live
   ALLOW_LIVE_MODE=true
   OKX_API_KEY_LIVE=your_okx_live_api_key
   OKX_SECRET_KEY_LIVE=your_okx_live_secret_key
   OKX_PASSPHRASE_LIVE=your_okx_live_passphrase
   ```

---

## 3. Safety Gates

| Gate | Descrizione | Stato |
|------|-------------|-------|
| `ALLOW_LIVE_MODE=false` | Blocca avvio in modalità live | ✅ Attivo |
| `TRADING_MODE=test` | Default a Demo Trading | ✅ Attivo |
| `SCALPING_FORCE_PAPER=true` | Paper mode forzato | ✅ Attivo |
| Conferma UI per live | DA IMPLEMENTARE (frontend) | ❌ Pending |
| Trade value minimo | `SCALPING_TRADE_VALUE` default 10€ | ✅ Configurabile |

### Trade Value Consigliato

| Modalità | Valore Minimo | Note |
|----------|---------------|------|
| Paper | 10€ | Test strategia |
| Demo | 10€ | Test execution OKX |
| Live iniziale | 20€ | Trade minimo per fee reali |
| Live normale | 50-100€ | Dopo validazione positiva |

---

## 4. Smoke Tests — Checklist Pre-Go-Live

### 4.1 Backend Health

```bash
# Verifica che il backend sia in esecuzione
curl http://localhost:8000/health

# Atteso: {"status":"ok","version":"0.1.0","mode":"testnet"}
```

### 4.2 Instruments / Simboli Disponibili

```bash
# Verifica discovery strumenti OKX
curl http://localhost:8000/api/scalping/exchange/instruments

# Atteso: lista strumenti spot OKX con BTC-EUR in testa
# Deve includere: lotSz, minSz, tickSz, maxMktSz, maxMktAmt
```

### 4.3 Dashboard — Saldo OKX

```bash
# Verifica dashboard mostra saldo OKX
curl http://localhost:8000/api/dashboard

# Atteso: exchange_provider="okx", balance_eur ~112k€ (demo)
```

### 4.4 Start Paper Session

```bash
# Avvia sessione paper
curl -X POST http://localhost:8000/scalping/session \
  -H "Content-Type: application/json" \
  -d '{"action":"start","mode":"paper","symbol":"BTC-EUR"}'

# Atteso: session_id, status="running", exchange_provider="okx"
```

### 4.5 Start Demo Session

```bash
# Avvia sessione demo (test execution OKX reale)
curl -X POST http://localhost:8000/scalping/session \
  -H "Content-Type: application/json" \
  -d '{"action":"start","mode":"demo","symbol":"BTC-EUR"}'

# Atteso: session_id, status="running", exchange_demo=true
```

### 4.6 Candele Storiche

```bash
# Verifica caricamento candele OKX
curl http://localhost:8000/candles/btceur

# Atteso: 100 candele 1m con prezzi reali (non piatti)
```

### 4.7 Supervisor History

```bash
# Verifica storico decisioni supervisor (se disponibile)
curl http://localhost:8000/scalping/supervisor/history

# Atteso: lista decisioni supervisor o array vuoto
```

---

## 5. Emergency Stop Procedure

Se qualcosa va storto durante una sessione live:

### 5.1 Da API

```bash
# Stop immediato sessione
curl -X POST http://localhost:8000/scalping/session \
  -H "Content-Type: application/json" \
  -d '{"action":"stop"}'

# Questo cancella bracket aperti e chiude posizioni al market
```

### 5.2 Da DB (se API non risponde)

```sql
UPDATE scalping_sessions
SET status = 'stopped', stopped_at = NOW()
WHERE status = 'running';

-- Chiudi posizioni aperte
UPDATE scalping_trades
SET status = 'closed', closed_at = NOW(),
    exit_price = 0, pnl = 0,
    close_reason = 'emergency_stop'
WHERE status = 'open';
```

### 5.3 Da OKX (last resort)

1. Vai su [OKX Spot Trading](https://www.okx.com/trade-spot/BTC-EUR)
2. Chiudi manualmente ogni posizione aperta
3. Revoca API key da [OKX Account > API](https://www.okx.com/account/my-api)

---

## 6. Go-Live Checklist

- [ ] `.env` configurato con credenziali OKX Demo
- [ ] `ALLOW_LIVE_MODE=false` (sempre in demo/test)
- [ ] Backend avviato e health check OK
- [ ] Dashboard mostra saldo OKX demo (~112k€)
- [ ] Candele OKX caricate correttamente (prezzi reali, non piatti)
- [ ] Sessione paper avviata con successo (TASK-1112 ✅)
- [ ] Trade eseguito e bracket piazzato in paper
- [ ] Position chiusa (TP/SL/stop) e registrata in DB
- [ ] Supervisor AI produce decisioni (anche se degrade a no_action)
---

## 7. Cronologia Decisioni

| Data | Decisione | Note |
|------|-----------|------|
| 2026-07-03 | OKX Demo Trading verificato | Spike TASK-1100 completato |
| 2026-07-03 | Router provider-neutral | TASK-1107 100% |
| 2026-07-03 | Integration tests 12/12 PASS | TASK-1111 |
| 2026-07-08 | Sessione paper OKX funzionante | 6 trade, PnL -0.94 |
| 2026-07-08 | Fix grafico OKX real-time | Candele WS live funzionanti |
| TBD | Primo trade Demo con bracket reale | Da validare |
| TBD | Go-Live minimo (20€) | DA CONFERMA MANUALE |

---

## 8. Rischi Identificati

| Rischio | Impatto | Mitigazione |
|---------|---------|-------------|
| WS privato OKX bloccato per EU (60032) | Fill bracket non in tempo reale | REST polling fallback (2s) |
| Modelli AI senza crediti | Supervisor degradato a no_action | Graceful degradation già testata |
| Fee OKX rebate negative | Calcolo TP/SL invertito | `abs()` già applicato in router.py |
| Short selling non implementato | Segnali SELL ignorati | Nessun rischio live, solo opportunità perse |