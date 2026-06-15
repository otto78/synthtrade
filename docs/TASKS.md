# TASKS.md — SynthTrade Task Tracking

## Active Tasks

### TASK-814 — Live Mode Bug Fixes (2026-06-05 → 2026-06-09) ✅

**Status:** Complete ✅

Fix issues identified from live session logs:
- [x] **Issue 1-8**: All fixed — WS handshake, RSS/CoinGecko/Whale pollers, OCO balance settlement, logging visibility, session restore pipeline, minNotional, OCO post-fee balance
- [x] Update docs and commit

---

### TASK-815 — SignalScoreEngine: soglia dinamica e pesi calibrati (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `signal_score_engine.py`

**Modifiche:**
- Pesi ridistribuiti (funding_rate 0.20, cvd 0.20, OI 0.15, L/S 0.15, F&G 0.15, whale 0.10, sentiment 0.05, onchain 0.0)
- Normalizzazione USDC→USDT per collector futures
- Soglia scalata: `effective_threshold = threshold * coverage`

---

### TASK-816 — RSI Bollinger: soglie calibrate per mercato ranging (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `rsi_bollinger.py`

**Modifiche:**
- RSI_OVERSOLD: 30 → 38
- RSI_OVERBOUGHT: 70 → 62
- BB tolleranza: 1.01 → 1.015
- Confidence: 0.7 → 0.6

---

### TASK-817 — SignalAggregator: bypass mean-reversion per ranging (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `signal_aggregator.py`

**Modifiche:**
- `MEAN_REVERSION_STRATEGIES = ("rsi_bollinger", "stoch_rsi_bb_squeeze")`
- Permette SELL da mean-reversion in ranging quando bias intelligence è bullish
- Permette BUY da mean-reversion in ranging quando bias intelligence è bearish

---

### TASK-818 — StrategySelector: mapping regimi corretto (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `strategy_selector.py`

**Modifiche:**
- `ranging` → `rsi_bollinger`
- `volatile` → `stoch_rsi_bb_squeeze`
- `trending_up/down` → `ema_cross`
- `unknown` → `momentum_base`

---

### TASK-819 — Supervisor: cooldown e regime validation (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `supervisor_scheduler.py`, `supervisor_client.py`

**Modifiche:**
- Cooldown cambio strategia: 20 minuti
- Cooldown aggiornamento parametri: 10 minuti
- Regime validation: blocca strategie non compatibili col regime corrente
- Se strategia proposta non ammessa, resetta cooldown per prossimo tick valido
- `REGIME_ALLOWED_STRATEGIES` mapping completo nel prompt AI

---

### TASK-820 — EMA Cross: rimuovere slope filter + registrazione nuove strategie (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `ema_cross.py`, `stoch_rsi_bb_squeeze.py`, `registry.py`

**Modifiche:**
- `ema_cross.py`: Rimosso MIN_SLOPE e logica pendenza — segnale BUY se EMA9 > EMA21, SELL se EMA9 < EMA21
- `stoch_rsi_bb_squeeze.py`: Creata strategia StochRSI + BB Squeeze per regime volatile
- `registry.py`: Registrata `stoch_rsi_bb_squeeze`

---

### TASK-821 — Frontend: default BNBUSDC e rimozione initial load (2026-06-09) ✅

**Status:** Complete ✅

**Modifiche:**
- Default symbol: BTCUSDT → BNBUSDC in tutti i componenti scalping
- Default strategia: scalping_v2 → momentum_base
- Dropdown strategie: aggiunto `stoch_rsi_bb_squeeze`, rimosso `scalping_v2`, nomi normalizzati
  (`RSI + Bollinger` invece di `RSI con Bollinger`, `StochRSI BB Squeeze` invece di `Stoch RSI con BB Squeeze`)
- Rimosso initial load da TradeLog e PerformancePanel (attendono sessione attiva)
- `strategy-panel.component.ts`: fallback `STRATEGY_DEFAULTS['momentum_base']` invece di `scalping_v2`

**File modificati:**
- `session-controls.component.ts`
- `live-chart.component.ts`
- `market-intel-panel.component.ts`
- `session-api.service.ts`
- `trade-log.component.ts`
- `performance-panel.component.ts`
- `strategy-panel.component.ts`

