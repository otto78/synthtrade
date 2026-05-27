# Handoff Protocol — SynthTrade

---

## 🔄 Ultimo Handoff

### Da: Cline → prossima sessione

**Data:** 2026-05-27

**Contesto:** 14 bug fix sulla UI scalping — WS endpoint, proxy, session state, posizioni, trade log, performance, PnL live.

---

### ✅ FASE COMPLETATA: Fix frontend scalping (2026-05-27)

**Cosa è stato fatto:**
- Fix Binance WS URL: da `/stream?streams=` combinato a connessioni separate `/ws/SYMBOL@kline` e `/ws/SYMBOL@trade`
- Fix proxy.conf.json: aggiunto `"ws": true` alla regola `/api` per WS upgrade
- Fix WS endpoint route: spostato da `/api/scalping/ws/scalping` a `/ws/scalping`
- Fix initial session state: rimosso invio stato idle su WS connect
- Fix session UI: rimosso polling, ChangeDetectorRef per aggiornamento reattivo
- Fix position ticker: usa WS `position$` invece di REST call
- Fix trade log: usa WS `trade_closed$` invece di polling REST
- Fix performance panel: mappatura snake_case → camelCase, refresh su trade closed
- Fix PnL live: `position_update` broadcast su ogni candela mock
- Fix mock generator: avviato (mancava `asyncio.create_task`)
- Fix collector bug: `await response.json()` → `response.json()` in 4 collectors
- Fix Decimal serialization: `float()` per long_pct/short_pct in snapshot job
- Nuovo endpoint `GET /api/scalping/trade-history`

**Dati mock:** Candele simulate localmente (non Binance). WS funzionante.

---

### 📊 Stato Attuale

**Fase corrente:** Scalping Module v2.0 — Frontend Dashboard funzionante

**Completato:**
- ✅ TASK-800 (ScalpingSettings)
- ✅ TASK-801 (Estensione moduli core)
- ✅ TASK-802 (DB Migrations)
- ✅ TASK-803 (Binance WsClient)
- ✅ TASK-804 (Intelligence Layer)
- ✅ TASK-805 (TickProcessor + ExecutionLoop)
- ✅ TASK-806 (AI Supervisor)
- ✅ TASK-807 (Scheduler Centralizzato)
- ✅ TASK-808 (Backtest Engine)
- ✅ TASK-809 (Frontend Dashboard Scalping) — fix completati
- 🔜 TASK-810 (Opportunity Monitor) — stub implementato
- 🔜 TASK-811 (Regressione E2E)
- 🔜 TASK-812 (Go Live)

**Componenti funzionanti:**
- SessionControls (start/stop/pause/resume)
- LiveChart (candele simulate)
- PositionTicker (posizione aperta + PnL live)
- TradeLog (trade chiusi via WS)
- PerformancePanel (metriche su trade_closed)
- MarketIntelPanel (dati reali API)
- SignalScorecard (score aggregato)

---

### 🎯 Prossimi Step (in ordine)

1. **TASK-810 — Opportunity Monitor**: Completare scheduler + frontend feed
2. **TASK-811 — Regressione E2E**: Test Playwright per scalping session, market intel
3. **TASK-812 — Go Live**: Review sicurezza ordini, test LIVE con trade minimo
4. **Fix Binance WS**: Connessione reale a Binance (al posto del mock)
5. **Opportunities**: Collegare scheduler a endpoint, popolare tabella

### 📝 Note Importanti

- Backend: `http://localhost:8888` (porta configurata in `.env`)
- Frontend: `http://localhost:4208` (proxy → 8888)
- WS endpoint: `/ws/scalping` (non `/api/scalping/ws/scalping`)
- Modalità: PAPER default (cambia in `.env`: `TRADING_MODE=live`)
- Test backend: `cd synthtrade/backend && python -m pytest`
- Build frontend: `cd synthtrade/frontend/synthtrade-ui && ng build`

---

**Ultima modifica:** 2025-01-15 — Amazon Q
