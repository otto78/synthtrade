# SynthTrade — EPICA Short Selling OKX Spot Margin (versione combinata)

> **Data:** 22 luglio 2026
> **Stato:** design completo, zero codice. Pronta per apertura task.
> **Fonti:** `docs/architecture/okx-short-selling-architecture.md`, `docs/analysis/2026-07-21_okx-short-timestop-design.md`, `docs/recap/2026-07-21_okx-short-selling-analysis-recap.md`
> **Origine di questo file:** fusione di due breakdown indipendenti generati in parallelo (Claude + opencode/Big Pickle) sulla stessa architettura, confrontati riga per riga e uniti prendendo il meglio di entrambi.
> **Numerazione:** `TASK-1220` → `TASK-1233`, coerente con lo schema numerico già in uso nel progetto (TASK-1100+ OKX, TASK-1150+ collector, TASK-1200+ Bybit). Evita il prefisso alternativo `TASK-SHORT-XXX` usato in una delle due bozze, per restare coerente con `docs/TASKS.md`.
> **Principio guida non negoziabile:** "one change at a time". Fase 1 = MVP con bracket mirrorato e time-stop **fisso** (48h), zero formula dinamica. Fase 2 (interesse dinamico, Layer 3-6) parte solo dopo aver osservato trade reali. Nessuna fase salta la precedente.
> **Gate bloccante:** TASK-1220 è l'unico prerequisito reale di tutta l'epica. Se lo spike read-only non conferma `enableSpotBorrow=true` e almeno un simbolo con `max-loan>0`, l'epica si ferma e va rivalutata — non si scrive codice attorno a un prerequisito non confermato.

---

## 0. Cosa è cambiato rispetto alle due bozze di partenza

Le due bozze indipendenti coprivano lo stesso terreno con enfasi diverse. Questa versione integra:

| Da dove | Cosa | Perché tenerlo |
|---|---|---|
| Bozza "opencode" | Riferimenti `file:riga` precisi sul codice reale (`candle_processor.py:338-355`, `pricing.py:83-136`, `_state.py:14`, ecc.) | Grounding concreto post-refactor TASK-1166 — evita di scrivere pseudocodice scollegato dalla struttura modulare attuale |
| Bozza "opencode" | Modulo a **funzioni pure** `short_timestop.py` per le formule Layer 3-6, testabile senza mock | Le funzioni pure sono più facili da verificare in isolamento — stesso principio già usato per `resolve()` in WalletOrchestrator (Binance, ora superseded, ma il pattern resta valido) |
| Bozza "opencode" | Task dedicato **paper mode short** (TASK-1225.bis, ex 010) | La maggior parte dei test nel progetto passa da paper mode prima del demo/live — mancava del tutto nella mia bozza originale |
| Bozza "opencode" | Metodi adapter con firme esplicite (`get_max_loan`, `get_interest_rate`, `get_position_tiers`, `get_account_config`) e verifica `acctLv` | Più actionable per chi implementa |
| Bozza Claude | Decisione di prodotto esplicita: short **solo trend-following** vs anche mean-reversion | Rischio concreto se non deciso prima di scrivere `SignalAggregator` — lasciato aperto nella bozza opencode |
| Bozza Claude | Nota esplicita sul rischio CHECK constraint DB (già successo **due volte**: `mode='TEST'` TASK-1116.D, `rejected_short_unsupported` TASK-1117) | Pattern di errore ricorrente nel progetto, va prevenuto proattivamente per i nuovi `decision_type`/`exit_reason` introdotti qui |
| Bozza Claude | TASK-1231 esplicito su TASK-908 (resume guard bearish) — con short disponibile la guard va **disattivata/adattata**, non lasciata come dead weight | Impatto diretto su un comportamento già in produzione, nessuna delle due bozze lo aveva collegato esplicitamente all'inizio |
| Bozza Claude | Formule Layer 1-6 spellate per intero con i valori numerici del design doc | Evita che chi implementa debba tornare al doc originale per i numeri |
| Entrambe | Struttura dipendenze, fasi, acceptance criteria | Consolidate in un unico grafo |

---

## 1. Mappa dipendenze (unificata)

```text
TASK-1220 (spike read-only — BLOCCANTE)
  │
  ├─→ TASK-1221 (check disponibilità short — backend + frontend badge)
  ├─→ TASK-1222 (adapter margin methods + tdMode parametrico)
  ├─→ TASK-1226 (DB migration — parallelizzabile, default safe)
  │
  TASK-1222 ─→ TASK-1223.a (session config short_enabled)
             ─→ TASK-1223.b (SignalAggregator gate + decisione trend-following/mean-reversion)
                  │
                  ▼
            TASK-1224 (apertura short MVP)
                  │
                  ▼
            TASK-1225 (chiusura short + time-stop 48h fisso)
                  │
     ┌────────────┼────────────┬──────────────┬──────────────┐
     ▼            ▼            ▼              ▼              ▼
TASK-1225.bis TASK-1227    TASK-1228      TASK-1231      TASK-1232
(paper mode)  (frontend)   (test integr.) (supervisor)   (risk manager)
     │            │            │
     └────────────┴────────────┘
                  ▼
            TASK-1229 (E2E demo/live minimo)
                  │
                  ▼  (solo dopo dati reali osservati)
            TASK-1230 (Fase 2 — time-stop interest-based, Layer 3-6)
                  │
                  ▼
            TASK-1233 (housekeeping doc)
```

**Parallelizzabile dopo TASK-1220:** TASK-1221, TASK-1222, TASK-1226 possono partire insieme.
**Parallelizzabile dopo TASK-1225:** TASK-1225.bis, TASK-1227, TASK-1228, TASK-1231, TASK-1232.

---

## 2. TASK-1220 — Spike read-only OKX Margin Account

**Status:** Pending
**Priorità:** 🔴 CRITICA — bloccante per tutta l'epica
**Dipendenze:** nessuna
**Stima:** 2-3h
**Tipo:** Spike bloccante, sola lettura
**Non modificare:** codice runtime, DB, frontend

### Obiettivo

Verificare empiricamente, sul conto OKX reale, tutti i prerequisiti tecnici per lo short prima di scrivere qualunque riga di codice runtime. **Nessuno di questi endpoint è mai stato chiamato sul conto reale.**

### Endpoint da chiamare (solo GET, nessun ordine)