---

### TASK-823 — Fix persistenza sessione scalping: saldo, trade history, posizione aperta (2026-06-10) ✅

**Status:** Complete ✅

**Bug 1 — Saldo 10,000 falso dopo restart:**
- `_restore_scalping_session()` ora inizializza `BinanceExchangeAdapter` e fa `fetch_balance()` da Binance per sessioni live
- Usa `_normalize_binance_total_balance()` e `_select_preferred_quote_balance()` per trovare il saldo corretto

**Bug 2 — Lista trade vuota dopo restart:**
- Step 5: carica fino a 200 trade dalla tabella `scalping_trades` via `session_id`
- Popola `_execution_state["trade_history"]` in memoria

**Bug 3 — Performance vuota dopo restart:**
- Stessa causa del Bug 2 — dipende da `trade_history` popolato

**Bug 4 — Trade persi al restart (posizione aperta non persistita):**
- Nuova funzione `_save_open_position_to_db()`: salva posizione aperta su DB con `status='open'` subito dopo `pm.open_position()`
- Nuova funzione `_update_closed_position_in_db()`: UPDATE della stessa riga alla chiusura (anziché INSERT)
- La funzione `_close_position_and_record()` ora usa `_update_closed_position_in_db()` invece di INSERTare ex-novo
- Step 7: carica eventuale posizione con `status='open'` da DB e la ripristina in `PositionManager`
- `_restore_scalping_session()` resa async per supportare le chiamate CCXT

**Migration 010:** Aggiunta colonna `trade_value FLOAT` a `scalping_sessions`

**File modificati:**
- `synthtrade/backend/app/main.py` — `_restore_scalping_session()` async, Steps 5-8
- `synthtrade/backend/app/scalping/router.py` — funzioni helper persistenza

---

---

## Epica 800 — OCO Flow + UDS Definitivo

### TASK-824 — Pulizia codice legacy OCO sintetico e polling (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Rimosso `_place_oco_synthetic_inverted()` da `exchange.py`
- [x] Rimosso `_place_oco_synthetic()` da `exchange.py`
- [x] Rimosso polling OCO su ogni candela in `router.py` (sezione `FIX-2026-06-05: Sync OCO`)
- [x] Rimossi `place_stop_loss_order()`, `place_limit_order()` da `exchange.py`
- [x] Rimossi dal `ExchangeProtocol` i metodi non più necessari
- [x] `place_oco_order()` ora lancia `ExchangeOrderError` se OCO fallisce (no silent fallback)

---

### TASK-825 — Schema DB: aggiungere tp_price, sl_price a scalping_positions (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Migration SQL: `supabase/migrations/20260612_oco_flow_v2.sql`
  - Colonne aggiunte: `tp_price`, `sl_price`, `oco_order_list_id`, `sl_order_id`, `tp_order_id`
- [x] `_save_open_position_to_db()` aggiornata con nuovi parametri `tp_price`, `sl_price` e OCO IDs

---

### TASK-826 — Implementare `_on_order_update` in router.py (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Definito `_on_order_update(event)` in `router.py`
- [x] Gestione `status == "filled"`: determina TP/SL da orderId, calcola PnL, aggiorna DB, chiude posizione, broadcast UI
- [x] Gestione `status == "expired"`: log informativo, nessuna azione
- [x] Guard: se `pos` è None o `oco_order_list_id` non corrisponde → return silenzioso

---

### TASK-827 — UDS singleton check + avvio post OCO riuscito (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Rimosso avvio UDS immediato da `action == "start"` in `control_session()`
- [x] Aggiunta funzione `_start_uds_if_needed()` con singleton check
- [x] UDS avviato SOLO dopo OCO confermato (Caso A) nel `_candle_processor()`
- [x] UDS avviato in restore sessione se posizione aperta trovata
- [x] `on_reconnect_sync=_on_uds_reconnect_sync` passato a `uds.start()`
- [x] UDS stoppato correttamente in `action == "stop"`

---

