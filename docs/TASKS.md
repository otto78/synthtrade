# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-08-05. Task completati in `docs/ARCHIVE_TASKS.md`.

---

### TASK-1248 — Trailing stop: reason errata nei log (Stop Loss Trailing in verde) ✅ Completato

> **Priorità:** MEDIA (telemetria/log — nessun impatto sulla logica di trading).
> **File:**
>   - Backend: `scalping/trade_executor.py`, `scalping/reconciliation.py`, `scalping/pipeline.py`, `scalping/db_ops.py`, `scalping/rest/market_data.py`, `main.py`
>   - Frontend: `trade-log.component.ts`, `logs.page.ts`, `logs.model.ts`, `scalping-ws.service.ts`

**Problema**: i trade chiusi da trailing stop apparivano nei log come "Take Profit" invece che come "Stop Loss Trailing (step N)" in verde. Root cause: il blocco di determinazione reason in `_on_order_update` confrontava `fill_price >= entry` → `take_profit`, ignorando che uno stop ricalcato (amended) può chiudere in profitto. Confermato via API OKX (`orders-algo-history`): i bracket trailing hanno `actualSide="sl"`, non TP.

**Implementato:**
- Backend: nuova `_resolve_close_reason()` position-aware in `trade_executor.py` — TP solo se il fill è al livello `pos.tp_price` (±0.1%) o leg/order-id TP; altrimenti `stop_loss_trailing` (trailing_step ≥ 1), `stop_loss_breakeven` (BE attivo), `stop_loss`; fallback legacy su entry_price.
- `trailing_step` propagato in: trade_record, broadcast `trade_closed`, `_on_uds_reconnect_sync`, `_close_position_and_record`, `_reconcile_position_with_exchange`/`_matched_bracket_fill` (reason `stop_loss_trailing`/`stop_loss_breakeven`), restore `pipeline.py`, `_update_closed_position_in_db` (DB), API trade-history (`market_data.py`), restore (`main.py`).
- Frontend: `formatReason(reason, trailingStep)` → label `Stop Loss Trailing (step N)` se step > 0; CSS `.reason-trailing` verde (`#26a69a`); `TradeClosedEvent.trailing_step?: number` e `LogEntry.trailing_step?: number`.
- DB retroattivo: sessione `d253c56e` — `d595f87b` (step 2) e `f7aa9ee4` (step 1) → `signal_reason='stop_loss_trailing'` (verificati via OKX `actualSide="sl"`).
- Verifica: 44/44 test backend verdi + `tsc --noEmit` ok.

---

### TASK-1247 — Position ticker: SL dinamico con segno e stati colore (BE→giallo, trailing→verde) ✅ Completato

> **Priorità:** MEDIA (UI/telemetria — nessun impatto sulla logica di trading).
> **File:**
>   - Backend: `candle_processor.py`, `router.py`, `scalping/rest/position.py`
>   - Frontend: `position-ticker.component.ts`, `position.model.ts`, `scalping-ws.service.ts`

**Problema**: la tab Stop Loss mostrava la percentuale di config (es. `(0.50%)`) senza segno e non cambiava mai quando lo SL veniva amendato da break-even/trailing. `trailing_step` non veniva inviato dal backend (impossibile distinguere BE da trailing) e lo stato `profit_lock_active` si perdeva al refresh pagina.

**Implementato:**
- Backend: payload `position`/`position_update`/REST arricchiti con `trailing_step`, `profit_lock_active` (iniziale/restore) e `sl_net_pct` = rendimento netto % effettivo al prezzo SL corrente (`_expected_net_pct_at_exit`, fee-adjusted). Aggiunti anche a `position` di apertura live.
- Frontend: `formatSlPct()`/`formatTpPct()` (segno `-`/`+`, senza parentesi, 2 decimali), `isTrailing()` (step ≥ 1). Tab SL: rossa → gialla (BE, `lock-active`) → verde (trailing, `trailing-active`). Font percentuali 10→13px bold. Messaggio sotto la progress bar: giallo per BE, verde "Trailing Stop attivo — Step N · profitto protetto a +X.XX%" per trailing.
- Fix mapping WS/REST: `stop_loss_pct_net`/`take_profit_pct_net`/`sl_net_pct`/`trailing_step` ora propagati nel componente (prima `_net` e `sl_net_pct` non venivano mappati → la percentuale restava statica).
- Verifica: `tsc --noEmit` ok + 38/38 test backend verdi.

---

### TASK-1244 — Reconcile OKX: correlazione OCO stretta post-offline ✅ Completato