| # | Endpoint | Verifica | Fonte |
|---|----------|----------|-------|
| 1 | `GET /api/v5/account/config` | `enableSpotBorrow=true`? `acctLv` (account mode) compatibile con margin? | entrambe |
| 2 | `GET /api/v5/account/max-loan?instId=BTC-EUR&mgnMode=isolated` | BTC borrowable? Limite massimo? | entrambe |
| 3 | `GET /api/v5/account/max-loan?instId=OKB-EUR&mgnMode=isolated` | OKB borrowable? (probabile **no** — token nativo exchange, mercato prestito sottile) | entrambe |
| 4 | `GET /api/v5/public/interest-rate-loan-quota?ccy=BTC` | Tasso APR reale BTC — pubblico, nessuna auth | entrambe |
| 5 | `GET /api/v5/public/interest-rate-loan-quota?ccy=OKB` | Tasso APR reale OKB (se borrowable) | entrambe |
| 6 | `GET /api/v5/public/interest-rate-loan-quota?ccy=ETH` | Tasso APR reale ETH (terzo simbolo di confronto) | Claude |
| 7 | `GET /api/v5/account/position-tiers?instType=MARGIN&instId=BTC-EUR` | Maintenance margin ratio reale per tier di posizione — necessario per collaterale minimo | opencode (path confermato) |
| 8 | `GET /api/v5/account/leverage-info?instType=MARGIN&ccy=BTC` | Leva attualmente impostata (baseline prima di modificarla) | opencode |
| 9 | `GET /api/v5/account/positions?instType=MARGIN` | Formato reale campo `posCcy`, `mgnRatio` — verificare che risponda anche senza posizioni aperte | Claude |
| 10 | `GET /api/v5/account/quick-margin-borrow-repay-history` | Formato risposta storico borrow/repay (anche vuoto) | Claude |
| 11 | `GET /api/v5/account/interest-limits` | Eventuale quota interest-free applicabile all'account mode attuale | Claude |

### Sottotask

- [ ] **1220.A** — `enableSpotBorrow` e `acctLv` via `/account/config`
- [ ] **1220.B** — `max-loan` per almeno 3 simboli (BTC-EUR, ETH-EUR, OKB-EUR) — **OKB è il candidato più a rischio**
- [ ] **1220.C** — Tasso APR reale per BTC/ETH/OKB via `interest-rate-loan-quota` — sostituisce il 15% illustrativo del design doc
- [ ] **1220.D** — Leva di default via `leverage-info` per almeno un simbolo
- [ ] **1220.E** — Formato `posCcy`/`mgnRatio` da `/account/positions?instType=MARGIN`
- [ ] **1220.F** — `position-tiers` per BTC-EUR — maintenance margin ratio reale
- [ ] **1220.G** — Risposta (anche vuota) di `quick-margin-borrow-repay-history` e `interest-limits`
- [ ] **1220.H** — **Gate pre-apertura** con i tassi reali appena raccolti: verificare se `(rate_hourly × 24h) < SL_gross_fee_only (≈0.35%)` per almeno un simbolo. Se il gate fallisce per tutti i simboli testati, l'epica si ferma qui.
- [ ] **1220.I** — Se `BTC-EUR` non risulta disponibile in margin su EU, provare fallback su coppie USDT

### File da creare

- `scripts/test_okx_short_spike.py` — script isolato, read-only, fuori dal runtime SynthTrade (stesso pattern di `test_okx_demo.py`)
- `docs/analysis/okx-short-spike-results.md` — stesso formato di `okx-demo-spike-results.md`: tabella (asset, borrowable sì/no, limite max, APR reale, maintenance margin ratio, leva attuale) + raccomandazione simbolo di test
- `docs/analysis/okx-short-spike-results.json` — payload raw

### Acceptance Criteria

- Tutti gli 11 endpoint chiamati e documentati con payload reali
- Almeno un simbolo confermato borrowable con `max-loan > 0`
- Gate pre-apertura (1220.H) verificato con numeri reali, non con l'APR illustrativo
- Se OKB non è borrowable: non è un problema, va solo documentato (lo short si abilita solo su un sottoinsieme di simboli)
- **Blocco esplicito:** se `enableSpotBorrow=false` o nessun simbolo ha `max-loan>0`, l'epica si ferma — apre una nota di rivalutazione strategica, non si procede a TASK-1221+
- Nessun codice runtime modificato

### Rischi

- Account non abilitato al margin → serve attivazione manuale da UI OKX
- BTC-EUR non disponibile in margin su EU → provare USDT pairs
- OKB non borrowable → non bloccante, solo da documentare

---

## 3. TASK-1221 — Check disponibilità short per simbolo (feature pre-sessione)

**Status:** Pending
**Priorità:** 🔴 Alta
**Dipendenze:** TASK-1220
**Stima:** 3-4h

### Obiettivo

Al momento della selezione simbolo (stesso punto del flusso già usato da TASK-1116.G, instrument discovery environment-aware), mostrare se lo short è disponibile e a che tasso. Evita di scoprirlo solo dopo aver avviato la sessione con segnali SELL sistematicamente bloccati.

### File coinvolti (grounding dal codice reale)

- `synthtrade/backend/app/execution/okx_exchange.py` → `list_instruments()` (riga ~359)
- `synthtrade/backend/app/scalping/rest/market_data.py` (endpoint `/exchange/instruments`, post-refactor TASK-1166)
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/exchange-symbols.service.ts` (riga ~18, modello `ExchangeInstrument`)
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts` (righe ~39-93)

### Sottotask

- [ ] **1221.A** — `OkxExchangeAdapter.get_short_availability(symbol: SymbolRef) -> ShortAvailability` — chiama `max-loan` + `interest-rate-loan-quota`, ritorna `{available: bool, borrow_rate_apr: float | None, max_loan_qty: float | None}`
- [ ] **1221.B** — Estendere `GET /api/scalping/exchange/instruments` con `short_available: bool` e `short_borrow_rate_apr: float | None` per strumento, calcolato **una volta per ciclo di discovery**, non ad ogni selezione
- [ ] **1221.C** — Cache environment-aware (demo/live), stessa politica già usata in TASK-1116.G — chiavi separate per ambiente
- [ ] **1221.D** — Frontend: `shortAvailable?: boolean` e `shortBorrowRateApr?: number` sul modello `ExchangeInstrument`
- [ ] **1221.E** — Frontend: badge dopo il selettore simbolo in `session-controls.component.ts` — ✅ "Short disponibile — X% APR" oppure ⚠️ "Short non disponibile per questo simbolo"
- [ ] **1221.F** — `ShortAvailability` model in `exchange_models.py`, provider-neutral (Binance ritorna sempre `available=False`)

### Test (TDD)

- [ ] `test_get_short_availability_success` — max-loan>0 → `available=True` con rate popolato
- [ ] `test_get_short_availability_zero_max_loan` — max-loan=0 → `available=False`
- [ ] `test_get_short_availability_endpoint_error` — errore rete → `available=False`, nessuna eccezione propagata
- [ ] `test_instruments_endpoint_includes_short_fields`
- [ ] `test_cache_environment_aware_demo_vs_live`
- [ ] `test_badge_renders_available_with_apr` / `test_badge_renders_unavailable` (frontend, mock payload)