### TASK-828 — Market sell emergenza con `_get_available_base_balance()` (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Funzione `_handle_oco_failed(exchange, symbol)` implementata in `router.py`
- [x] Cancella ordini orfani via `get_open_orders` + `cancel_order`
- [x] Market sell con `_get_available_base_balance()` (qty reale post-fee)
- [x] Broadcast UI `error` con `code: "OCO_FAILED"`
- [x] Nessun salvataggio DB — `continue` nel flusso live

---

### TASK-829 — Stop sessione: wait conferma cancellazione OCO prima di market sell (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Dopo `cancel_open_orders()` in stop sessione: `asyncio.sleep(0.5)`
- [x] Loop di verifica max 3 retry × 0.3s che `get_open_orders()` sia vuoto
- [x] Solo dopo conferma → prosegue con `_close_position_and_record()`

---

### TASK-830 — UDS reconnect sync: parametro `on_reconnect_sync` (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] `self._on_reconnect_sync: Optional[Callable] = None` in `UserDataStreamManager.__init__`
- [x] Parametro `on_reconnect_sync` aggiunto a `uds.start()`
- [x] Dopo `_reconnect()` in `_listen_loop()`: chiamata `await self._on_reconnect_sync()` se impostato
- [x] Implementata `_on_uds_reconnect_sync()` in `router.py`:
  - Query specifica per `tp_order_id` / `sl_order_id` via `_fetch_fill_price_by_order_id()`
  - Fallback a `fetch_closed_orders` se IDs non disponibili
  - Chiude posizione, aggiorna DB, broadcast UI

---

### TASK-831 — Restore sessione: query specifica per sl_order_id/tp_order_id (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] In `_restore_scalping_session()`: ripristina `oco_order_list_id`, `sl_order_id`, `tp_order_id` dal DB sul position object
- [x] `exchange._fetch_fill_price_by_order_id()` implementato in `exchange.py`
- [x] Restore usa `_fetch_fill_price_by_order_id()` invece di `fetch_my_trades` generico
- [x] Fallback a `fetch_closed_orders` filtrato per side se IDs non trovano match
- [x] UDS riavviato post-restore se posizione aperta trovata

---

### TASK-832 — Session Load Guard: bloccare trade durante avvio/restore sessione (2026-06-15)

**Status:** Complete ✅

**Scope completato:**
- [x] Aggiunta `SessionLoadGuard` in `_execution_state["session_load_guard"]`
- [x] Fasi richieste: `db_phase`, `exchange_phase`, `position_phase`, `buffer_phase`, `pipeline_phase`
- [x] Timeout 30s con log periodici ogni 5s e stato `failed` se una fase non completa
- [x] `_restore_scalping_session()` marca `loading` all'avvio e completa DB/exchange/position
- [x] `control_session(action="start")` resetta il guard, completa exchange/position e DB dopo insert
- [x] `_start_ws_broadcast()` completa `buffer_phase` dopo warmup e `pipeline_phase` dopo `BinanceWSClient.start()`
- [x] Gate in `_candle_processor`, `_trade_processor` e trade live inline: nessun trade finché `guard.is_ready()` è false
- [x] WebSocket `session_loading` e endpoint `GET /scalping/debug/session-load` per osservabilità
- [x] Tentativi trade bloccati salvati in `deque(maxlen=100)` per evitare crescita illimitata

**File modificati:**
- `synthtrade/backend/app/scalping/session_load_guard.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/backend/app/main.py`
- `docs/TASKS.md`
- `docs/OCO_FLOW.md`

---

---

## Epica 800 — Supervisor Intelligence + Fix Critici (Piano v3.1)

### TASK-833 — FASE A1: Rimuovere force_execute hardcoded (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** CRITICA — bypassa SignalAggregator, RiskManager e tutti i filtri  
**Fase:** A (prerequisito per tutto il resto)  
**Stima:** 0.5h  
**File coinvolti:** `router.py`, `signal_aggregator.py`

**Scope:**
- [ ] Rimuovere `execution_loop.force_execute = True` da `router.py`
- [ ] Rimuovere attributo `self.force_execute` dalla classe `ExecutionLoop`
- [ ] Rimuovere il "Caso 0: FORCE_EXECUTE" da `signal_aggregator.py`
- [ ] Verifica: avviare sessione paper e controllare che non appaia `LIVE MODE: ... (intelligence bypassed)`

