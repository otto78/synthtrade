# Bug Fix Summary — Modulo Scalping

## Problemi Critici Identificati

### 1. SignalAggregator — Bypass Intelligence Errato (FIXATO 2026-06-11)
**File:** `synthtrade/backend/app/scalping/engine/signal_aggregator.py`

**Problema:** La condizione `abs(score) < 5.0 OR collectors ≤ 3` mischiava due casi distinti — score basso con dati sufficienti veniva bypassato come se mancassero dati.

**Soluzione Applicata (2026-06-11):**
- ✅ Separato in 3 casi distinti:
  1. **≤ 3 collector** → BYPASS intelligence (mancanza dati, usa solo segnale tecnico) — log `📋`
  2. **4+ collector + `abs(score) < 5.0`** → BLOCCO (dati sufficienti, mercato neutrale) — log `🔴 BLOCK ... intelligence neutrale (5 collectors, score=1.3)`
  3. **Score ≥ 5.0** → filtro intelligence completo (tradeable check, bias alignment, combined confidence)
- ✅ Colore `BLOCK` corretto da `🟡 YELLOW` a `🔴 RED` per coerenza
- ✅ Aggiunto campo `signal_type` (BUY/SELL/CLOSE/NONE) a `ExecutionDecision` per preservare il tipo originale

### 2. Segnali SELL Convertiti in BUY (FIXATO 2026-06-11)
**File:** `synthtrade/backend/app/scalping/router.py` (riga ~956)

**Problema:** Il router usava `"BUY" if decision.confidence > 0 else "SELL"` per determinare il tipo di segnale. Qualsiasi confidence positiva diventava BUY, anche se il segnale tecnico era SELL.

**Soluzione Applicata:**
- ✅ `signal_type` in `ExecutionDecision` usato direttamente per broadcast e trade execution
- ✅ Segnali SELL esplicitamente ignorati con log `>>> SKIP SELL: short non implementato, solo long permesso`

### 3. OCO Sync — Falso Stop-Loss a PnL=0 (FIXATO 2026-06-11)
**File:** `synthtrade/backend/app/scalping/router.py` (righe ~1214-1296)

**Problema:** L'OCO sync controllava `get_open_orders()` per rilevare se l'OCO era stato eseguito. Ma l'OCO è best-effort e spesso fallisce. Nessun ordine aperto non significa "OCO eseguito" ma "OCO mai piazzato". L'app registrava una chiusura fittizia a entry price (PnL=0) mentre la posizione reale su Binance era ancora aperta.

**Soluzione Applicata:**
- ✅ Ora controlla `getattr(pos, 'oco_id', None)` prima dello sync
- ✅ Se l'OCO non è mai stato piazzato (oco_id = None), lo sync viene saltato
- ✅ Previene il mismatch tra trade history e trades reali su Binance
- ✅ Dati falsi già cancellati da Supabase (2 record)

### 4. Trade Non Partono (Signal Aggregator)
**File:** `synthtrade/backend/app/scalping/engine/signal_aggregator.py`

**Problema:** Bias intelligence quasi sempre "neutral" blocca tutti i trade anche quando il segnale tecnico è valido.

**Soluzione Applicata (precedente):**
- ✅ Aggiunto parametro `paper_mode` al metodo `should_execute()`
- ✅ In paper mode, se `|score| < 5.0`, usa solo segnale tecnico con confidence check

**File:** `synthtrade/backend/app/scalping/engine/execution_loop.py`

**Soluzione Applicata:**
- ✅ Aggiunto attributo `self.paper_mode: bool = True`
- ✅ Aggiunto attributo `self.session_id: Optional[str] = None`
- ✅ Passa `paper_mode` al signal aggregator in `process_candle()`

### 5. Altri Bug in `router.py` (Da Verificare)
**File:** `synthtrade/backend/app/scalping/router.py`

**Problemi Segnalati:**
- `_trade_processor` — struttura closure (da verificare se ancora rotto)
- `paper_mode` non impostato su ExecutionLoop — già presente in `_start_ws_broadcast`?
- `_stop_ws_broadcast` non awaita cancellazione task
- `GET /session` senza fallback DB

## Prossimi Passi

1. ✅ **FIXATO (2026-06-11):** SignalAggregator: separata logica bypass/block intelligence
2. ✅ **FIXATO (2026-06-11):** Router: segnali SELL ignorati (solo LONG)
3. ✅ **FIXATO (2026-06-11):** OCO sync: guard su oco_id previene finti stop-loss
4. ✅ **FIXATO (2026-06-11):** DB pulito: cancellati 2 record falsi da scalping_trades
5. ⚠️ **DA VERIFICARE:** Bug strutturali `_trade_processor`, `_stop_ws_broadcast`, `GET /session`