### Acceptance Criteria

- Selezionando un simbolo con `max-loan=0`, l'utente vede il badge di non disponibilità **prima** di avviare la sessione
- Nessuna chiamata di rete ripetuta ad ogni render — cache per ciclo di discovery
- Il check non impatta le prestazioni della sessione

---

## 4. TASK-1222 — OkxExchangeAdapter: metodi margin/short + tdMode parametrico

**Status:** Pending
**Priorità:** 🔴 Alta
**Dipendenze:** TASK-1220
**Stima:** 4-5h

### Obiettivo

Estendere l'adapter esistente con i metodi necessari al margin trading, riusando l'infrastruttura REST-only già presente (TASK-1164, no CCXT) e parametrizzando ciò che oggi è hardcoded per lo spot puro.

### File coinvolti

- `synthtrade/backend/app/execution/okx_exchange.py`
- `synthtrade/backend/app/execution/exchange_models.py`
- `synthtrade/backend/tests/integration/fake_okx_adapter.py`

### Sottotask

- [ ] **1222.A** — Parametrizzare `tdMode` in `_direct_place_market_order` (riga ~559) e `_direct_place_exit_bracket` (riga ~801) — oggi hardcoded `"cash"`, deve accettare `"isolated"` quando richiesto
- [ ] **1222.B** — Parametrizzare `instType` in `get_symbol_rules()` (riga ~334) — oggi hardcoded `"spot"`, per margin serve poter chiamare con `"margin"`
- [ ] **1222.C** — `get_account_config() -> dict` — `GET /api/v5/account/config`, ritorna `enableSpotBorrow`, `acctLv`
- [ ] **1222.D** — `get_max_loan(inst_id, mgn_mode) -> float` — `GET /api/v5/account/max-loan`
- [ ] **1222.E** — `get_interest_rate(ccy) -> float` — `GET /api/v5/public/interest-rate-loan-quota`
- [ ] **1222.F** — `get_position_tiers(inst_id) -> dict` — `GET /api/v5/account/position-tiers?instType=MARGIN`
- [ ] **1222.G** — `set_leverage(symbol, leverage, mgn_mode="isolated")` — `POST /api/v5/account/set-leverage`. **Nota:** la leva si imposta per **valuta** (`ccy`), non per coppia — confermare parametro esatto dallo spike
- [ ] **1222.H** — `get_leverage_info(symbol, mgn_mode="isolated")` — GET, da chiamare prima di ogni `set_leverage` per evitare chiamate ridondanti
- [ ] **1222.I** — `get_margin_positions() -> list[MarginPosition]` — `GET /api/v5/account/positions?instType=MARGIN`, mappa `posCcy` → `side` (posCcy=quote → SHORT, posCcy=base → LONG), estrae `mgnRatio`
- [ ] **1222.J** — `get_borrow_repay_history(symbol) -> list[BorrowRecord]` — `GET /account/quick-margin-borrow-repay-history`, popola `borrow_amount`/`margin_interest`
- [ ] **1222.K** — `close_short_position(symbol) -> ExchangeOrder` — market buy per ricoprire, stesso pattern di `close_position()` esistente ma verifica `posCcy` prima
- [ ] **1222.L** — Aggiungere campo `margin_mode: Optional[str] = None` a `MarketOrderRequest` e `ExitBracketRequest` in `exchange_models.py`
- [ ] **1222.M** — Estendere `place_exit_bracket()` per direzione short (TP sotto entry, SL sopra entry) — verificare se serve un flag esplicito `position_side` o se basta dedurlo da `side`
- [ ] **1222.N** — Aggiornare `FakeOkxAdapter` in `fake_okx_adapter.py` con tutti i nuovi metodi mockati

### Test (TDD)

- [ ] `test_set_leverage_success`
- [ ] `test_place_market_order_isolated_side_sell` — verifica `tdMode: "isolated"` nel payload
- [ ] `test_place_exit_bracket_short_direction` — TP sotto entry, SL sopra entry
- [ ] `test_get_margin_positions_recognizes_short_via_poscсy`
- [ ] `test_get_margin_positions_recognizes_long_via_poscсy`
- [ ] `test_close_short_position_market_buy`
- [ ] `test_borrow_repay_history_parsing`
- [ ] `test_market_order_defaults_to_cash_when_margin_mode_none` — nessuna regressione sul long esistente

### Acceptance Criteria

- `place_market_order` con `margin_mode="isolated"` genera `tdMode: "isolated"` nel payload
- Tutti i nuovi metodi hanno test con mock OKX
- Nessuna regressione sul flusso long esistente (`tdMode` resta `"cash"` quando non specificato)

---

## 5. TASK-1223 — Session config `short_enabled` + SignalAggregator gate

**Status:** Pending
**Priorità:** 🟡 Media-Alta
**Dipendenze:** TASK-1222
**Stima:** 4-5h (combinazione di due sotto-task originariamente separati nelle due bozze)

### 5a. Flag di sessione `short_enabled` (default `false`, esplicito)

**File coinvolti (grounding):**
- `synthtrade/backend/app/scalping/_state.py` (riga ~14, default dict sessione)
- `synthtrade/backend/app/scalping/rest/session.py` (righe ~118-263, body di start)
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/models/session.model.ts` (riga ~24)
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/session-api.service.ts` (riga ~57)

**Sottotask:**
- [ ] **1223.A** — `_state.py`: aggiungere `"short_enabled": False` al default dict della sessione
- [ ] **1223.B** — `rest/session.py`: leggere `control.get("short_enabled", False)` nel body di start, salvare nello state
- [ ] **1223.C** — Frontend: `short_enabled?: boolean` in `SessionControl` (`session.model.ts`)
- [ ] **1223.D** — Frontend: parametro `shortEnabled` in `session-api.service.ts::start()`
- [ ] **1223.E** — Frontend: toggle "Short abilitato" nella config grid di `session-controls`, **visibile/attivabile solo se il simbolo ha `shortAvailable=true`** (da TASK-1221), altrimenti disabilitato/grigio
- [ ] **1223.F** — Warning esplicito in UI quando si abilita: "Comporta rischio di liquidazione e interesse su prestito — usare solo con capitale ridotto durante i test"

### 5b. Gate nel SignalAggregator + decisione di prodotto

Oggi ogni segnale SELL viene scartato con `decision_type='rejected_short_unsupported'` (TASK-1117). Va sostituito con un gate esplicito a 3 vie.