---

### TASK-834 — FASE A2: Supervisor interval da .env (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** CRITICA — supervisor gira ogni 45s invece di 10min, spreca API  
**Fase:** A (prerequisito per tutto il resto)  
**Stima:** 0.5h  
**File coinvolti:** `router.py`, `supervisor_scheduler.py`, `.env`, `config.py`

**Scope:**
- [ ] Aggiungere `SCALPING_SUPERVISOR_INTERVAL_SEC=600` a `.env`
- [ ] Aggiungere `SCALPING_SUPERVISOR_INTERVAL_SEC`, `SCALPING_STRATEGY_COOLDOWN_SEC`, `SCALPING_PARAM_UPDATE_COOLDOWN_SEC` a `config.py`
- [ ] Sostituire `interval_seconds=45` con `settings.SCALPING_SUPERVISOR_INTERVAL_SEC` nei 2 punti di istanziazione `SupervisorScheduler` in `router.py`
- [ ] Sostituire costanti hardcoded `STRATEGY_CHANGE_COOLDOWN = 1200` e `PARAM_UPDATE_COOLDOWN = 600` in `supervisor_scheduler.py` con valori da `settings`
- [ ] Verifica: log supervisor ogni ~600 secondi, missed jobs APScheduler spariti

---

### TASK-835 — FASE B1-B2: .env completo e config.py aggiornato (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — prerequisito per B3-B5  
**Fase:** B (dopo Fase A)  
**Stima:** 1h  
**File coinvolti:** `.env`, `config.py`

**Scope:**
- [ ] Sostituire sezione scalping in `.env` con versione completa e commentata (da piano §B1)
- [ ] Aggiungere/sostituire sezione scalping in `config.py` con tutti i campi tipizzati (da piano §B2)
- [ ] Verificare compatibilità con pattern `settings.scalping.*` se usato nel codice esistente

---

### TASK-836 — FASE B3: Migration DB tabella `scalping_runtime_config` (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta  
**Fase:** B  
**Stima:** 0.5h  
**File coinvolti:** nuova migration Supabase

**Scope:**
- [ ] Creare migration SQL con `CREATE TABLE scalping_runtime_config (key, value, value_type, description, updated_at)`
- [ ] Inserire valori di default (specchio del .env) per tutti i 15 parametri `[RUNTIME]`
- [ ] Applicare migration su Supabase

---

### TASK-837 — FASE B4: Nuovo `ScalpingConfigLoader` (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta  
**Fase:** B  
**Stima:** 1h  
**File coinvolti:** nuovo `app/scalping/config_loader.py`

**Scope:**
- [ ] Creare `app/scalping/config_loader.py` con classe `ScalpingConfigLoader`
- [ ] Implementare `_load()`: step 1 da settings, step 2 override da DB con type-casting
- [ ] Implementare `reload()` per aggiornamento runtime senza restart
- [ ] Implementare proprietà typed per tutti i parametri configurabili
- [ ] Esporre singleton `get_scalping_config()`

---

### TASK-838 — FASE B5: Endpoint API config scalping (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Media  
**Fase:** B  
**Stima:** 0.5h  
**File coinvolti:** `router.py` o nuovo `config_scalping_api.py`

**Scope:**
- [ ] `GET /api/scalping/config` — ritorna config corrente merge .env+DB
- [ ] `POST /api/scalping/config/{key}` — aggiorna valore nel DB e ricarica
- [ ] `POST /api/scalping/config/reload` — ricarica senza restart
- [ ] Test: modificare un valore via POST e verificare che il reload abbia effetto

---

### TASK-839 — FASE C1: Sostituire Fear & Greed con alternative.me (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — F&G congelato a 8, dato falso guida tutte le decisioni AI  
**Fase:** C (dopo Fase B)  
**Stima:** 1h  
**File coinvolti:** `app/scalping/intelligence/collectors/fear_greed.py`

