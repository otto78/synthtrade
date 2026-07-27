# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-27. Task completati in `docs/ARCHIVE_TASKS.md`.

---

### Fix: Session log recap + early log capture — ✅ COMPLETED

> **Problemi:**
> 1. Il recap "SESSION ANALYSIS SUMMARY" non veniva incluso nel file .txt scaricato perché l'endpoint filtrava solo righe con timestamp.
> 2. Il `SessionLogHandler` veniva attivato solo dopo l'insert DB, perdendo i log delle chiamate preparatorie (get_balance, get_trade_fee, get_symbol_rules).
>
> **Soluzioni:**
> 1. L'endpoint `download_session_logs()` ora rigenera l'analysis al volo dalle righe di log estratte (retroattivo per tutte le sessioni con log_content).
> 2. Il `SessionLogHandler` viene creato e attaccato subito all'inizio del start, prima delle verifiche di balance/fee. Dopo l'insert DB, l'handler early viene riutilizzato (non sovrascritto) aggiornando db_session_id e session_id.
>
> **File modificato:** `synthtrade/backend/app/scalping/rest/session.py`

---

### TASK-1230: Session Max Loss + Drawdown Fix — 🔧 IN PROGRESS

> **Problema:** `_check_drawdown()` in `trade_executor.py` usa `paper_balance` come base del calcolo. In live mode, `paper_balance` si riduce ad ogni trade aperto (candle_processor.py:686) ma non viene mai ripristinato alla chiusura (solo in paper mode, trade_executor.py:492-493). Risultato: la base del drawdown è artificialmente bassa, bloccando trade a caso.
>
> Inoltre, `_check_daily_loss()` calcola la perdita su base giornaliera, ma le sessioni durano giorni. Serve un **session max loss**: perdita massima dall'inizio della sessione, espressa in % del balance iniziale.

> **Soluzione:**
> 1. Salvare `starting_balance` in DB (`scalping_sessions`) all'avvio sessione, persistente e sopravvive a restart
> 2. Riscrivere `_check_drawdown()` per usare `starting_balance` come base
> 3. Sostituire `_check_daily_loss()` con `_check_session_loss()`: `total_pnl <= -(starting_balance * session_max_loss_pct / 100)` → pausa forzata
> 4. Aggiungere `session_max_loss_pct` al risk config (default 10%)
> 5. Nascondere campo leverage dal frontend (mantenere in DB)

> **Files coinvolti:**
> - `supabase/migrations/` — nuove colonne `starting_balance`, `session_max_loss_pct`
> - `scalping/rest/session.py` — salvare starting_balance all'avvio
> - `main.py` — ripristinare starting_balance al restart
> - `scalping/trade_executor.py` — riscrivere `_check_drawdown()` + `_check_session_loss()`
> - `scalping/candle_processor.py` — usare `_check_session_loss()`, pausa su breach
> - `scalping/rest/config.py` — persistere `session_max_loss_pct`
> - `scalping/_state.py` — default `session_max_loss_pct: 10`
> - `frontend/risk-controls.component.ts` — UI: session_max_loss_pct, nascondere leverage

> **Riferimento:** Log originale: `Max drawdown 10% exceeded. Blocking new real trade.` — trade bloccato nonostante sessione profittevole.

---

### Dashboard: Convert balance to EUR, add session count — ✅ COMPLETED

> **Problema:** Il saldo veniva mostrato in USD invece che EUR. Il totale USD non includeva correttamente EUR (0.72 EUR valorizzati a $0). Mancavano indicatori sessione scalping attiva.

> **Soluzione:**
> 1. Fixato `_get_usd_price()` in `okx_balance.py` per gestire conversione EUR→USD
> 2. Dashboard ora usa `get_total_balance_eur()` → saldo in EUR
> 3. Aggiunto campo `currency: "EUR"` e `active_session_count` nel response
> 4. Rimossi PnL Oggi, Trade Chiusi Oggi, equity chart (API OKX per storico non disponibili su EEA — 404)
> 5. Frontend: 4 card (Saldo OKX €, Strategie Attive, Trade Aperti, Sessione Scalping)

> **File modificati:** `dashboard.py`, `okx_balance.py`, `dashboard.model.ts`, `dashboard.service.ts`, `dashboard.page.ts`, `dashboard.page.spec.ts`

> **Branch:** `feat/dashboard-eur`

---

### EPICA: Short Selling OKX Spot Margin — ❌ CANCELLED

> **Stato:** Cancellata definitivamente (2026-07-24). Budget insufficiente (~€300) per margin trading su OKX EEA.
> **Audit:** Vedi `docs/analysis/audit-short-selling-cancelled.md`
> **Decisione:** Tutto il codice short è stato rimosso. Focus esclusivo su long trading.

---