> **Priorità:** CRITICA — impedisce che una vendita di un altro trade/sessione chiuda una riga DB errata.
>
> **Fix:** la riconciliazione ora segue `exchange_bracket_id`/`algoId` → `orders-algo-history` → `ordId` figlio → `/trade/fills?ordId=…`. I fill vengono aggregati con prezzo medio ponderato e usano il `fillTime` reale. Sono stati eliminati sia il fallback per lato SELL sul simbolo sia la chiusura fittizia a entry price. Se il fill OCO non è ancora verificabile, il trade rimane aperto localmente per un retry sicuro.
>
> **Compatibilità futura:** questa identità è specifica del trade e non del simbolo; evita collisioni quando più sessioni opereranno sullo stesso strumento.

---

## 🔴 FASE 1 — Bug Critici e Pulizia (EV Fix)

> **Contesto**: analisi di 5 sessioni live (24/07–03/08/2026) ha dimostrato EV = -0.236%/trade.
> Causa: 2 bug di codice critici + 2 problemi strutturali che rendono il sistema incapace
> di operare profittevolmente. Queste task DEVONO essere completate prima di qualsiasi
> altra espansione (multi-session, nuove strategie, ecc.).
> Riferimento: `analisi_sessioni.md` nell'artifact directory di questa sessione.

---

### TASK-1238 — Fix VWAP Reversion: logica BUY/SELL invertita ✅ Completato

> **Priorità**: CRITICA — la strategia vwap_reversion genera segnali opposti a quelli attesi
> **File**: `synthtrade/backend/app/scalping/strategies/vwap_reversion.py`
>
> **Problema**: La strategia emette BUY quando `prezzo > VWAP + 0.2%` (breakout/momentum)
> invece di emettere BUY quando `prezzo < VWAP - 0.2%` (reversion al dip, comportamento
> corretto per una strategia mean-reversion). La logica è esattamente invertita.
> In un mercato in trend rialzista, la logica attuale entra già dopo un movimento fatto;
> in un mercato laterale/ribassista entra contro il movimento, amplificando le perdite.
>
> **Fix**: Invertire le condizioni BUY/SELL nella strategia.
> **Nota**: i segnali SELL vengono già bloccati dall'aggregator, ma vanno rimossi dal codice
> per pulizia (vedi TASK-1240).
> **Acceptance**: unit test che verifica che BUY venga emesso con price < VWAP e non viceversa.

---

### TASK-1239 — Fix btc_change_24h_pct: campo OKX "chg" inesistente ✅ Completato

> **Priorità**: CRITICA — il supervisor e il regime detector ricevono sempre 0% di variazione
> 24h, rendendo il contesto macro cieco per tutte le decisioni di sessione.
> **File**: `synthtrade/backend/app/execution/okx_exchange.py` (~L.430-480)
>
> **Problema**: L'API OKX `/api/v5/market/ticker` non restituisce un campo `"chg"`.
> Il codice fa `ticker.get("chg") or 0.0` che produce sempre 0.
> I campi reali che OKX restituisce sono `"last"` e `"open24h"`.
>
> **Fix**:
> ```python
> last = float(ticker.get("last") or 0)
> open24h = float(ticker.get("open24h") or 0)
> change_24h_pct = ((last - open24h) / open24h * 100) if open24h > 0 else 0.0
> ```
> **Acceptance**: valore non-zero e coerente con il mercato al momento dell'esecuzione.

---

### TASK-1240 — Rimuovere generazione segnali SELL dalle strategie ✅ Completato

> **Priorità**: ALTA — i segnali SELL vengono già bloccati nell'aggregator, ma le strategie
> li generano ancora internamente causando rumore computazionale e potenziali distorsioni
> nelle metriche del supervisor (che vede segnali che poi non esegue).
> **File**:
>   - `synthtrade/backend/app/scalping/strategies/momentum_base.py`
>   - `synthtrade/backend/app/scalping/strategies/vwap_reversion.py`
>
> **Problema**: In Europa non è consentito lo short selling in spot. I segnali SELL/SHORT
> sono permanentemente disabilitati nell'aggregator (`signal_aggregator.py` log:
> "SELL signals are permanently disabled"). Tuttavia le strategie continuano a generarli,
> sprecando cicli e inquinando le metriche del supervisor AI.
>
> **Fix**: In entrambe le strategie, sostituire i blocchi `if price < threshold: signal = SELL`
> con un segnale `WAIT` o semplicemente `return None`. Mantenere solo la logica BUY.
> **Acceptance**: le strategie non emettono mai `TechnicalSignal(type="SELL")`.

---

### TASK-1241 — Persistere signal_score e intelligence fields nel DB ✅ Completato