**Scope:**
- [ ] Riscrivere `FearGreedCollector` per usare `https://api.alternative.me/fng/?limit=1` (gratuita, no API key)
- [ ] Implementare cache intraday con TTL 4h
- [ ] Implementare `value_to_score(value)` con logica contrarian (-100..+100)
- [ ] Impostare `SCALPING_FEAR_GREED_SOURCE=alternative_me` in `.env`
- [ ] Verifica log: `FearGreed aggiornato: XX (Fear/Greed)` con valore reale, non 8

---

### TASK-840 — FASE C2: Fix copertura whale collector disabilitato (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — peso 0.10 fantasma riduce coverage artificialmente  
**Fase:** C  
**Stima:** 0.5h  
**File coinvolti:** `signal_score_engine.py`

**Scope:**
- [ ] Escludere whale da `active_collectors` se `settings.SCALPING_WHALE_ENABLED=False`
- [ ] Correggere formula coverage: `total_weight_configured` calcolato solo sui collector attivi con peso > 0
- [ ] Aggiungere `SCALPING_WHALE_ENABLED=false` a `.env`
- [ ] Verifica: coverage non più penalizzata dal whale assente

---

### TASK-841 — FASE D1: Log diagnostica score engine (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — senza diagnosi non si sa se i score sono in [-1,+1] o [-100,+100]  
**Fase:** D (dopo Fase C)  
**Stima:** 0.5h  
**File coinvolti:** `signal_score_engine.py`

**Scope:**
- [ ] Aggiungere log DEBUG in `compute()` con breakdown raw score per collector
- [ ] Log deve mostrare: `breakdown raw`, `weighted_avg`, `total_weight`, `coverage`
- [ ] Avviare sessione paper e analizzare 2-3 cicli di output
- [ ] Determinare Scenario A (scala già -100..+100) o Scenario B (scala -1..+1)

---

### TASK-842 — FASE D2-D3: Fix normalizzazione score e soglie (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — score mai supera 1.0 con soglia a 15, nessun trade passa il gate  
**Fase:** D (dopo TASK-841)  
**Stima:** 2h  
**File coinvolti:** `signal_score_engine.py`, `.env`

**Scope:**
- [ ] In base alla diagnosi D1: se Scenario B, scalare ogni `*_to_score()` da [-1,+1] a [-100,+100]
- [ ] Verificare che `weighted_avg` non venga diviso per 100 prima di confronto soglia
- [ ] Aggiornare `SCALPING_SIGNAL_STRENGTH_THRESHOLD=15.0` in `.env` con commenti di interpretazione
- [ ] Verifica log: score appare in range [-100,+100]

---

### TASK-843 — FASE D4: SignalAggregator min_collectors da config (2026-06-15)

**Status:** Todo  
**Priorità:** Media  
**Fase:** D  
**Stima:** 0.25h  
**File coinvolti:** `signal_aggregator.py`

**Scope:**
- [ ] Sostituire `num_collectors_responded <= 3` hardcoded con `get_scalping_config().min_collectors`
- [ ] Importare `get_scalping_config` da `app.scalping.config_loader`

---

### TASK-844 — FASE E1-E2: Supervisor — contesto arricchito con performance sessione (2026-06-15)

**Status:** Todo  
**Priorità:** Media — supervisor decide senza vedere storico trade né PnL  
**Fase:** E (dopo Fasi A, B, C)  
**Stima:** 2h  
**File coinvolti:** `supervisor_scheduler.py`

**Scope:**
- [ ] Aggiungere parametro `session_id` a `build_scalping_context()`
- [ ] Query DB `scalping_trades` per ultimi 20 trade chiusi della sessione
- [ ] Calcolare `session_performance`: trade count, wins, losses, pnl, win_rate, ultimi 5
- [ ] Leggere strategia attiva da `_execution_state`
- [ ] Aggiornare `_format_context()` con sezione `=== PERFORMANCE SESSIONE ===`
- [ ] Includere `supervisor_history` nel formato (preparazione per F3)

---

### TASK-845 — FASE E3: Aggiornare system prompt supervisor (2026-06-15)

**Status:** Todo  
**Priorità:** Media — prompt attuale non guida correttamente quando NO agire  
**Fase:** E  
**Stima:** 0.5h  
**File coinvolti:** `supervisor_client.py`

