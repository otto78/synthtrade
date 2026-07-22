# SynthTrade — Breakdown Dettagliato Task Short Selling OKX

> Data: 21 luglio 2026
> Architettura: `docs/architecture/okx-short-selling-architecture.md`
> Design time-stop: `docs/analysis/2026-07-21_okx-short-timestop-design.md`
> Supersede: TASK-1000 (Binance WalletOrchestrator)

---

## Regole di Coordinamento

Stesse regole dello breakdown migrazione OKX (`okx-migration-task-breakdown.md`):

1. ogni agente deve leggere architettura e questo breakdown prima di modificare codice;
2. ogni task deve aggiornare `docs/TASKS.md`, `docs/STORY.md`, `docs/HANDOFF.md` a fine lavoro;
3. non usare Binance come assunzione implicita in nuovo codice;
4. se un comportamento OKX non e' verificato, marcarlo come `UNVERIFIED`;
5. preferire fake adapter/fake stream nei test, Demo Trading solo per validazione manuale controllata;
6. un task alla volta nel path live — non introdurre piu' cambiamenti strutturali insieme.

### Stati Consentiti

- `Pending`: non iniziato.
- `In Progress`: un agente lo sta lavorando.
- `Blocked`: manca credenziale, payload o decisione esterna.
- `Ready for Review`: codice/documentazione pronti, test eseguiti.
- `Done`: verificato e documentato.

---

## Mappa Dipendenze

```text
TASK-SHORT-001 (spike read-only)
  ├→ TASK-SHORT-002 (check short disponibile — backend + frontend badge)
  └→ TASK-SHORT-003 (adapter margin methods)
       └→ TASK-SHORT-004 (session config short_enabled)
            └→ TASK-SHORT-005 (execution loop branch short MVP)
                 ├→ TASK-SHORT-006 (DB migration)
                 ├→ TASK-SHORT-007 (interest rate reader)
                 │    └→ TASK-SHORT-008 (bracket refresh time-stop)
                 ├→ TASK-SHORT-009 (supervisor context update)
                 └→ TASK-SHORT-010 (paper mode short)
                      └→ TASK-SHORT-011 (tests)
```

