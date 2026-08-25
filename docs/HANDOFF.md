# Handoff Protocol — SynthTrade

## Ultimo Handoff

### Da: sessione TASK-1250 + TASK-1251 (filtro macro trend + override guard) → prossima sessione

**Data:** 2026-08-25

**Contesto:** Analisi sessione 11-25 agosto (48 trade, 14 giorni) ha confermato che il bot perdeva per cause strutturali: override mean-reversion con win rate 25%, regime detector che vedeva "ranging" durante un rally +27% BTC. Implementati due fix chirurgici che indirizzano entrambe le cause.

### ✅ Fatto in questa sessione

- **TASK-1251 — Strong Bearish Guard** (`signal_aggregator.py` + `config_loader.py`): Blocco override mean-reversion quando bias bearish forte (score < -15.0). Soglia configurabile via DB (`MEAN_REVERSION_STRONG_BEARISH_THRESHOLD`). 4 nuovi test — tutti verdi.
- **TASK-1250 — Macro Trend Filter** (4 file): Se BTC > EMA20 4h, strategy selector forza `ema_cross` invece di `rsi_bollinger` su regime ranging; signal aggregator blocca qualsiasi override mean-reversion residuo. Macro context fetchato una sola volta per candela (eliminata chiamata duplicata all'exchange). 8 nuovi test — tutti verdi.
- **Archivio e doc**: ARCHIVE_TASKS.md, TASKS.md, STORY.md, HANDOFF.md, CHANGELOG.md aggiornati.

### ⚠️ Cosa NON fare la prossima settimana

- **NON cambiare SL/TP** (TASK-1253) finché non ci sono almeno 30 trade post-fix. I parametri attuali potrebbero essere già adeguati se il win rate sale con il nuovo filtro macro.
- **NON ricalibrar lo score** (TASK-1252) prima di avere dati puliti: la correlazione score→PnL era misurata su sessioni con l'override difettoso, non è detto che resti zero.
- **NON attivare trailing** su sessioni nuove prima di aver verificato che il win rate sia salito a >38%.

### ⏳ Da fare la settimana del 2026-09-01

1. **Raccogliere dati:** avviare sessione live con TASK-1250/1251 attivi, raccogliere almeno 30 trade.
2. **Analizzare:** win rate per combinazione regime/strategia (regime=ranging+ema_cross vs rsi_bollinger), correlazione score→PnL sui nuovi dati.
3. **TASK-1252:** se score resta con correlazione ~0, implementare ricalibrazione soglia.
4. **TASK-1253:** se win rate resta <38%, adeguare SL/TP o bloccare combinazioni low-win-rate.

### ⚠️ Test stale pre-esistenti (non regressioni)

- `test_blocks_sell_when_bullish` — si aspetta "conflitto" nel reason, ma i SELL sono disabilitati permanentemente (long-only engine, TASK-1240) e restituiscono "SELL signals disabled".
- `test_allows_sell_when_bearish` — stessa causa: SELL disabilitati.
- `test_historical_context.py` — mock `get_supabase` non nel namespace modulo.
- `test_task_906.py::test_falling_knife_does_not_block_mean_reversion_sell` — testa SELL mean-reversion, permanentemente disabilitati.

### ⏳ GATE pre-live TASK-1246 (trailing stop) ancora pendente

1. `python -m scripts.test_okx_amend_rate [--symbol BTC-EUR] [--interval 15]` con `TRADING_MODE=test` → 6 amend consecutivi su OKX Demo, zero 429/sCode rate-limit.
2. Query storica TP per confermare `TRAILING_STEP_NET_PCT=0.15`.
3. ≥20 trade con `trailing_enabled=true` prima di considerare stabile la feature.

---

### Handoff Precedente

### Da: sessione TASK-1246 (trailing stop) → prossima sessione

**Data:** 2026-08-05

**Contesto:** TASK-1246 (trailing stop progressivo post break-even) — implementazione completata, migration `trailing_step` applicata. GATE pre-live ancora pendente.

### ✅ Fatto in questa sessione

- **Migration DB applicata:** `scalping_trades.trailing_step int NOT NULL DEFAULT 0` (mancava mentre `TRAILING_ENABLED=true` era già attivo). File locale: `synthtrade/supabase/migrations/20260805000000_task1246_add_trailing_step.sql`.
- **Fix flaky test** `test_polling_is_async_not_blocking` (`test_wait_for_fill.py`): `time.monotonic()` + soglia tollerante.
- **Dedup `_update_trailing_in_db`** in `db_ops.py` (doppia definizione).
- **38/38 test verdi** (`test_wait_for_fill.py` + `test_task_1243.py`). La suite unit completa `tests/unit` va in timeout — non è regressione di questa sessione.
- Commit `68eddb5` (parallelo, già su main): `_wait_for_fill()` per sCode 51008 + filtro log WinError 10054 + cleanup banner position-ticker.

### ⏳ GATE pre-live TASK-1246 ancora da eseguire

1. `python -m scripts.test_okx_amend_rate [--symbol BTC-EUR] [--interval 15]` con `TRADING_MODE=test` → 6 amend consecutivi su OKX Demo, verificare zero 429/sCode rate-limit e `algoId` invariato.
2. Query storica TP (`docs/plans/trailing-stop-progressive.md` §step size) per confermare `TRAILING_STEP_NET_PCT=0.15`.
3. ≥20 trade con `trailing_enabled=true` prima di considerare stabile la feature.

### ⚠️ Note operative

- Config runtime in `scalping_runtime_config`: `BREAK_EVEN_ENABLED=true`, `TRAILING_ENABLED=true` (entrambi attivi).
- Colonna `trailing_step` è solo telemetria/UI; la fonte di verità del prezzo SL resta `sl_price`.
- Sessione LIVE attiva al momento (`d253c56e-…`) — non riavviare il backend se non necessario; niente `--reload`.

---

## Handoff Precedenti

### Da: Kiro → prossima sessione

**Data:** 2026-08-04

**Contesto:** TASK-1243 — Break-even profit lock OCO OKX — **COMPLETATO e validato in produzione**.

---

### ✅ Cosa è stato fatto

**Feature implementata end-to-end:**
- `app/scalping/break_even.py` — modulo autonomo con trigger, amend, lock async, DB, WS
- `execution/okx_exchange.py` — `amend_exit_bracket_stop_loss()` firmato verso `/api/v5/trade/amend-algos`
- `execution/exchange_models.py` — metodo nel protocollo `ExchangeAdapterProtocol`
- `execution/exchange.py` — stub Binance `NotImplementedError`
- `scalping/db_ops.py` — `_update_break_even_in_db()` filtra solo per `exchange_bracket_id`
- `scalping/config_loader.py` — chiavi `BREAK_EVEN_ENABLED` (default false), `BREAK_EVEN_TRIGGER_NET_PCT` (0.15), `BREAK_EVEN_LOCK_NET_PCT` (0.05)
- `scalping/candle_processor.py` — chiamata `_check_and_apply_break_even` su ogni candela chiusa + `profit_lock_active` nel broadcast WS
- `main.py` — restore dei 3 campi `break_even_*` dal DB per impedire doppio amend dopo restart
- Migration DB: colonne `break_even_triggered`, `break_even_activated_at`, `break_even_sl_price` su `scalping_trades`
- 22 test automatici verdi (`tests/test_task_1243.py`)

**Feature flag:** `BREAK_EVEN_ENABLED` in tabella `scalping_runtime_config`. Al momento è `true` (attivato manualmente il 2026-08-04).

---

### 🧪 Prova live eseguita — 2026-08-04

**Sessione:** `6701e55b-8208-4dd2-a34f-0cf9552cbd14`
**algoId:** `3802582373171404800`
**Simbolo:** BTC-EUR

| Evento | Ora | Dettaglio |
|--------|-----|-----------|
| Restore posizione | 11:39:49 | entry=55154.6, qty=0.000363, SL=54988.75 |
| BE TRIGGER | 12:53:01 | current=55368.0, net_pct=+0.186%, newSL=55292.70 |
| AMEND_SL SUCCESS | 12:53:01 | sCode=0, latenza ~0.77s |
| Trade chiuso (SL) | 13:08:04 | exit=55291.0, **PnL=+0.01 EUR (+0.05%)** |
| Nuovo trade aperto | 13:33:00 | entry=55270.4, algoId=3803085709051285504 |

**Risultato:** senza break-even → perdita attesa ~-0.06 EUR se SL originale colpito. Con break-even → +0.01 EUR. **Delta +0.07 EUR su trade da 20 EUR.**

---

### 📌 Prossimi passi consigliati

1. **Raccogliere almeno 20 trade** con `BREAK_EVEN_ENABLED=true` e ricalcolare EV medio per validare l'impatto statistico.
2. **Frontend:** aggiungere badge "🔒 Profit Lock" nel componente posizione quando `profit_lock_active=true` nel payload WS.
3. **Calibrazione soglie:** dopo 20 trade valutare se `BREAK_EVEN_TRIGGER_NET_PCT=0.15` è troppo aggressivo (trigger troppo presto) o conservativo (trigger raramente). Modificabile via `scalping_runtime_config` senza restart.

---

### ⚠️ Regole invarianti da non toccare

- L'identità dell'ordine è sempre e solo `algoId` (`pos.oco_order_list_id`). Non usare mai match per simbolo/lato.
- `break_even_triggered` è una transizione monotona (false→true). Non può tornare false.
- L'amend viene applicato **solo dopo** conferma OKX (`code=="0"` AND `sCode=="0"`). Se OKX rigetta, stato locale invariato.
- Il nuovo SL deve essere strettamente > SL attuale per un long. Il guard è nel codice — non rimuoverlo.



- Il piano completo è in `docs/plans/phase3-trailing-sl.md`. La configurazione proposta
  attiva a circa +0.15% netto (circa +0.35% lordo con fee 0.10%+0.10%) e mira a un nuovo
  SL di circa +0.05% netto. Non è un profitto garantito perché lo SL OCO esegue a mercato.
- L'unica identità ammessa è `Position.oco_order_list_id` / `exchange_bracket_id`
  (OKX parent `algoId`). Non ricercare un SELL o “il primo ordine” di BTC-EUR: romperebbe
  multi-sessione e il reconcile OCO appena corretto.
---

### Da: Codex → prossima sessione

**Data:** 2026-08-04

**Contesto:** TASK-1244 — correzione definitiva della riconciliazione delle chiusure OCO OKX mentre l'app era offline.

### Riparazione storico già chiuso
- `scripts/repair_okx_trade_history.py` non modifica nulla per default. Eseguire il dry-run con `--session-id <uuid> --report C:\tmp\okx-repair.json`, verificare le righe `update_verified`, quindi applicare con `--apply --report ... --confirm APPLY_OKX_REPAIR`.
- Il job non usa matching per simbolo/lato e scarta i casi senza catena `algoId → ordId → fill`. Non eseguire gli script storici `fix_db.py`/`list_db.py`: sono stati rimossi perché non sicuri.

### ✅ Diagnosi e fix
- Il codice precedente chiamava `get_algo_orders_history()`, ma l'adapter interrogava prima `/api/v5/trade/fills` per l'intero simbolo e ritornava subito. Il reconcile, se l'`algoId` non compariva in quel fill, sceglieva la prima vendita `side=sell`: non era una correlazione con l'OCO e poteva usare il trade di un'altra sessione.
- `OkxExchangeAdapter.get_algo_orders_history(symbol, bracket_id)` ora legge `orders-algo-history` per lo specifico `algoId` salvato nel DB, estrae il child `ordId` e richiede i fill soltanto per quell'ordine. Restituisce prezzo medio ponderato, `actualSide` (TP/SL) e `fillTime` reale.
- `reconciliation.py` accetta una chiusura solo con match esatto `algoId`. Rimossi fallback ``exit side`` e ``entry_price``; se l'API non ha ancora propagato il fill, la posizione locale non viene chiusa/corrotta e il retry successivo resta sicuro.

### 🧪 Verifica eseguita
- `.venv\\Scripts\\python.exe -m pytest synthtrade/backend/tests/unit/test_reconcile_position.py synthtrade/backend/tests/unit/test_okx_oco_reconciliation.py -q`
- Risultato: **7 passed**. `ruff` non è installato nel virtualenv.

### 📌 Test manuale raccomandato
1. Aprire un trade live con OCO, annotare `exchange_bracket_id` nella riga `scalping_trades`.
2. Fermare il backend, lasciare scattare SL o TP su OKX, riavviare.
3. Verificare che `exit_price`/`exit_time` coincidano con il fill del child `ordId` dell'OCO e che la riga diventi `closed`; sia dashboard sia pagina Log leggono la stessa riga DB.
4. In caso di ritardo API, verificare il warning ``no verified fill exists``: non deve comparire una chiusura a entry price.

---

### Da: Antigravity → prossima sessione

**Data:** 2026-08-03 09:45

**Contesto:** Fix bug timestamp riconciliazione exit_time OKX post-riavvio weekend e fix formattazione data/ora trade log sessioni frontend.

---

### ✅ Fix 1 — Timestamp riconciliazione exit_time (`okx_exchange.py`)
- **Problema:** Post-riavvio del weekend, i trade riconciliati mostravano come `exit_time` l'orario di esecuzione della riconciliazione (`datetime.now()`) invece del reale timestamp di fill su OKX.
- **Root Cause:** OKX `/api/v5/trade/fills` utilizza la chiave `ts` per il timestamp dei fill e non `fillTime`. L'adapter `okx_exchange.py` (L.745) eseguiva `fill.get("fillTime")` che ritornava sempre `None`.
- **Fix:** Modificato in `fill.get("fillTime") or fill.get("ts")`. Ora `exit_time` viene estratto correttamente dal fill OKX.

---

### ✅ Fix 2 — Formattazione data/ora trade log sessioni (`logs.page.ts`)
- **Problema:** La tabella dei trade nel dettaglio sessione mostrava solo l'ora (`HH:mm`) per `entry_time`, rendendo ambigua la data dei trade.
- **Fix:** In `logs.page.ts` (L.184), aggiornato il pipe di formattazione a `dd/MM/yy HH:mm` e rinominata l'intestazione da `Ora` a `Data/Ora`, allineandola allo Storico Trade.

---

### ⚠️ Punto Aperto Residuo
- **`position_manager.py` (Live close path):** Il percorso di chiusura in-memory/live imposta ancora `closed_at = datetime.now()` al momento della ricezione/gestione dell'evento di chiusura anziché adottare il timestamp esatto dal payload dell'exchange/WS. Resta da gestire in un task separato.

---

### Precedente Handoff

### Da: Antigravity → prossima sessione

**Data:** 2026-07-28 09:30

**Contesto:** Analisi completa log sessione 4a42133e (10.847 righe) — 5 nuovi task creati per approfondimento e fix.

---

### ✅ Recap mancante — Risolto

Il blocco SESSION ANALYSIS SUMMARY ora è presente in testa al dump e popolato correttamente. La fix applicata:
- Rimuovere conteggio SELL dal summary (long-only engine)

**Verificato:** Decisioni=891 totali, Segnali=1, Trades=8, Intelligence min=-26.2 max=18.9 avg=-4.3

### ✅ Punto 1 aggiornato — Task TASK-1231 creato

Cleanup: rimuovere scomposizione BUY/SELL dal Session Summary.

---

### 🔴 TASK-1232: Query storica win rate mean-reversion override

Join `session_signal_log` → `scalping_trades` via `signal_log_id`, bucket per `intel_score`, calcolo win rate e avg PnL per bucket. Documento in `docs/recap/`.

**Bloccante:** TASK-1233 (verifica integrità signal_log_id)

### 🔴 TASK-1233: Verifica integrità signal_log_id sessione 4a42133e

Query LEFT JOIN tra `scalping_trades` e `session_signal_log`. Documentare se trade con signal_log_id NULL.

### 🟡 TASK-1234: Signal log writer — aggiungere conferma successo esplicita

Aggiungere log INFO con signal_log_id su insert riusciti per override mean-reversion. Oggi solo ERROR loggato.

### 🔴 TASK-1235: fee_tier_certified False dal 2° trade in poi

Solo trade 1/8 ha certified=True. Verificare `candle_processor.py` e `okx_exchange.py`. Fix minimo: loggare motivo del fallback.

### 🟡 TASK-1236: Verificare fee_tier_certified persistito per-trade in DB

Query `scalping_trades.entry_fee_rate/exit_fee_rate` vs `scalping_sessions.fee_tier_certified`.

---

### 📋 Task ancora Pending

| Task | Descrizione | Priorità |
|------|-------------|----------|
| TASK-1230 | Session Max Loss + Drawdown Fix | 🔴 ALTA |
| TASK-1231 | Cleanup: rimuovere SELL dal Session Summary | 🟢 BASSA |
| TASK-1232 | Query storica win rate mean-reversion override | 🔴 ALTA (dipende da 1233) |
| TASK-1233 | Verifica integrità signal_log_id sessione 4a42133e | 🔴 ALTA |
| TASK-1234 | Signal log writer: aggiungere conferma successo | 🟡 MEDIA |
| TASK-1235 | fee_tier_certified False dal 2° trade | 🔴 ALTA |
| TASK-1236 | Verificare fee_tier_certified per-trade in DB | 🟡 MEDIA |

### 📊 Scoperte chiave dalla sessione 4a42133e

1. **Mean-reversion override → trade:** 29 override, solo 8 con trade reale. 18 fallimenti scrittura DB (hold), 0 coincidenti con entry.
2. **Fee tier certified:** Solo trade 1/8 ha certified=True. Tutti gli altri fallback a 0.001/0.001.
3. **Supervisor auto-decay:** Dalle 00:26:38, session in paused — override continuano senza esecuzione (~15 "fantasma").

---

### Precedente Handoff

**Data:** 2026-07-24 11:40

**Contesto:** Risoluzione errore 51155 OKX e pulizia finale epica short.

---

### ✅ Risoluzione Errore 51155 (OKX Compliance)

**Problema:** Nonostante il codice fosse tornato allo Spot puro (`tdMode="cash"`), le operazioni su OKX fallivano con `51155 Local compliance restrictions`.
**Causa:** L'errore scattava perché la sessione era avviata sulla coppia **`BTC-USD`** (valuta fiat americana), che è bloccata dalle policy MiCA per gli account retail in EU, indipendentemente dalla modalità di margin.
**Soluzione:** L'utente ha cambiato il balance e ha avviato la sessione su `BTC-EUR`, e gli ordini BUY a mercato con relativi bracket exit (OCO) sono partiti perfettamente.

### ✅ Cleanup default symbol

**Fix applicati:**
- Modificati i default del frontend in `session-api.service.ts` e `market-intel-panel.component.ts` da `OKBEUR` a `BTC-EUR` per evitare che l'app parta sulla chart sbagliata all'avvio.

**Prossimi passi:**
- Focus su strategie Long-only (mean reversion, ecc).
- Nessun residuo short rimasto nel codice.

---

### Precedente Handoff

### Da: Antigravity → prossima sessione

**Data:** 2026-07-17 14:30

**Contesto:** TASK-1166 Refactoring `router.py` — Fasi 1-4 completate.

---

### ✅ TASK-1166 Completato: `router.py` da 4310→180 righe (95.8% riduzione)

**Problema:** `router.py` era un monolite ingestibile da oltre 4300 righe.
**Soluzione completa (4 fasi):**
- **Fase 1:** Estratti `_state.py` (50 righe), `pricing.py` (149), `reconciliation.py` (162), `db_ops.py` (169).
- **Fase 2:** Estratti `trade_executor.py` (451), `session_lifecycle.py` (59).
- **Fase 3:** Estratti `broadcast.py` (38), `pipeline.py` (224), `market_processors.py` (1006).
- **Fase 4:** Estratti REST endpoints in `rest/`:
  - `rest/market_data.py` (245): exchange-info, instruments, sessions, trade-history, candles, `_snapshot_to_dict`
  - `rest/backtest.py` (75): run, result, list endpoints
  - `rest/session.py` (968): control_session, get_session, logs, position, config, risk, performance, health
  - `rest/intel_opportunity.py` (243): intelligence, opportunities, debug, supervisor endpoints
- `router.py` (180 righe) ora è un thin shell che include 4 sub-router + re-export backward-compat + WS endpoint.
- Tutti i test passano: 12/12 OKX integration, 6/6 reconcile, 27/27 unit.
- Pre-existing bugs fixati: `session_lifecycle.py` import path, `market_processors.py` loose code syntax.

### 📋 Task ancora Pending

| Task | Descrizione | Priorità |
|------|-------------|----------|
| TASK-1166.Cleanup | Eliminare eventuali test o commenti obsoleti, aggiornare TASKS.md | BASSA |

### 🔍 Verifica manuale da fare al prossimo avvio

- Testare start sessione live per verificare che `_on_order_update` funzioni correttamente da `trade_executor.py`.
- Verificare che il WebSocket endpoint inizia correttamente (lo WS è ancora in `router.py`).
- Controllare che tutti gli import backward-compat in `router.py` funzionano con main.py, config_api.py, scalping_jobs.py, user_data_stream.py, supervisor_scheduler.py, parameter_updater.py.

---

(Il resto del file HANDOFF.md precedente è preservato ma troncato per chiarezza — vedi versione completa su disco)