**Scope:**
- [ ] Sostituire `SUPERVISOR_SYSTEM_PROMPT` con versione completa dal piano §E3
- [ ] Sezione `QUANDO NON AGIRE`: < 5 trade, stessa azione 3+ volte, < 4 collector, score neutrale
- [ ] Sezione `QUANDO AGIRE`: regole per change_strategy, update_params, pause/resume
- [ ] Mapping REGIME → STRATEGIA nel prompt
- [ ] Gerarchia segnali (1-8) nel prompt
- [ ] Verifica: supervisor risponde `no_action` se < 5 trade in sessione

---

### TASK-846 — FASE F1: Migration DB tabella `supervisor_memory` (2026-06-15)

**Status:** Todo  
**Priorità:** Media — senza memoria il supervisor propone la stessa azione in loop  
**Fase:** F (dopo Fase E)  
**Stima:** 0.5h  
**File coinvolti:** nuova migration Supabase

**Scope:**
- [ ] Creare migration SQL `supervisor_memory` con colonne: id, session_id, symbol, decided_at, action, reason, confidence, market_bias, primary_signal, new_strategy, new_params, was_applied, blocked_reason, market_context, session_perf, outcome_*
- [ ] Creare indici su (symbol, decided_at DESC), session_id, (action, was_applied)
- [ ] Applicare migration su Supabase

---

### TASK-847 — FASE F2-F3: Persistenza e caricamento memoria supervisor (2026-06-15)

**Status:** Todo  
**Priorità:** Media  
**Fase:** F  
**Stima:** 1.5h  
**File coinvolti:** `supervisor_scheduler.py`

**Scope:**
- [ ] Implementare `_save_decision_to_memory()`: INSERT su `supervisor_memory` per ogni decisione (anche bloccate)
- [ ] Chiamare `_save_decision_to_memory()` dopo ogni esecuzione del supervisor con flag `was_applied` e `blocked_reason`
- [ ] Aggiungere a `build_scalping_context()`: query ultime 10 decisioni da `supervisor_memory` per symbol
- [ ] Popolare chiave `supervisor_history` nel context dict
- [ ] Verifica: tabella `supervisor_memory` si popola a ogni ciclo supervisor

---

### TASK-848 — FASE F4: Job APScheduler verifica outcome decisioni (2026-06-15)

**Status:** Todo  
**Priorità:** Bassa  
**Fase:** F  
**Stima:** 1h  
**File coinvolti:** `scheduler/jobs.py` (o equivalente)

**Scope:**
- [ ] Implementare `verify_supervisor_outcomes_job()`
- [ ] Query decisioni applicate 25-35 minuti fa senza outcome
- [ ] Calcolare `pnl_delta` vs snapshot PnL al momento della decisione
- [ ] Classificare outcome: positive/negative/neutral (soglia ±0.01)
- [ ] UPDATE `supervisor_memory` con `outcome_verified_at`, `outcome_pnl_delta`, `outcome_label`
- [ ] Registrare job in `setup_scheduler()` con interval 5 minuti
- [ ] Verifica: dopo 30 min da una decisione applicata, `outcome_label` è valorizzato

---

### TASK-822 — Config panel: rimuovere sub-tab "Strategy" e aggiungere titolo "Session" con ID (2026-06-09)

**Status:** Complete ✅

**Problema:** Nel pannello di configurazione principale è presente una sub-scheda "Strategy" che mostra la strategia selezionata inizialmente ma non si aggiorna quando la strategia corrente cambia (es. dopo una decisione del supervisor AI). Esiste già una sezione più completa e aggiornata nel pannello Strategy dedicato.

**Soluzione:**
1. Rimuovere la sub-scheda "Strategy" dal pannello di configurazione principale
2. Aggiungere un titolo principale "Session" al pannello di configurazione
3. Mostrare l'ID della sessione in testo più piccolo sotto il titolo
4. Mantenere visibili le impostazioni di configurazione del trade già esistenti nel sistema

**Modifiche:**
- Rimuovere sub-tab "Strategy" dal componente del pannello configurazione sessione
- Aggiungere header con titolo "Session" + session ID
- Lasciare al loro posto le impostazioni esistenti (symbol, strategy selector, trade value)

**Rischio:** Basso — rimozione UI senza impatto su logica backend.