**File coinvolti:**
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py`
- `synthtrade/backend/app/core/signal_log_writer.py`

**Sottotask:**
- [ ] **1223.G** — In `SignalAggregator`, per segnale SELL senza posizione aperta:
  - `short_enabled=False` → comportamento invariato, `decision_type='rejected_short_unsupported'`
  - `short_enabled=True` e `short_available=False` per il simbolo → nuovo `decision_type='rejected_short_unavailable_symbol'` (richiede estensione CHECK constraint, vedi TASK-1226.D)
  - `short_enabled=True` e `short_available=True` → `execute`, side="short"
- [ ] **1223.H** — **⚠️ Decisione di prodotto da prendere ESPLICITAMENTE prima di implementare, non assumere:** short solo trend-following (segnale tecnico + intelligence bearish allineati, coerente con `ema_cross`/regime `trending_down`) oppure anche short mean-reversion (rischioso — stesso tipo di logica che ha causato la Falling Knife Protection sul long, TASK-906)? **Raccomandazione:** iniziare solo trend-following, più sicuro, coerente con quanto già raccomandato nel vecchio doc Binance §5. Documentare la decisione nel commit e in `docs/TASKS.md`.
- [ ] **1223.I** — Nessuna modifica al path BUY esistente

### Test (TDD)

- [ ] `test_short_enabled_flag_defaults_false`
- [ ] `test_session_start_with_short_enabled_true`
- [ ] `test_toggle_disabled_when_symbol_short_unavailable` (frontend)
- [ ] `test_sell_signal_rejected_when_short_disabled` (comportamento invariato)
- [ ] `test_sell_signal_rejected_when_symbol_short_unavailable`
- [ ] `test_sell_signal_executed_when_short_enabled_and_available`
- [ ] `test_sell_only_trend_following_not_mean_reversion` (se 1223.H conferma solo trend-following)

### Acceptance Criteria

- `POST /scalping/session` con `"short_enabled": true` attiva lo short nella sessione
- Default resta `false` — nessuna regressione sulle sessioni long esistenti
- Nessun segnale SELL viene eseguito senza che entrambe le condizioni (`short_enabled` + `short_available`) siano vere
- Decisione trend-following-only vs anche-mean-reversion documentata esplicitamente, non lasciata implicita nel codice

---

## 6. TASK-1224 — Flusso apertura short (MVP, Fase 1 architettura)

**Status:** Pending
**Priorità:** 🔴 Alta — task più complesso della Fase 1
**Dipendenze:** TASK-1222, TASK-1223
**Stima:** 5-6h

### Obiettivo

Implementare l'apertura short in `candle_processor.py`, riusando il pattern già esistente per l'apertura long ma con `tdMode=isolated`, `side=sell`, bracket mirrorato. **Nessuna formula di interesse dinamico in questa fase** — solo il time-stop fisso di TASK-1225.

### File coinvolti (grounding dal codice reale, post-refactor TASK-1166)

- `synthtrade/backend/app/scalping/candle_processor.py` — blocco attuale da rimuovere/adattare:
  ```python
  # OGGI (righe ~338-355, bloccato incondizionatamente):
  if side == "SELL":
      logger.info("TRADE BLOCKED: SHORT NOT SUPPORTED")
      continue
  # DOPO (gate sul flag di sessione):
  if side == "SELL" and not _execution_state["session"].get("short_enabled"):
      logger.debug("SHORT signal skipped: short not enabled for this session")
      continue
  ```
- `candle_processor.py` riga ~358: rimuovere `if side != "BUY":` — permettere entrambi i lati come entry
- `candle_processor.py` righe ~394-684: path di apertura (oggi solo BUY) da estendere con branch SELL
- `pricing.py` righe ~83-136: `_sl_price_from_entry`/`_tp_price_from_entry` — verificare esplicitamente che già gestiscono `side="SELL"` (sembra di sì dal codice esistente, ma va testato, non assunto)
- `engine/position_manager.py` righe ~21-53: dataclass `Position`

### Sottotask

- [ ] **1224.A** — Prima di aprire: verificare `get_short_availability()` (cache già popolata da TASK-1221) — se `False`, non tentare l'ordine, log esplicito
- [ ] **1224.B** — `set_leverage()` a valore basso (1x-2x, configurabile `SCALPING_SHORT_LEVERAGE`, default 1) — solo se diversa da quella attuale (leggere prima con `get_leverage_info`)
- [ ] **1224.C** — Calcola qty da `_trade_val` (stesso pattern del BUY, `quote_amount` non `quantity` — coerente con FIX-2026-07-10 già applicato al long)
- [ ] **1224.D** — `place_market_order(tdMode="isolated", side="sell", quote_amount=trade_value)`
- [ ] **1224.E** — Fetch fill reale con retry (stesso pattern TASK-1186 per il long — `avgPx` spesso vuoto nella risposta sincrona OKX)
- [ ] **1224.F** — `place_exit_bracket()` con direzione invertita: TP sotto entry, SL sopra entry, stessi target netti già configurati (SL 1.05%/TP 1.55%, TASK-OKX-RECAL) — **nessun aggiustamento per interesse in questa fase**
- [ ] **1224.G** — Se il bracket fallisce: stesso pattern emergency-close già esistente (`_handle_bracket_failed`), ma con buy invece di sell per chiudere
- [ ] **1224.H** — Registra posizione in `PositionManager` con `side="SELL"`/`position_side="SHORT"`
- [ ] **1224.I** — Salvataggio DB: `position_side="SHORT"`, `borrow_asset`, `entry_order_id`, `exchange_bracket_id`, `margin_mode="isolated"`, `leverage` (richiede TASK-1226 completato prima)
- [ ] **1224.J** — Logging dedicato per short entry, stessa formattazione dei log BUY esistenti (facilita debug/confronto nei log)
- [ ] **1224.K** — Aggiornare `supervisor_client.py` (riga ~67) — rimuovere riferimento hardcoded "SHORT not supported" dal system prompt quando `short_enabled=True` (collegato a TASK-1231, qui solo la rimozione minima)

### Test (TDD, con FakeOkxAdapter)

- [ ] `test_open_short_happy_path` — entry + bracket confermati, posizione salvata con `position_side=SHORT`
- [ ] `test_open_short_bracket_failure_emergency_close` — bracket rifiutato → market buy immediato, nessuna posizione salvata
- [ ] `test_open_short_bracket_price_direction` — TP sotto entry, SL sopra entry verificato sui prezzi passati al fake adapter
- [ ] `test_open_short_skips_if_availability_false`
- [ ] `test_open_short_leverage_set_only_if_different`
- [ ] `test_sl_tp_price_from_entry_side_sell_explicit` — verifica esplicita che pricing.py gestisce side="SELL" correttamente (non assumere che funzioni già)

### Acceptance Criteria

- Stesso principio non-negoziabile già in uso per il long: nessuna posizione short salvata su DB senza bracket confermato o chiusura di emergenza
- Bracket TP/SL correttamente invertiti rispetto al long
- Trade SELL eseguibile in demo con SL > entry, TP < entry
- Nessuna regressione sul flusso long

---

## 7. TASK-1225 — Chiusura short + time-stop fisso 48h (MVP)

**Status:** Pending
**Priorità:** 🔴 Alta
**Dipendenze:** TASK-1224
**Stima:** 4-5h

### Obiettivo

Chiusura short via fill bracket (repay automatico se supportato) + rete di sicurezza a tempo fisso. **Nessuna formula dinamica** — quella è TASK-1230, Fase 2.

### File coinvolti

- `synthtrade/backend/app/scalping/trade_executor.py`
- `synthtrade/backend/app/execution/okx_order_event_stream.py`
- `synthtrade/backend/app/scheduler/scalping_jobs.py`
- `candle_processor.py` riga ~719-725 (`_close_position_and_record()`, già esistente per il long)

### Sottotask

- [ ] **1225.A** — `_on_order_update`: riconoscere fill su posizione short (side="buy" per la chiusura) e instradare a `_close_short_and_record()` invece del path long
- [ ] **1225.B** — `_close_short_and_record()`: PnL invertito (`entry_price − exit_price`, non `exit_price − entry_price`); verificare/loggare repay automatico via `get_borrow_repay_history()` post-chiusura
- [ ] **1225.C** — Se il repay **non** risulta automatico (verificare in TASK-1220): chiamata esplicita `POST /api/v5/account/quick-margin-borrow-repay`
- [ ] **1225.D** — **Time-stop fisso 48h** (config `SCALPING_SHORT_TIMESTOP_HOURS=48`, default): scegliere UN pattern implementativo tra i due proposti dalle bozze originali — **raccomandato: job schedulato** (`short_timestop_job`, ogni 30 min, stesso pattern degli altri job in `scalping_jobs.py`, controllo su `opened_at` in DB) invece di `asyncio.create_task(asyncio.sleep(48*3600))` in-process, perché sopravvive a un restart dell'app (il secondo approccio no — se l'app si riavvia, il timer in-memory si perde, esattamente il tipo di problema già affrontato con la riconciliazione posizioni TASK-1177/1184)
- [ ] **1225.E** — Se scade: cancella bracket, market buy di chiusura, `exit_reason="timestop_fixed"`
- [ ] **1225.F** — Log esplicito quando il time-stop scatta, distinto da stop_loss/take_profit ordinari

### 7.bis — Paper mode short (da bozza opencode, mancante nella mia versione originale)

- [ ] **1225.G** — `candle_processor.py` (path paper mode, righe ~686-717 nel codice attuale): replicare la logica short anche in paper mode — è il percorso di test più economico e veloce prima di demo/live
- [ ] **1225.H** — Paper mode: simulare PnL invertito coerentemente (`entry_price - exit_price`)
- [ ] **1225.I** — Verificare che il trade log in paper mode mostri correttamente `side=SELL`/`position_side=SHORT` con PnL corretto

### Test (TDD)

- [ ] `test_close_short_pnl_inverted` — entry 100, exit 95 → PnL positivo (short che guadagna quando il prezzo scende)
- [ ] `test_close_short_triggers_repay`
- [ ] `test_timestop_job_closes_position_after_48h`
- [ ] `test_timestop_job_ignores_positions_under_threshold`
- [ ] `test_timestop_job_ignores_long_positions` (il job tocca solo posizioni SHORT)
- [ ] `test_timestop_survives_app_restart` — verifica che il pattern job-based (non in-memory) funzioni anche se il processo riparte a metà finestra
- [ ] `test_paper_mode_short_pnl_and_side_correct`

### Acceptance Criteria

- Nessuna posizione short può restare aperta oltre 48h senza intervento
- PnL calcolato correttamente in direzione invertita, verificato su almeno un caso di test esplicito
- Time-stop robusto a riavvio dell'app (non basato solo su timer in-memory)
- Short funzionante in paper mode prima di qualunque test demo/live

---

## 8. TASK-1226 — DB migration: campi short-specific

**Status:** Pending
**Priorità:** 🔴 Alta
**Dipendenze:** nessuna (parallelizzabile, ma va completato prima di TASK-1224.I)
**Stima:** 1-2h

### Sottotask

- [ ] **1226.A** — Migration SQL:
  ```sql
  ALTER TABLE scalping_sessions
    ADD COLUMN IF NOT EXISTS allows_short BOOLEAN DEFAULT FALSE;

  ALTER TABLE scalping_trades
    ADD COLUMN IF NOT EXISTS position_side TEXT CHECK (position_side IN ('LONG','SHORT')) DEFAULT 'LONG',
    ADD COLUMN IF NOT EXISTS margin_mode TEXT,
    ADD COLUMN IF NOT EXISTS leverage NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS borrow_asset TEXT,
    ADD COLUMN IF NOT EXISTS borrow_amount NUMERIC(16,8),
    ADD COLUMN IF NOT EXISTS margin_interest NUMERIC(16,8),
    ADD COLUMN IF NOT EXISTS repay_status TEXT CHECK (repay_status IN ('pending','completed','failed')),
    ADD COLUMN IF NOT EXISTS interest_rate_apr_at_open NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS timestop_deadline TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS wallet_transfer_log JSONB;
  ```
- [ ] **1226.B** — `db_ops.py::_update_closed_position_in_db` — popolare `position_side` ("LONG"/"SHORT" da `pos.side`)
- [ ] **1226.C** — `db_ops.py` — popolare `margin_interest` se disponibile (per ora `None`, valorizzato in Fase 2 con TASK-1230)
- [ ] **1226.D** — **⚠️ Verificare ESPLICITAMENTE se esiste già un CHECK constraint su `decision_type`/`exit_reason` che va esteso.** Pattern di errore già capitato **due volte** in questo progetto (TASK-1116.D per `mode='TEST'`, TASK-1117 per `rejected_short_unsupported`): un nuovo valore enum scritto dal codice ma non incluso nel constraint DB causa insert falliti silenziosamente. Estendere qui, proattivamente, per: `rejected_short_unavailable_symbol` (da TASK-1223), `timestop_fixed` e `stop_loss_interest` (da TASK-1225/1230)

### Acceptance Criteria

- Migration applicata senza errori su Supabase
- `position_side` popolato correttamente per trade LONG e SHORT
- Query su un trade long storico non fallisce (retrocompatibilità, default `position_side='LONG'`)
- **Nessun CHECK constraint blocca gli insert dei nuovi decision_type/exit_reason** — verificato con un insert di test per ciascun nuovo valore prima di chiudere il task

---

## 9. TASK-1227 — Frontend: supporto UI completo per short

**Status:** Pending
**Priorità:** 🟡 Media
**Dipendenze:** TASK-1221 (badge), TASK-1223 (toggle), TASK-1224 (posizioni reali da mostrare)
**Stima:** 3-4h

### File coinvolti

- `session-controls.component.ts` (toggle, già iniziato in TASK-1223.E)
- `position-ticker.component.ts`
- `trade-log.component.ts`
- `session.model.ts`

### Sottotask

- [ ] **1227.A** — `position-ticker.component.ts`: badge direzione LONG/SHORT sulla posizione aperta, colore distinto (`--color-sell` per short, coerente con la palette già in uso)
- [ ] **1227.B** — `trade-log.component.ts`: colonna `Side` (LONG/SHORT) oltre a BUY/SELL esistente, PnL colorato coerentemente con la direzione (attenzione: per uno short, prezzo che scende = verde, invertito rispetto al long — non dare per scontato che il colorimetro esistente funzioni senza modifiche)
- [ ] **1227.C** — Breakeven indicator (TASK-2026-07-16 già esistente per il long): verificare se va adattato per lo short — la barra di progresso e il marker BE assumono oggi implicitamente `entry < TP`, per uno short è invertito

### Test

- [ ] `test_position_ticker_shows_short_badge`
- [ ] `test_trade_log_side_column_short`
- [ ] `test_breakeven_bar_inverted_for_short`

### Acceptance Criteria

- Nessuna sessione short parte accidentalmente — toggle esplicito, default off
- UI distingue visivamente in ogni punto (ticker, trade log, breakeven) una posizione SHORT da una LONG, senza ambiguità di colore/direzione

---

## 10. TASK-1228 — Test di integrazione short (fake adapter)

**Status:** Pending
**Priorità:** 🔴 Alta
**Dipendenze:** TASK-1222, TASK-1224, TASK-1225
**Stima:** 4h

### File coinvolti

- `synthtrade/backend/tests/integration/test_okx_short_integration.py` (nuovo)
- `fake_okx_adapter.py` (esteso da TASK-1222.N)

### Scenari obbligatori

- [ ] **1228.A** — Happy path: SELL signal → leverage → market sell isolated → bracket → fill (buy) → repay → DB closed con `position_side=SHORT`, PnL positivo
- [ ] **1228.B** — Bracket failure: entry short ok → bracket reject → emergency market buy → nessuna posizione salvata
- [ ] **1228.C** — Stop sessione con short aperto: cancel bracket → market buy di chiusura → DB closed reason=`session_stop`
- [ ] **1228.D** — Time-stop 48h: posizione aperta simulata >48h → job la chiude → `exit_reason=timestop_fixed`
- [ ] **1228.E** — Short non disponibile per simbolo: segnale SELL con `short_enabled=True` ma `short_available=False` → nessun ordine, `decision_type=rejected_short_unavailable_symbol`
- [ ] **1228.F** — Restore/riavvio con posizione short aperta: riconoscimento via `posCcy` durante reconcile (stesso meccanismo di `_reconcile_position_with_exchange`, va esteso per il campo `posCcy`)
- [ ] **1228.G** — Unit test pricing isolato: `_tp_price_from_entry`/`_sl_price_from_entry` con `side="SELL"` — TP sotto entry, SL sopra entry (duplica 1224 ma a livello di funzione pura, senza adapter)

### Acceptance Criteria

- Tutti gli scenari passano senza chiamate di rete reali
- Nessuna regressione sui test long esistenti (12/12 di `test_okx_integration.py`)
- Coverage minimo: pricing, flow completo, gate disponibilità, time-stop, restore

---

## 11. TASK-1229 — Validazione demo/live minimo end-to-end

**Status:** Pending
**Priorità:** 🟡 Media (manuale/supervisionato)
**Dipendenze:** TASK-1225, TASK-1225.bis (paper), TASK-1228
**Stima:** manuale, 1 sessione supervisionata

### Checklist

1. Sessione paper con `short_enabled=True` — almeno un ciclo completo prima di passare a demo
2. Sessione demo su simbolo confermato borrowable (TASK-1220.B) con `short_enabled=True`
3. Segnale SELL trend-following approvato
4. Apertura: borrow + sell isolated confermati su OKX UI
5. Bracket TP/SL piazzato e visibile
6. Fill (TP o SL, anche indotto manualmente se possibile)
7. Repay confermato (automatico o esplicito)
8. PnL calcolato correttamente (verificare segno)
9. Se il trade non si chiude naturalmente: verificare che il time-stop 48h scatti (per accelerare il test, abbassare temporaneamente `SCALPING_SHORT_TIMESTOP_HOURS`, poi ripristinare)
10. Nessuna posizione orfana o borrow non ripagato a fine test
11. `mgnRatio` letto da `GET /account/positions` durante il test — confrontare col valore teorico di collaterale minimo (§3.3 del design doc, mai verificato empiricamente prima)

### Output

`docs/analysis/okx-short-demo-e2e-report.md`, stesso formato di `okx-demo-e2e-report.md` (già menzionato in TASK-1112 per il flusso long, mai completato — non ripetere l'omissione qui)

---

## 12. TASK-1230 — Fase 2: Time-stop interest-based completo (Layer 3-6)

**Status:** Pending
**Priorità:** 🟡 Media — **bloccata** finché TASK-1224/1225/1229 non producono trade short reali con tasso di interesse osservato
**Dipendenze:** TASK-1225, TASK-1229 (dati reali)
**Stima:** 6-8h

### Formule complete (dal design doc, da implementare esattamente così)

```
Layer 1 (invariato): SL_net_target=1.05%, TP_net_target=1.55%