Parallelizzabile dopo TASK-SHORT-003:
- TASK-SHORT-002 (frontend badge, indipendente dall'adapter)
- TASK-SHORT-004 + TASK-SHORT-005 (execution flow, dipende solo dall'adapter)

---

## TASK-SHORT-001 — Spike read-only OKX account (margin endpoints)

**Status:** Pending
**Tipo:** Spike bloccante
**Non modificare:** codice runtime, DB, frontend
**Prerequisito:** nessuno
**Owner ideale:** agente con accesso credenziali e capacita' API/debug

### Obiettivo

Verificare empiricamente che il vostro account OKX supporta margin short, quali asset sono borrowable, e con che tassi/margini. Nessuno di questi endpoint e' mai stato chiamato sul vostro account reale.

### Sottotask

1. **001.A** — `GET /api/v5/account/config` → verificare `enableSpotBorrow` e `acctLv` (account mode). Il vostro account deve essere in modalita' che supporta margin trading.
2. **001.B** — `GET /api/v5/account/max-loan?instId=BTC-EUR&mgnMode=isolated` → confermare che BTC e' borrowable e quale e' il limite massimo.
3. **001.C** — `GET /api/v5/account/max-loan?instId=OKB-EUR&mgnMode=isolated` → confermare se OKB e' borrowable (probabile che non lo sia — token nativo).
4. **001.D** — `GET /api/v5/public/interest-rate-loan-quota?ccy=BTC` → tasso reale APR per BTC.
5. **001.E** — `GET /api/v5/public/interest-rate-loan-quota?ccy=OKB` → tasso reale APR per OKB.
6. **001.F** — `GET /api/v5/account/position-tiers?instType=MARGIN&instId=BTC-EUR` → maintenance margin ratio reale per tier di posizione.
7. **001.G** — `GET /api/v5/account/leverage-info?instType=MARGIN&ccy=BTC` → leva attualmente impostata.

### Output

Aggiornare `docs/analysis/okx-demo-spike-results.md` con:
- Tabella: asset, borrowable (si/no), limite max, APR reale, maintenance margin ratio, leva attuale
- Payload raw salvati in `docs/analysis/okx-demo-spike-results.json`
- Raccomandazione: quale simbolo usare per il primo trade di test

### Acceptance Criteria

- Tutti i 7 endpoint chiamati e documentati
- Tabella completa in `okx-demo-spike-results.md`
- Almeno un asset confermato borrowable
- Nessun codice runtime modificato

### Rischi

- Account non abilitato al margin → serve attivazione manuale da sito OKX
- BTC-EUR non disponibile in margin su EU → provare con USDT pairs
- OKB non borrowable → non e' un problema, basta saperlo

---

## TASK-SHORT-002 — Check disponibilita' short per simbolo (backend + frontend)

**Status:** Pending
**Tipo:** Feature
**Prerequisito:** TASK-SHORT-001
**Architettura riferimento:** §5

### Obiettivo

Quando l'utente seleziona un simbolo, il sistema deve dire se lo short e' disponibile per quel simbolo — con tasso interesse. Questo evita di aprire sessioni che poi bloccano tutti i segnali SELL.

### Sottotask

1. **002.A** — Backend: aggiungere a `GET /api/scalping/exchange/instruments` i campi `short_available: bool` e `short_borrow_rate_apr: float | null` per strumento. Calcolato una volta per ciclo di discovery, non ad ogni selezione.
   - File: `synthtrade/backend/app/execution/okx_exchange.py` → `list_instruments()` (line 359)
   - Logica: `max-loan > 0` = short available; tasso da `interest-rate-loan-quota`
2. **002.B** — Frontend: aggiungere `shortAvailable?: boolean` e `shortBorrowRateApr?: number` al modello `ExchangeInstrument`.
   - File: `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/exchange-symbols.service.ts:18`
3. **002.C** — Frontend: badge nella session-controls component dopo il selettore simbolo.
   - File: `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts:39-93`
   - Visual: ✅ "Short disponibile — X% APR" o ⚠️ "Short non disponibile per questo simbolo"
4. **002.D** — Test: mock payload con `shortAvailable=true/false`, verificare rendering badge

### Acceptance Criteria

- Selezionando un simbolo borrowabile, il badge mostra "Short disponibile" con tasso APR
- Selezionando un simbolo non borrowable, il badge mostra "Short non disponibile"
- Il check non impatta le prestazioni della sessione (calcolato una volta per discovery)

---

## TASK-SHORT-003 — Adapter: margin methods + tdMode parametrico

**Status:** Pending
**Tipo:** Backend adapter
**Prerequisito:** TASK-SHORT-001
**Architettura riferimento:** §2, §4

### Obiettivo

Estendere `OkxExchangeAdapter` con i metodi necessari al margin trading e parametrizzare `tdMode` (oggi hardcoded `"cash"`).

### Sottotask

1. **003.A** — Parametrizzare `tdMode` in `_direct_place_market_order` (line 559) e `_direct_place_exit_bracket` (line 801). Oggi hardcoded `"cash"`, deve accettare `"isolated"` quando `short_enabled=true`.
   - File: `synthtrade/backend/app/execution/okx_exchange.py:559,801`
2. **003.B** — Parametrizzare `instType` in `get_symbol_rules()` (line 334) — oggi hardcoded `"spot"`, per margin short serve poter chiamare con `"margin"`.
3. **003.C** — Nuovo metodo `get_account_config() → dict` — chiama `GET /api/v5/account/config`, ritorna `enableSpotBorrow`, `acctLv`.
4. **003.D** — Nuovo metodo `get_max_loan(inst_id, mgn_mode) → float` — chiama `GET /api/v5/account/max-loan`.
5. **003.E** — Nuovo metodo `get_interest_rate(ccy) → float` — chiama `GET /api/v5/public/interest-rate-loan-quota`.
6. **003.F** — Nuovo metodo `get_position_tiers(inst_id) → dict` — chiama `GET /api/v5/account/position-tiers`.
7. **003.G** — Aggiungere campo `margin_mode: Optional[str] = None` a `MarketOrderRequest` e `ExitBracketRequest` in `exchange_models.py`.
8. **003.H** — Test: fake adapter con i nuovi metodi, verificare che `tdMode` viene passato correttamente nei payload.

### Acceptance Criteria

- `place_market_order` con `margin_mode="isolated"` genera `tdMode: "isolated"` nel payload
- Tutti i nuovi metodi hanno test con mock OKX
- Nessuna regressione sul flusso long esistente (`tdMode` resta `"cash"` quando non specificato)

---

## TASK-SHORT-004 — Session config: flag `short_enabled`

**Status:** Pending
**Tipo:** Backend + Frontend config
**Prerequisito:** TASK-SHORT-003

### Obiettivo

Aggiungere un flag `short_enabled` alla sessione, controllabile dall'utente all'avvio. Default `false` — lo short va abilitato esplicitamente.

### Sottotask

1. **004.A** — `_state.py` (line 14): aggiungere `"short_enabled": False` al default dict della sessione.
   - File: `synthtrade/backend/app/scalping/_state.py:14`
2. **004.B** — `rest/session.py` (line 118): leggere `control.get("short_enabled", False)` nel body di start, salvare nello state.
   - File: `synthtrade/backend/app/scalping/rest/session.py:118-263`
3. **004.C** — Frontend: aggiungere `short_enabled?: boolean` a `SessionControl` in `session.model.ts:24`.
4. **004.D** — Frontend: aggiungere parametro `shortEnabled` al metodo `start()` in `session-api.service.ts:57`.
5. **004.E** — Frontend: toggle "Short abilitato" nella config grid di session-controls (visibile solo se il simbolo ha `shortAvailable=true`).
6. **004.F** — DB: aggiungere `allows_short BOOLEAN DEFAULT FALSE` a `scalping_sessions` (da fare in TASK-SHORT-006).

### Acceptance Criteria

- `POST /scalping/session` con `"short_enabled": true` attiva lo short nella sessione
- Il toggle frontend e' disabilitato grigio se il simbolo non supporta lo short
- Default resta `false` — nessuna regressione sulle sessioni long esistenti

---

## TASK-SHORT-005 — ExecutionLoop branch short (MVP)

**Status:** Pending
**Tipo:** Backend core — task piu' complesso
**Prerequisito:** TASK-SHORT-003, TASK-SHORT-004
**Architettura riferimento:** §6.7 (Fase 1 MVP)
**NON implementare:** Layer 3-6 del time-stop (arriva in TASK-SHORT-008)

### Obiettivo

Abilitare l'esecuzione di trade SELL (short) quando `short_enabled=true`. MVP: bracket identico al long, time-stop 48h fisso, nessun refresh interest-based.

### Sottotask

1. **005.A** — Rimuovere il blocco hardcoded SELL in `candle_processor.py:338-355`:
   ```python
   # OGGI (bloccato):
   if side == "SELL":
       logger.info("TRADE BLOCKED: SHORT NOT SUPPORTED")
       continue
   # DOPO (gate su flag):
   if side == "SELL" and not _execution_state["session"].get("short_enabled"):
       logger.debug("SHORT signal skipped: short not enabled for this session")
       continue
   ```
   - File: `synthtrade/backend/app/scalping/candle_processor.py:338-355`
2. **005.B** — Rimuovere `if side != "BUY":` (line 358) — allow both BUY and SELL come entry side.
3. **005.C** — Path SELL — apertura short:
   - Calcola qty da `_trade_val` (come per BUY ma con `side="sell"`)
   - Place market order con `tdMode=isolated`, `side=sell` (usa metodi TASK-SHORT-003)
   - Place exit bracket `side=buy`, SL sopra entry, TP sotto entry (pricing.py gia' gestisce le direzioni)
   - Registra posizione in PositionManager con `side="SELL"`
   - Salva in DB
   - File: `synthtrade/backend/app/scalping/candle_processor.py:394-684`
4. **005.D** — Chiusura short: quando arriva un signal opposto con posizione aperta → `_close_position_and_record()` (gia' esiste, line 719-725). Verificare che PnL e' calcolato correttamente per short (entry - exit, non exit - entry).
5. **005.E** — Time-stop 48h fisso (MVP): `asyncio.create_task` con `asyncio.sleep(48*3600)` che dopo 48h chiude la posizione con `exit_reason="time_stop"`. Nessun refresh bracket, nessuna formula — solo una rete di sicurezza.
6. **005.F** — Verificare che `_sl_price_from_entry` e `_tp_price_from_entry` funzionano con `side="SELL"` — pricing.py line 83-136 gia' lo fa, ma va testato esplicitamente.
7. **005.G** — Logging: aggiungere log dedicati per short entry/exit con stessa formattazione dei log BUY esistenti.
8. **005.H** — Supervisor prompt: aggiornare `supervisor_client.py:67` — rimuovere "SHORT not supported", indicare che lo short e' attivo se `short_enabled=true`.

### Acceptance Criteria

- Trade SELL eseguito in demo con bracket SL/TP corretto (SL > entry, TP < entry)
- Posizione tracciata correttamente con `side="SELL"`
- Chiusura funzionante (OCO fill o chiusura manuale)
- Time-stop 48h chiude la posizione se non gia' chiusa
- Nessuna regressione sul flusso long

### File coinvolti

- `synthtrade/backend/app/scalping/candle_processor.py:338-355,358,394-684,719-725`
- `synthtrade/backend/app/scalping/pricing.py:83-136`
- `synthtrade/backend/app/scalping/engine/position_manager.py:21-53`
- `synthtrade/backend/app/scalping/supervisor/supervisor_client.py:67`

---

## TASK-SHORT-006 — DB migration

**Status:** Pending
**Tipo:** Database
**Prerequisito:** TASK-SHORT-005 (o parallelizzabile con default safe)

### Obiettivo

Aggiungere al database le colonne necessarie per tracciare posizioni short, borrowing e interesse.

### Sottotask

1. **006.A** — Migration SQL per `scalping_trades`:
   ```sql
   ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
       position_side TEXT CHECK (position_side IN ('LONG', 'SHORT')) DEFAULT 'LONG';
   ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
       borrow_amount NUMERIC(16, 8);
   ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
       borrow_asset TEXT;
   ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
       margin_interest NUMERIC(16, 8);
   ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
       repay_status TEXT CHECK (repay_status IN ('pending', 'completed', 'failed'));
   ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
       wallet_transfer_log JSONB;
   ```
2. **006.B** — Migration SQL per `scalping_sessions`:
   ```sql
   ALTER TABLE scalping_sessions ADD COLUMN IF NOT EXISTS
       allows_short BOOLEAN DEFAULT FALSE;
   ```
3. **006.C** — `db_ops.py`: aggiornare `_update_closed_position_in_db` per popolare `position_side` ("LONG"/"SHORT" basato su `pos.side`).
   - File: `synthtrade/backend/app/scalping/db_ops.py:92`
4. **006.D** — `db_ops.py`: popolare `margin_interest` se disponibile (per ora `None`, valorizzato in Fase 2 con TASK-SHORT-008).

### Acceptance Criteria

- Migration applicata senza errori su Supabase
- `position_side` popolato correttamente per trade LONG e SHORT
- Nessuna violazione CHECK constraint

---

## TASK-SHORT-007 — Interest rate reader + storage

**Status:** Pending
**Tipo:** Backend
**Prerequisito:** TASK-SHORT-003, TASK-SHORT-005

### Obiettivo

Leggere il tasso di interesse APR all'apertura di uno short e salvarlo nella posizione per il calcolo del time-stop interest-based (Fase 2).

### Sottotask

1. **007.A** — Nuovo modulo `synthtrade/backend/app/scalping/interest_rate.py`:
   - `async def get_apr(adapter, ccy) → float` — chiama `adapter.get_interest_rate(ccy)`
   - `async def get_hourly_rate(adapter, ccy) → float` — APR / 365 / 24
2. **007.B** — `position_manager.py`: aggiungere campi al dataclass `Position`:
   - `interest_apr: Optional[float] = None`
   - `interest_hourly: Optional[float] = None`
   - `interest_opened_at: Optional[datetime] = None`
   - File: `synthtrade/backend/app/scalping/engine/position_manager.py:21`
3. **007.C** — `candle_processor.py`: all'apertura short, leggere APR e salvare nella posizione.
4. **007.D** — Test: mock adapter, verificare calcolo hourly rate da APR noto.

### Acceptance Criteria

- APR letto e salvato nella posizione all'apertura short
- `interest_hourly = APR / 365 / 24` calcolato correttamente
- Test passanti con dati noti

---

## TASK-SHORT-008 — Bracket refresh time-stop (Layer 3-6)

**Status:** Pending
**Tipo:** Backend — complesso
**Prerequisito:** TASK-SHORT-007, TASK-SHORT-005
**Architettura riferimento:** §6.2-6.6
**Fase:** 2 (dopo aver osservato trade reali con TASK-SHORT-005)

### Obiettivo

Implementare il meccanismo completo di refresh orario del bracket con calcolo interest-based delle soglie SL/TP. Sostituisce il time-stop 48h fisso del MVP.

### Sottotask

1. **008.A** — Nuovo modulo `synthtrade/backend/app/scalping/short_timestop.py` con funzioni pure (testabili senza mock):
   - `compute_interest_projected_pct(rate_hourly, elapsed_h, buffer_hours=24) → float`
   - `compute_sl_effective(sl_gross, interest_pct) → float`
   - `compute_tp_effective(tp_gross, interest_pct) → float`
   - `compute_bracket_prices(entry, sl_eff, tp_eff, side) → tuple[float, float]`
   - `check_floor_guard(sl_eff, floor_min=0.02) → bool` — True se deve chiudere
   - `check_gate_pre_apertura(rate_hourly, buffer_hours, sl_gross) → bool` — True se bloccato
   - `compute_max_hold_hours(sl_gross, rate_hourly, buffer_hours) → float`
2. **008.B** — Task periodico orario (sostituisce il timer 48h del MVP):
   - Per ogni posizione aperta con `side="SELL"`:
     1. Calcola `elapsed_real_h` da `entry_time`
     2. Calcola `interest_projected_pct` con buffer 24h
     3. Calcola nuovi SL/TP con Layer 4-5
     4. Cancella vecchio bracket (`DELETE /api/v5/trade/order-algo`)
     5. Piazza nuovo bracket (`order-algo`)
     6. Log: "Bracket refreshed: SL=X%, TP=Y%, interest_projected=Z%"
   - File: nuovo `bracket_refresher.py` o estensione di `candle_processor.py`
3. **008.C** — Floor guard: se `SL_effective <= 0.02%`, chiudi posizione a mercato con `exit_reason="stop_loss_interest"`.
4. **008.D** — Gate pre-apertura: se `rate_hourly × 24 >= SL_gross`, blocca apertura short con log esplicito.
5. **008.E** — Test: simulare 180h di uptime con APR=15%, verificare che SL tocca zero e scatta il floor guard.
6. **008.F** — Test: verificare gate pre-apertura con tasso troppo alto (APR=100% deve bloccare).
7. **008.G** — Test: verificare refresh bracket (cancel + replace) con dati simulati.

### Acceptance Criteria

- SL si restringe nel tempo come previsto dalla formula
- TP si allontana nel tempo
- Floor guard chiude quando SL effettivo <= 0.02%
- Gate pre-apertura blocca con tassi incompatibili
- Refresh bracket funziona (cancel + replace senza buchi)
- Tempo massimo di detenzione calcolato correttamente

### Limiti Noti (da documentare)

- Tasso fisso: se il tasso sale molto durante il trade, il calcolo sottostima l'interesse reale
- Refresh orario: introduce finestra di rischio operativo (cancel + replace ogni ora)
- Collaterale minimo reale ancora ignoto — non usare in live senza verifica empirica

---

## TASK-SHORT-009 — Supervisor context update

**Status:** Pending
**Tipo:** Backend
**Prerequisito:** TASK-SHORT-005

### Obiettivo

Aggiornare il contesto del Supervisor AI perche' tenga conto dello short attivo e non proponga regolazioni inutili.

### Sottotask

1. **009.A** — Aggiungere al contesto AI (in `supervisor_client.py` o `context_builder.py`):
   ```python
   "short_enabled": session_config.short_enabled,
   "position_side": position_manager.get_open().side if has_open else None,
   "short_blocked_reason": None | "margin_not_enabled" | "signal_rejected",
   ```
2. **009.B** — Aggiornare il prompt del Supervisor per riflettere che lo short e' ora disponibile — rimuovere riferimenti a "SHORT not supported".
3. **009.C** — Verificare che il Supervisor non abbassa la soglia inutilmente in sessioni con short attivo (il problema documentato nel §12 dell'architettura Binance originale).

### Acceptance Criteria

- Il contesto AI include `short_enabled` e `position_side`
- Il prompt non menziona piu' "SHORT not supported"
- Il Supervisor distingue tra "mercato neutro" e "short strutturalmente non disponibile"

---

## TASK-SHORT-010 — Paper mode short

**Status:** Pending
**Tipo:** Backend
**Prerequisito:** TASK-SHORT-005

### Obiettivo

Abilitare lo short anche in paper mode per testare il flusso senza rischi.

### Sottotask

1. **010.A** — `candle_processor.py:686-717` (paper mode path): replicare la logica short anche in paper mode.
2. **010.B** — Paper mode: simulare PnL invertito (per short: `entry_price - exit_price`, non `exit_price - entry_price`).
3. **010.C** — Verificare che il trade log in paper mode mostra correttamente `side=SELL` con PnL corretto.

### Acceptance Criteria

- Trade SELL eseguito in paper mode
- PnL calcolato correttamente (inverted vs long)
- Trade log mostra `side=SELL`

---

## TASK-SHORT-011 — Tests

**Status:** Pending
**Tipo:** Testing
**Prerequisito:** TASK-SHORT-005 → TASK-SHORT-010

### Obiettivo

Testare a fondo tutto il flusso short, dal pricing al time-stop.

### Sottotask

1. **011.A** — Unit test pricing: verificare `_tp_price_from_entry` e `_sl_price_from_entry` con `side="SELL"` — TP deve essere sotto entry, SL sopra entry.
2. **011.B** — Unit test time-stop (TASK-SHORT-008): testare tutte le formule Layer 3-6 con dati noti.
3. **011.C** — Unit test gate pre-apertura e floor guard.
4. **011.D** — Integration test: mock adapter, simulare apertura + chiusura short completa (market sell → bracket → fill → close).
5. **011.E** — Integration test: bracket refresh orario simulato (3 refresh consecutivi, verifica che SL si restringe).
6. **011.F** — Test DB: verificare che `position_side` viene popolato correttamente in `scalping_trades`.

### Acceptance Criteria

- Tutti i test passanti
- Coverage minimo: pricing, time-stop formulas, gate, floor guard, flow completo
- Nessun test dipende da connessione reale a OKX

---

*Documento generato il 21 luglio 2026*
*Fonti: `docs/architecture/okx-short-selling-architecture.md`, `docs/analysis/2026-07-21_okx-short-timestop-design.md`, analisi codebase*