> **Priorità**: ALTA — senza questi dati non è possibile analizzare la correlazione tra
> qualità del segnale e outcome del trade, né implementare filtri basati su score minimo.
> **File**: `synthtrade/backend/app/scalping/db_ops.py` (funzione `_save_open_position_to_db`)
>
> **Problema**: I seguenti campi esistono nella tabella `scalping_trades` ma sono sempre NULL
> perché non vengono passati al momento del salvataggio del trade:
>   - `signal_score` (punteggio composito dell'intelligence layer, range -100/+100)
>   - `funding_rate_at_entry` (funding rate OKX al momento dell'ingresso)
>   - `fear_greed_at_entry` (indice Fear&Greed al momento dell'ingresso)
>   - `cvd_trend_at_entry` (trend CVD: "bullish"/"bearish"/"neutral")
>   - `regime_classified` (regime classificato dal regime_detector: trending_up/down/ranging)
>
> **Fix**: Aggiungere questi campi al dict `supervisor_context` che viene passato a
> `_save_open_position_to_db`, e includerli nella `insert_data` nel DB.
> Verificare che i valori siano disponibili nel router al momento dell'apertura trade.
> **Acceptance**: dopo un trade live, questi campi sono non-NULL nel DB.

---

## 🟠 FASE 2 — Trend Filter (dopo completamento Fase 1)

> **Contesto**: Fase 2 può iniziare solo dopo che la Fase 1 è validata con ≥10 trade live.
> Il filtro trend è la modifica con il maggiore impatto atteso sul win rate (+15-20%).

---

### TASK-1242 — Trend Filter: bloccare BUY quando BTC sotto EMA20 4h ✅ Completato

> **Priorità**: ALTA (Fase 2)
> **File**: `synthtrade/backend/app/scalping/engine/signal_aggregator.py`
>          oppure `engine/regime_detector.py`
>
> **Problema**: Il sistema entra long indipendentemente dalla direzione del trend di medio
> termine. Nel periodo 27/07-03/08, BTC è sceso da 57.600€ a 53.000€ e il sistema ha
> continuato ad aprire long durante tutta la discesa, totalizzando 19 perdite su 24 trade.
>
> **Fix**: Prima di autorizzare ogni segnale BUY, verificare:
>   1. BTC price > EMA20 calcolata sulle ultime 20 candele 4h
>   2. btc_change_1h_pct > -0.5% (non comprare in forte discesa oraria)
> Se una delle condizioni non è soddisfatta → segnale WAIT (non BUY).
>
> **Dati necessari**: candlestick 4h già disponibili (verificare nel signal engine).
> **Acceptance**: nessun BUY viene autorizzato quando BTC è sotto EMA20 4h.

---

## 🟡 FASE 3 — Revisione TP/SL (dopo validazione Fase 2)

> **Contesto**: Da avviare dopo almeno 20 trade con Fase 1+2 attive e EV stimato positivo.

---

### TASK-1243 — Stop protettivo OCO dopo break-even ✅ Completato

> **Priorità**: ALTA (Fase 3)
> **Piano tecnico**: `docs/plans/phase3-trailing-sl.md`
> **Completato:** 2026-08-04
>
> **Implementazione:** Feature completa implementata e validata in produzione.
> - `app/scalping/break_even.py` — modulo autonomo con logica trigger, amend OKX, lock async, persistenza
> - `execution/okx_exchange.py` — `amend_exit_bracket_stop_loss()` con doppio check `code`+`sCode`
> - `execution/exchange_models.py` — metodo aggiunto al protocollo `ExchangeAdapterProtocol`
> - `execution/exchange.py` — stub Binance che solleva `NotImplementedError`
> - `scalping/db_ops.py` — `_update_break_even_in_db()` filtra solo per `exchange_bracket_id`
> - `scalping/config_loader.py` — chiavi `BREAK_EVEN_*` con feature flag `BREAK_EVEN_ENABLED`
> - `scalping/candle_processor.py` — chiamata trigger + campo `profit_lock_active` nel broadcast WS
> - `main.py` — restore dei 3 campi break_even dal DB per impedire doppio amend dopo restart
> - `tests/test_task_1243.py` — 22 test tutti verdi
> - Migration DB: `break_even_triggered`, `break_even_activated_at`, `break_even_sl_price` su `scalping_trades`
>
> **Prova live eseguita 2026-08-04** (sessione `6701e55b`, algoId `3802582373171404800`):
> - entry 55154.6 EUR → trigger a 55368.0 EUR (+0.19% netto) → SL amendato da 54988.75 a 55292.70
> - Trade chiuso a 55291.0 EUR → **PnL +0.01 EUR (+0.05%)** invece di un'eventuale perdita di ~-0.06 EUR
> - Senza break-even: SL a 54988, perdita attesa -0.30% netto. Delta salvato: **+0.07 EUR sul trade**

---



### TASK-1246 — Trailing stop progressivo post break-even (OCO OKX) 🟡 In corso

> **Priorità**: ALTA (Fase 3 — dopo TASK-1243 validato in produzione).
> **Piano**: `docs/plans/trailing-stop-progressive.md`.
> **Stato**: implementazione completata e committata; migration `trailing_step` applicata; GATE pre-live pendente.

**Implementato (commits `0bc59b0`, `68eddb5`):**
- `break_even.py` — `_check_and_apply_trailing()` con step progressivi post-BE, guard dinamico
  `next_trigger < tp_net - safety_margin` (immune a cambio TP a runtime), `sl_price` come fonte di verità al restore
- `config_loader.py` — `TRAILING_ENABLED`(false), `TRAILING_STEP_NET_PCT`(0.15), `TRAILING_BUFFER_NET_PCT`(0.10),
  `TRAILING_SAFETY_MARGIN_NET_PCT`(0.10)
- `position_manager.py` — `trailing_step: int = 0` (solo telemetria/UI)
- `db_ops.py` — `_update_trailing_in_db()` filtrato per `exchange_bracket_id` (dedup funzione duplicata)
- `main.py` — restore `trailing_step` dal DB (mai ricalcolato da step count)
- `candle_processor.py` — `_wait_for_fill()` polling del fill asincrono OKX prima del bracket (fix sCode 51008)
- `core/logging.py` — filtro rumore asyncio WinError 10054 (WS reconnect già loggato dai client)
- Frontend — banner step-aware (poi semplificato), reason `stop_loss_trailing`, campo `trailing_step` nel WS
- `scripts/test_okx_amend_rate.py` — spike 6 amend consecutivi su OKX Demo
- Migration DB: `scalping_trades.trailing_step int NOT NULL DEFAULT 0` (applicata 2026-08-05)
- Test: 38/38 verdi (`test_wait_for_fill.py` + `test_task_1243.py`)

**Config runtime attuale (DB):** `BREAK_EVEN_ENABLED=true`, `TRAILING_ENABLED=true`.

**GATE pre-live pendenti:**
1. Eseguire `scripts/test_okx_amend_rate.py` su OKX Demo → nessun HTTP 429 né sCode rate-limit su 6 amend consecutivi
2. Validazione statistica: ≥20 trade con trailing attivo prima di considerare la feature stabile
3. Query storica sui TP (p25 gross_pct < 0.45%?) per confermare `TRAILING_STEP_NET_PCT=0.15`

---

### BUG-2026-08-03 — Fix reconcile exit_time timestamp OKX + frontend date display ✅ Completato

> **Stato:** Completato il 03/08/2026.
> - **Backend `okx_exchange.py` L.745**: OKX `/api/v5/trade/fills` usa `ts` (non `fillTime`) come timestamp. L'adapter mappava `fill.get("fillTime")` (sempre `None`), causando il fallback di `exit_time` a `datetime.now()` (reconcile time) invece della data/ora reale del fill OKX post-riavvio weekend. Risolto con `fill.get("fillTime") or fill.get("ts")`.
> - **Frontend `logs.page.ts` L.184**: La tabella trade nella vista sessioni mostrava solo `HH:mm` invece di `dd/MM/yy HH:mm` per `entry_time`. Rinominata anche l'intestazione da `Ora` a `Data/Ora` per coerenza con il tab Storico Trade.

---

### TASK-1245 — Riparazione controllata storico trade OCO OKX ✅ Completato

> **File:** `scripts/repair_okx_trade_history.py`
>
> Il job opera in due fasi: dry-run JSON obbligatorio e applicazione esplicita del report. Corregge solo trade collegabili senza ambiguità a `exchange_bracket_id`/`oco_order_list_id` e al fill del child order. Non usare `--apply` prima di avere verificato il report.

---

### TASK-1166 — Consolidamento a 3 Strategie Runtime ✅ Completato

> **Stato:** Tutte le fasi completate il 30/07/2026.
> - **Fase 1**: 6 chiavi `REGIME_STRATEGY_*` / `REGIME_ALLOWED_*` inserite in `scalping_runtime_config` (DB override)
> - **Fase 2**: Default hardcoded aggiornati in `config_loader.py`, `strategy_selector.py`, `supervisor_scheduler.py`
> - **Fase 3**: Dropdown frontend ridotto a 3 opzioni (EMA Cross, RSI+Bollinger, VWAP Reversion), default `vwap_reversion`
> - **Fase 4**: `docs/plans/okx-sl-tp-recalibration-task.md` marcato come superato (fee reale 0,20% round-trip)
> - **Prossimo**: Fase 4.1/4.2 (osservazione post-cambio) — dopo 15-20 trade con nuovo mapping

---

### Punto 4 (pesi signal score) — 🟡 Fermo

> **Stato:** Confermato nessuna azione da intraprendere ora — coerente con TASK-1159 bloccato. Resta in attesa di revisione pesi futura.