Layer 2 (riuso _net_to_gross_pct esistente):
  SL_gross_fee_only = |_net_to_gross_pct(SL_net_target, fee_taker, fee_taker)|  ≈ 0.35%
  TP_gross_fee_only = |_net_to_gross_pct(TP_net_target, fee_taker, fee_taker)|  ≈ 2.26%

Layer 3 (nuovo, cuore del meccanismo):
  rate_hourly = APR_al_open / 365 / 24     [bloccato all'apertura, mai rivalutato]
  BUFFER_HOURS = 24                         [configurabile, copre notte PC spento]
  interest_projected_pct(t) = rate_hourly × (elapsed_real_h(t) + BUFFER_HOURS)

Layer 4:
  SL_effective_gross(t) = SL_gross_fee_only − interest_projected_pct(t)
  TP_effective_gross(t) = TP_gross_fee_only + interest_projected_pct(t)

Layer 5 (direzione invertita rispetto al long):
  SL_price(t) = entry_price × (1 + SL_effective_gross(t) / 100)     [SL sopra entry]
  TP_price(t) = entry_price × (1 − TP_effective_gross(t) / 100)     [TP sotto entry]

Layer 6 (floor guard):
  if SL_effective_gross(t) <= FLOOR_MIN_PCT (0.02%):
      → chiudi immediatamente a mercato, exit_reason="stop_loss_interest"

Gate pre-apertura:
  if (rate_hourly × BUFFER_HOURS) >= SL_gross_fee_only:
      → BLOCCA apertura short

Tempo massimo di detenzione (stima, non enforcement):
  elapsed_max_h = SL_gross_fee_only / rate_hourly − BUFFER_HOURS
```

Esempio numerico di riferimento (APR=15% illustrativo, da sostituire col tasso reale di TASK-1220.C): tempo massimo ≈ 180h (~7,5 giorni). Con APR=50%: ≈ 37h (~1,5 giorni) — il meccanismo si autoregola.

### Design: modulo a funzioni pure (da bozza opencode — testabilità senza mock)

- [ ] **1230.A** — Nuovo modulo `synthtrade/backend/app/scalping/short_timestop.py`, **solo funzioni pure**, nessuna chiamata di rete:
  - `compute_interest_projected_pct(rate_hourly, elapsed_h, buffer_hours=24) -> float`
  - `compute_sl_effective(sl_gross, interest_pct) -> float`
  - `compute_tp_effective(tp_gross, interest_pct) -> float`
  - `compute_bracket_prices(entry, sl_eff, tp_eff, side) -> tuple[float, float]`
  - `check_floor_guard(sl_eff, floor_min=0.02) -> bool`
  - `check_gate_pre_apertura(rate_hourly, buffer_hours, sl_gross) -> bool`
  - `compute_max_hold_hours(sl_gross, rate_hourly, buffer_hours) -> float`
- [ ] **1230.B** — Salvare `rate_hourly` (bloccato) all'apertura in `interest_rate_apr_at_open` (schema da TASK-1226) — oggetto `Position` esteso con `interest_apr`, `interest_hourly`, `interest_opened_at` (dataclass in `position_manager.py`)
- [ ] **1230.C** — Job periodico orario di refresh bracket (nuovo `bracket_refresher.py` o job in `scalping_jobs.py`): per ogni posizione short aperta, ricalcola Layer 3-5, **cancella il vecchio bracket e ne piazza uno nuovo** — riusare lo stesso pattern "attendi conferma cancellazione prima di ripiazzare" già in uso per lo stop sessione long (evita race condition tra cancel e fill, stesso principio già codificato in `oco-flow-architecture.md` §4)
- [ ] **1230.D** — Floor guard nel job: se scatta, chiudi immediatamente invece di ripiazzare un bracket ormai invalido
- [ ] **1230.E** — Gate pre-apertura in TASK-1224 (retrofit): sostituire/integrare il check più semplice di TASK-1221 con questo, usando il tasso reale letto all'apertura
- [ ] **1230.F** — Disattivare/rimuovere il time-stop fisso 48h di TASK-1225 (ridondante — il floor guard lo sostituisce con un meccanismo auto-limitante). Non cancellare il codice, marcarlo come fallback se il job orario fallisce ripetutamente (difesa in profondità)
- [ ] **1230.G** — Loggare all'apertura `elapsed_max_h` stimato — utile per monitoraggio operativo

### Test (TDD, sul modulo puro — nessun mock necessario)

- [ ] `test_interest_projected_pct_formula` — verifica numerica esatta contro la tabella del design doc (APR=15%, t=0/24h/100h/180h)
- [ ] `test_sl_tp_effective_gross_narrows_over_time`
- [ ] `test_floor_guard_triggers_at_correct_threshold`
- [ ] `test_gate_blocks_open_when_buffer_exceeds_sl_budget`
- [ ] `test_gate_allows_open_with_low_apr`
- [ ] `test_compute_max_hold_hours_matches_manual_calc`
- [ ] `test_rate_hourly_locked_at_open_not_reevaluated` (integrazione, verifica che il refresh orario non rilegga l'APR da OKX)
- [ ] `test_hourly_refresh_cancel_replace_no_gap` (integrazione, con fake adapter — simula 180h con 15% APR, verifica che SL tocca zero e scatta il floor guard)
- [ ] `test_180h_simulation_matches_design_doc_table` — replica esatta della tabella d'esempio nel design doc come test di regressione

### Limiti noti (da documentare esplicitamente nel codice/commit, non nascondere)

- Tasso fisso: se il tasso sale molto durante il trade, il calcolo sottostima l'interesse reale accumulato — mitigato dal buffer 24h ma non eliminato
- Refresh orario: introduce una finestra di rischio operativo (cancel+replace) che non esiste per il long
- Collaterale minimo reale (§3.3 design doc) resta una stima fino a conferma empirica da TASK-1229.11

### Acceptance Criteria

- Meccanismo verificato con almeno 2-3 sessioni short reali prima di essere considerato definitivo (stesso principio già applicato a TASK-1159 — mai a intuito)
- Nessun bracket invalido (SL dalla parte sbagliata) viene mai piazzato — stesso tipo di bug già preso una volta sul long (sCode 51280, TASK-1127), da non ripetere qui
- SL si restringe nel tempo, TP si allontana, come da formula
- Tempo massimo di detenzione calcolato e loggato correttamente

---

## 13. TASK-1231 — Supervisor AI: awareness short

**Status:** Pending
**Priorità:** 🟢 Bassa-Media (impatta un comportamento già in produzione, TASK-908)
**Dipendenze:** TASK-1223, TASK-1224
**Stima:** 2-3h

### Obiettivo

Il Supervisor oggi tratta l'assenza di short come un limite architetturale fisso — in particolare **TASK-908 (resume guard)** blocca esplicitamente `resume_trading` in regime `trending_down` proprio perché non c'è modo di tradare la direzione ribassista. Con short disponibile, questa premessa non è più vera e va aggiornata, non solo il prompt testuale.

### File coinvolti

- `synthtrade/backend/app/ai/supervisor_context.py`
- `synthtrade/backend/app/scalping/supervisor/supervisor_client.py` (riga ~67, system prompt)
- `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py` (righe ~339-358, resume guard TASK-908)
- `synthtrade/backend/app/scalping/supervisor/parameter_updater.py` (`_resume()`, no-op condizionale)

### Sottotask

- [ ] **1231.A** — Contesto AI: `short_enabled` ora riflette `session.short_enabled` reale (oggi hardcoded `False` da TASK-908/architettura precedente) + `position_side` della posizione aperta se esiste + `short_blocked_reason: None | "margin_not_enabled" | "signal_rejected" | "symbol_unavailable"`
- [ ] **1231.B** — System prompt: rimuovere/condizionare i riferimenti a "SHORT not supported" — deve dipendere da `short_enabled`, non essere un'affermazione assoluta
- [ ] **1231.C** — **TASK-908 resume guard**: se `short_enabled=True`, la guard che blocca `resume_trading` in `trending_down` senza posizione va **disattivata o adattata** — con short disponibile, un regime bearish confermato è un'opportunità di entry short, non (solo) un rischio da evitare. Verificare i 3 livelli della guard esistente (supervisor_scheduler.py, parameter_updater.py `_resume()`, supervisor_context.py) e decidere per ciascuno se disattivare o parametrizzare su `short_enabled`
- [ ] **1231.D** — Verificare che il Supervisor non abbassi la soglia inutilmente in sessioni con short attivo quando il vero blocco è di altra natura (stesso tipo di problema già documentato per il long, TASK-INVEST-014/bug §4 collector — il supervisor deve distinguere "mercato neutro" da "short strutturalmente non disponibile per questo simbolo")

### Test

- [ ] `test_context_includes_short_enabled_and_position_side`
- [ ] `test_prompt_does_not_mention_short_unsupported_when_enabled`
- [ ] `test_resume_guard_disabled_when_short_enabled` — regressione su TASK-908 esistente: verificare che quando `short_enabled=False` (default) il comportamento attuale resti **identico**
- [ ] `test_resume_guard_still_blocks_when_short_disabled` (nessuna regressione)

### Acceptance Criteria

- Nessuna regressione sul comportamento TASK-908 quando `short_enabled=False` (default) — questo è il test più importante del task, dato che TASK-908 è già in produzione
- Quando `short_enabled=True`, il supervisor riceve nel prompt l'informazione esplicita e la guard bearish si comporta diversamente in modo consapevole, non per bug

---

## 14. TASK-1232 — Risk Manager simmetrico per short

**Status:** Pending
**Priorità:** 🟢 Bassa
**Dipendenze:** TASK-1224, TASK-1225
**Stima:** 2h

### Obiettivo

Verificare — con test, non per assunzione — che i controlli di rischio esistenti (`_check_daily_loss`, `_check_drawdown`) si applichino correttamente a PnL generato da posizioni short, dato che il calcolo PnL invertito di TASK-1225 deve alimentare correttamente questi accumulatori senza modifiche separate previste.

### Sottotask

- [ ] **1232.A** — Verificare che `_check_daily_loss()` sommi correttamente PnL LONG + SHORT nello stesso accumulo giornaliero (nessuna doppia contabilità o segno invertito per errore)
- [ ] **1232.B** — Verificare `_check_drawdown()` con equity curve mista long/short
- [ ] **1232.C** — Verificare che il `max_position_pct`/sizing esistente non assuma implicitamente "solo long" in qualche punto residuo del codice (grep mirato su `side == "BUY"` hardcoded fuori dai path già coperti)

### Test

- [ ] `test_daily_loss_check_includes_short_pnl`
- [ ] `test_drawdown_check_mixed_long_short_equity`
- [ ] `test_no_hardcoded_buy_only_assumptions_in_risk_checks` (grep-assisted o test parametrico)

### Acceptance Criteria

- Nessuna modifica di codice prevista se i test passano già — questo task è principalmente di **verifica**, non di sviluppo. Se emergono bug, diventano fix puntuali documentati qui.

---

## 15. TASK-1233 — Documentazione: chiusura riferimenti superseded e indici

**Status:** Pending
**Priorità:** 🟢 Bassa (housekeeping)
**Dipendenze:** nessuna, può essere fatto subito o a fine epica
**Stima:** 30 min

### Sottotask

- [ ] **1233.A** — Verificare che `docs/architecture/short-selling-architecture.md` e `docs/analysis/short-selling-analysis.md` abbiano il banner `SUPERSEDED` (risulta già fatto il 21/07 — solo controllo)
- [ ] **1233.B** — Aggiornare `docs/BACKLOG.md` sezione Short Selling: stato da "pianificazione costi in corso" a "implementazione in corso, TASK-1220 avviato" (e poi via via aggiornare man mano che le fasi chiudono)
- [ ] **1233.C** — Aggiornare `docs/architecture/okx-migration-architecture.md` §5.3 con riferimento esplicito a questa epica invece del vecchio pseudocodice generico
- [ ] **1233.D** — A fine epica: aggiornare `docs/STORY.md` con milestone dedicata, come da convenzione già in uso nel progetto per ogni epica chiusa

---

## 16. Riepilogo rischi trasversali (da tenere sott'occhio durante tutta l'epica)

| Rischio | Dove può manifestarsi | Mitigazione già prevista |
|---|---|---|
| CHECK constraint DB dimenticato per nuovi enum | TASK-1226 | Verifica esplicita proattiva (1226.D), pattern già sbagliato 2 volte in passato |
| Bracket con SL dalla parte sbagliata (sCode 51280-style) | TASK-1224, TASK-1230 | Test espliciti su direzione prezzi, riuso di `_net_to_gross_pct` con `abs()` |
| Regressione su TASK-908 (resume guard) quando short disabilitato | TASK-1231 | Test di non-regressione esplicito come primo acceptance criterion |
| Timer time-stop perso al riavvio app | TASK-1225 | Job schedulato basato su DB, non `asyncio.sleep` in-memory |
| Race condition su cancel+replace bracket orario | TASK-1230 | Riuso pattern "attendi conferma cancellazione" già in uso per stop sessione |
| Collaterale minimo reale ignoto → liquidazione imprevista | TASK-1229 | Verifica `mgnRatio` empirica al primo trade reale, non prima |
| Decisione trend-following vs mean-reversion presa implicitamente/mai | TASK-1223.H | Decisione esplicita richiesta prima di procedere, da documentare nel commit |
| Short abilitato accidentalmente su sessione live | TASK-1223, TASK-1227 | Default `false`, toggle esplicito, disabilitato se simbolo non supportato, warning UI |
| Colori/direzione UI invertiti per short (breakeven, PnL) | TASK-1227 | Task dedicato a verificare ogni componente, non solo aggiungere un badge |

---

## 17. Ordine di esecuzione consigliato

```
1. TASK-1220 (gate bloccante — verificare PRIMA di tutto)
2. TASK-1221 ∥ TASK-1222 ∥ TASK-1226  (parallelizzabili)
3. TASK-1223 (config + gate + decisione prodotto)
4. TASK-1224 (apertura MVP)
5. TASK-1225 + TASK-1225.bis paper mode
6. TASK-1227 ∥ TASK-1228 ∥ TASK-1231 ∥ TASK-1232  (parallelizzabili)
7. TASK-1229 (validazione E2E demo/live minimo)
8. TASK-1230 (SOLO dopo dati reali da 1229 — Fase 2 interesse dinamico)
9. TASK-1233 (housekeeping, in qualunque momento)
```

**Prossimo passo immediato:** avviare TASK-1220 (spike read-only). È l'unico vero gate — tutto il resto presuppone che risponda positivamente.
