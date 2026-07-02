# Handoff Protocol — SynthTrade

---

## 🔄 Ultimo Handoff

### Da: Codex → prossima sessione

**Data:** 2026-07-02

**Contesto:** Pianificazione migrazione urgente Binance -> OKX per blocco trading Binance in Italia.

---

### ✅ FASE COMPLETATA: Architettura definitiva OKX + piano task

**Cosa e' stato fatto:**

1. **Creata architettura definitiva**
   - File: `docs/architecture/okx-migration-architecture.md`
   - Decisione: introdurre exchange provider pluggable, non porting 1:1 Binance.
   - Scope: config, adapter REST, market WS, order event stream, router, DB, frontend.

2. **Creato piano implementazione**
   - File: `docs/plans/okx-migration-implementation-plan.md`
   - Fasi: spike demo, config/factory, protocollo exchange, adapter OKX, WS, order stream, router, DB, frontend, cutover.

2b. **Creato breakdown dettagliato multi-agente**
   - File: `docs/plans/okx-migration-task-breakdown.md`
   - Contiene subtasks TASK-1100.A..1116.I, file coinvolti, test, acceptance criteria, rischi e checklist finale.

3. **Aggiornati task loom**
   - Aggiunta EPICA OKX in `docs/TASKS.md`.
   - Creati TASK-1100 -> TASK-1116.
   - Primo task obbligatorio: TASK-1100 spike OKX Demo Trading.
   - TASK-1000 WalletOrchestrator Binance marcato come superseded/sospeso.

4. **Aggiornati indici**
   - `docs/BACKLOG.md`: link corretti a architettura e piano OKX.
   - `docs/STORY.md`: aggiunta milestone v1.4.0.
   - `docs/CHANGELOG.md`: aggiunta entry documentale.

**Decisioni chiave:**
- OKX diventa provider operativo primario.
- Binance resta legacy solo temporaneamente.
- Non implementare lo short/margin prima del cutover OKX long-only.
- Non toccare runtime live prima dello spike OKX Demo Trading.
- Fee/net pricing e' requisito bloccante: recupero fee tier a inizio sessione, `fee_tier_certified`, TP/SL netti e PnL/log coerenti.
- Symbol discovery obbligatoria: default `OKB-EUR`, ma validato dalla lista strumenti OKX all'avvio.
- Dashboard balance e collector intelligence vanno migrati/auditati: oggi esistono chiamate Binance fuori dall'ordine execution.
- Per assegnare lavoro a piu' agenti, usare `docs/plans/okx-migration-task-breakdown.md` come contratto operativo.

**Prossimo step consigliato:**
1. TASK-1100 — risolvere blocco private auth OKX Demo (`50119 API key doesn't exist`).
2. Key UI verificata su OKX Trading demo; IP whitelist verificato da terminale (`77.32.127.105`). Restano da verificare copia completa API key/secret/passphrase, propagazione o rigenerazione key.
3. Dopo auth OK, rieseguire `python scripts/test_okx_demo.py`, poi ordine demo minimo solo con flag esplicito.
4. Solo dopo TASK-1100, partire con TASK-1101 e TASK-1102.

---

### Da: Cline → prossima sessione

**Data:** 2026-07-01

**Contesto:** Sincronizzazione regole loom su tutti i config IDE + pulizia docs/ da file .py.

---

### ✅ FASE COMPLETATA: docs/ cleanup — rimossi file task ridondanti (2026-07-01)

**Cosa è stato fatto:**

1. **Analizzati tutti i 36 file in `docs/`** e categorizzati:
   - 8 file di task ridondanti → eliminati (contenuto già in TASKS.md o ARCHIVE_TASKS.md)
   - 1 duplicato → eliminato (SynthTrade_Short_Selling_Architecture_1.md)
   - 28 file di documentazione legittima → mantenuti

2. **Criterio di eliminazione:**
   - Task completati (TASK-813, TASK-905, TASK-912) → già in TASKS.md o ARCHIVE_TASKS.md → elimina file standalone
   - Task pending (TASK-907) → già in TASKS.md → elimina file standalone
   - Duplicati → elimina la copia più vecchia

3. **File eliminati (x8):**
   - `TASK_813_ALL_ACTIONS_STATUS.md` — TASK-813 già in ARCHIVE_TASKS.md
   - `TASK_813_COMPLETE_ANALYSIS.md` — TASK-813 già in ARCHIVE_TASKS.md
   - `TASK_813_FINAL_SUMMARY.md` — TASK-813 già in ARCHIVE_TASKS.md
   - `TASK_813_IMPLEMENTATION_COMPLETE.md` — TASK-813 già in ARCHIVE_TASKS.md
   - `TASK_TP_SL_NET_PRICING.md` — TASK-905 ✅ già dettagliato in TASKS.md
   - `TASK-907_bug_frontend_paused_reload.md` — TASK-907 Pending già in TASKS.md
   - `SynthTrade_TASK_Fix_Signal_Log_Decision_Types.md` — TASK-912 ✅ già in TASKS.md
   - `SynthTrade_Short_Selling_Architecture_1.md` — duplicato

4. **docs/ ora contiene 28 file .md** categorizzati:
   - Documentazione standard loom (7): ARCHIVE_TASKS, BACKLOG, CHANGELOG, HANDOFF, STORY, TASKS, TDD_LOG
   - Architettura/reference (8): OCO_FLOW, OKX_API_Reference, Piano_Implementazione_supervisor, SynthTrade_MASTER_RECAP, SynthTrade_Scalping_DataFlow_Reference, SynthTrade_ScalpingModule_Plan, SynthTrade_Short_Selling_Architecture, synthtrade-considerazioni-roadmap
   - Recap sessioni (9): RECAP_EPICA_MEMORY_LEARNING, SynthTrade_Piano_Logging_Decisionale_Livello1, SynthTrade_Recap_Errori_Notturni_29-30Giugno2026, SynthTrade_Recap_Sessione_Debug_22-23Giugno2026, SynthTrade_Recap_Sessione_Mean-Reversion-Bug_Short-Selling_25Giugno2026, SynthTrade_Recap_Sessione_Review_Memory_Learning_01Luglio2026, SynthTrade_Recap_Sessione_Strategie_Scalping, SynthTrade_Recap_Sessione_Trailing_Stop_Loss_Strategy_26Giugno2026, synthtrade-recap-sessione-risk-controls-audit
   - Fix/summary (4): BUG_FIX_SUMMARY, PERSISTENCE_FIX, PERSISTENCE_SUMMARY, STOP_WITH_OPEN_POSITION_ANALYSIS

**File modificati:**
- `docs/STORY.md` — aggiunta v1.3.9
- `docs/TASKS.md` — aggiunto TASK-DOCS-CLEANUP
- `docs/HANDOFF.md` — aggiornato

**Verifica:** `dir docs\*.md` → 28 file, nessun .py, nessun file di task standalone

---

### ✅ FASE COMPLETATA: Loom rules sync + docs/ cleanup (2026-07-01)

**Cosa è stato fatto:**

1. **Spostati script Python da `docs/` a `loom/scripts/`**:
   - `extract_tasks.py` e `parse_tasks.py` spostati nella posizione corretta secondo il framework loom
   - Aggiunto path resolution (SCRIPT_DIR → PROJECT_ROOT) per funzionare da `loom/scripts/`

2. **Rimosso `capital_allocator.py` da `docs/`**:
   - Era una vecchia versione duplicata (l'originale è in `synthtrade/backend/app/execution/capital_allocator.py`)

3. **Aggiornati tutti i config IDE** con regole loom complete:
   - `.clinerules/loom.md` — aggiunti comandi update/plugins/parse/extract + doc update section
   - `.cursorrules` — aggiunti parse/extract + doc update section
   - `.windsurfrules` — aggiunti parse/extract + doc update section
   - `CLAUDE.md` — aggiunti parse/extract + doc update section
   - `.cursor/rules/loom.mdc` — aggiunti parse/extract + doc update section
   - `AGENTS.md` — aggiunti parse/extract

4. **Aggiunta sezione "Documentation Update — MANDATORY"** a tutti i config IDE (obbligo di aggiornare TASKS.md, STORY.md, HANDOFF.md alla fine di ogni sessione)

5. **Verificato che `docs/` contenga solo file `.md`**

**File modificati:**
- `.clinerules/loom.md` — riscritto con tutti i comandi + doc update sezione
- `.cursorrules` — aggiunti parse/extract + doc update
- `.windsurfrules` — aggiunti parse/extract + doc update
- `CLAUDE.md` — aggiunti parse/extract + doc update
- `.cursor/rules/loom.mdc` — aggiunti parse/extract + doc update
- `AGENTS.md` — aggiunti parse/extract
- `loom/scripts/extract_tasks.py` — copiato da docs/ con path resolution
- `loom/scripts/parse_tasks.py` — copiato da docs/ con path resolution
- `docs/STORY.md` — aggiunta v1.3.8
- `docs/TASKS.md` — aggiunto TASK-LOOM-CONFIG
- Rimossi da `docs/`: `capital_allocator.py`, `extract_tasks.py`, `parse_tasks.py`

**Verifica:** `dir docs\*.py` → "File non trovato" (nessun .py in docs/)

---

### ✅ FASE COMPLETATA: Riorganizzazione docs/ — ridenominazione, backlog, stato moduli (2026-07-01)

**Cosa è stato fatto:**

1. **Eliminati 4 file ridondanti** (contenuto già in STORY.md):
   - `BUG_FIX_SUMMARY.md`, `PERSISTENCE_FIX.md`, `PERSISTENCE_SUMMARY.md`, `STOP_WITH_OPEN_POSITION_ANALYSIS.md`

2. **Rinominati 15 file** con formato data/topic per identificazione immediata:
   - 9 recap sessioni: `2026-06-20_risk-controls-audit.md`, `2026-06-22_debug-analisi.md`, `2026-06-25_mean-reversion-short.md`, `2026-06-26_trailing-stop-loss.md`, `2026-06-27_strategie-scalping.md`, `2026-06-29_errori-notturni.md`, `2026-06-29_logging-decisionale.md`, `2026-07-01_epica-memory-learning.md`, `2026-07-01_review-memory-learning.md`
   - 6 architettura: `oco-flow-spec.md`, `scalping-dataflow-reference.md`, `scalping-module-plan.md`, `short-selling-architecture.md`, `supervisor-implementation-plan.md`, `roadmap-considerazioni.md`, `okx-api-reference.md`

3. **Aggiunti 20 task investigativi** in TASKS.md (TASK-INVEST-001 → 020) da MASTER_RECAP.md, con status 🔍 "Da Investigare" — non assumiamo siano ancora aperti, ma non li perdiamo.

4. **BACKLOG.md riscritto** come indice strutturato con link ai file di dettaglio:
   - Piani di sviluppo (Short Selling, Trailing Stop Loss, Market Structure, Wallet Orchestrator, Supervisor)
   - Bug da investigare (cross-link a TASKS.md)
   - Reference architetturale (tabella con tutti i documenti)
   - Idee da esplorare ed esperimenti

5. **STORY.md arricchita** con sezione "Stato dei Moduli Architetturali" (tabella 12 moduli con stato 🟢🟡🔴) e link ai bug investigativi.

**File modificati:**
- `docs/BACKLOG.md` — riscritto come indice strutturato
- `docs/STORY.md` — aggiunta sezione stato moduli + v1.3.9
- `docs/TASKS.md` — aggiunti 20 task investigativi
- `docs/HANDOFF.md` — aggiornato
- Eliminati: `BUG_FIX_SUMMARY.md`, `PERSISTENCE_FIX.md`, `PERSISTENCE_SUMMARY.md`, `STOP_WITH_OPEN_POSITION_ANALYSIS.md`
- Rinominati: 15 file recap/architettura

---

### ✅ FASE COMPLETATA: Riorganizzazione recap per argomento (2026-07-02)

**Cosa è stato fatto:**

1. **Creata directory `docs/recap/`** — spostati 10 file:
   - 9 recap sessioni rinominati (formato `YYYY-MM-DD_topic.md`)
   - `MASTER_RECAP.md` (consolidamento generale)

2. **Eliminato `2026-06-27_strategie-scalping.md`** (28 righe ultra-sintetiche, contenuto già in MASTER_RECAP §2.7)

3. **Creati 5 file di analisi tematica** che consolidano informazioni sparse in più recap:

   | File | Tema | Fonti |
   |------|------|-------|
   | `docs/regime-detection-analysis.md` | Regime misclassification, Falling Knife, MarketStructureCollector | 4 recap |
   | `docs/short-selling-roadmap.md` | Short selling, dettagli tecnici Binance Margin, decisioni aperte | 3 recap |
   | `docs/supervisor-issues.md` | Issue note del Supervisor, fix applicati, proposte | 3 recap |
   | `docs/collector-intelligence-status.md` | Stato 8 collector (30% funzionante), priorità fix | 2 recap |
   | `docs/oco-dust-fee-analysis.md` | Bug fee/OCO/dust risolti e da verificare | 3 recap |

4. **Aggiornato BACKLOG.md** — ora funge da indice centrale con:
   - Piani di sviluppo (link alle 5 analisi tematiche)
   - Reference architetturale (tabella completa)
   - Recap storici (tabella con tutti i file in `docs/recap/`)
   - Bug da investigare (cross-link a TASKS.md)

---

### 📊 Stato Attuale

**Fase corrente:** Riorganizzazione docs/ completata

**Struttura finale:**

```
docs/
├── (7 standard loom)          ← ARCHIVE_TASKS, BACKLOG, CHANGELOG, HANDOFF, STORY, TASKS, TDD_LOG
├── analysis/ (5 analisi)      ← analisi tematiche consolidate da più recap
├── plans/ (7 piani/architetture) ← specifiche architetturali e piani implementazione
└── recap/ (9 cronologici)     ← MASTER_RECAP + 8 recap sessioni
```

### `docs/analysis/` — Analisi tematiche (5 file)
- `regime-detection-analysis.md` — Regime misclassification, Falling Knife
- `short-selling-analysis.md` — Short selling roadmap, decisioni aperte
- `supervisor-analysis.md` — Issue note del Supervisor
- `collector-intelligence-analysis.md` — Stato 8 collector (30% funzionante)
- `oco-dust-fee-analysis.md` — Bug fee/OCO/dust

### `docs/plans/` — Piani e architetture (7 file)
- `oco-flow-architecture.md` — Specifica OCO + User Data Stream
- `scalping-dataflow-architecture.md` — Data flow scalping
- `scalping-module-plan.md` — Piano implementazione scalping v2.0
- `short-selling-architecture.md` — Architettura short selling
- `supervisor-implementation-plan.md` — Piano implementazione supervisor
- `okx-api-reference.md` — Riferimento API OKX
- `roadmap-considerazioni.md` — Roadmap alternativa

### `docs/recap/` — Recap storici (9 file)
- `MASTER_RECAP.md` + 8 recap cronologici `YYYY-MM-DD_topic.md`

**Regola per nuovi file:**
- Nuova analisi → `docs/analysis/argomento-analysis.md`
- Nuovo piano/architettura → `docs/plans/argomento-plan.md` o `docs/plans/argomento-architecture.md`
- Nuovo recap sessione → `docs/recap/YYYY-MM-DD_topic.md`

---

### 🎯 Prossimi Step (in ordine)

1. **TASK-907** — Bug Frontend: dati mancanti su reload con sessione PAUSED
2. **TASK-908** — Hardcoded Resume Guard (no-short, regime bearish)
3. **TASK-1000** — WalletOrchestrator: Fase 1 (resolve puro + snapshot)
4. **TASK-INVEST-001→020** — Verificare se i 20 bug di MASTER_RECAP sono ancora aperti o già risolti

---

### 📝 Note Importanti

- **Documentation update obbligatorio** alla fine di OGNI sessione: aggiornare TASKS.md, STORY.md, HANDOFF.md
- **Script Python in `loom/scripts/`**: `parse_tasks.py` e `extract_tasks.py` risolvono i path relativi alla project root
- **docs/ organizzato**: root = standard loom + architettura + analisi tematiche (18 file); `docs/recap/` = cronologia sessioni (9 file)
- **BACKLOG.md** è l'indice centrale che collega tutti i documenti
- **5 analisi tematiche** consolidano informazioni da multipli recap, eliminando ridondanze
- **20 bug da investigare** in TASKS.md sezione "🎯 Task da Investigare"
- Backend: `http://localhost:8888` (porta configurata in `.env`)

**Ultima modifica:** 2026-07-02 — Cline

---

### ✅ FASE COMPLETATA: Close Positions on Session Stop (2026-06-03)

**Cosa è stato fatto:**

1. **Session stop chiude posizioni aperte** — Quando l'utente preme STOP (action: "stop" su `POST /scalping/session`), il backend ora:
   - Recupera il prezzo corrente (candle buffer → Binance REST → entry price fallback)
   - Calcola PnL/PnL% della posizione aperta
   - In **Paper Mode**: chiude la posizione in memoria via `PositionManager.close_position()`
   - In **Live Mode**: esegue market order tramite `Exchange.close_position()` (se exchange configurato)
   - Broadcast evento WS `trade_closed` al frontend
   - Salva il trade chiuso su Supabase (tabella `scalping_trades`)
   - Poi ferma WS broadcast, supervisor, e aggiorna stato sessione come prima

2. **`PositionManager.force_close_all()`** — Nuovo metodo per chiudere forzatamente TUTTE le posizioni aperte contemporaneamente, con log e conteggio.

3. **Fix type safety** — Gestito caso `current_price = None` con fallback a entry price (PnL=0) per evitare crash.

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` — Logica di chiusura posizioni in `action == "stop"`
- `synthtrade/backend/app/scalping/engine/position_manager.py` — Aggiunto `force_close_all()`, import logging

---

### 📊 Stato Attuale

**Fase corrente:** TASK-813 — Bug Fixes & Improvements (close positions su stop ✅)

**Completato:**
- ✅ TASK-800 → TASK-810 (tutti completati)
- ✅ Pipeline diagnostics (log colorati, debug endpoint)
- ✅ MomentumBaseStrategy, CVD simulator, Warmup retry
- ✅ Close positions on session stop (paper + live)

---

### 🎯 Prossimi Step (in ordine)

1. **Avviare sessione scalping** — Testare che i trade partano effettivamente con i nuovi log
2. **Verificare endpoint `/api/scalping/debug/pipeline`** — Controllare collector health e score
3. **TASK-813 completamento** — Eventuali fix rimanenti (dropdown simbolo, pulsanti Watch/Ignore, pulizia directory)
4. **TASK-811 — Regressione E2E**: Test Playwright per scalping session
5. **TASK-812 — Go Live**: Review sicurezza ordini, test LIVE con trade minimo

---

### 📝 Note Importanti

- Backend: `http://localhost:8888` (porta configurata in `.env`)
- Pipeline debug: `GET http://localhost:8888/api/scalping/debug/pipeline`
- I log colorati funzionano su terminali ANSI (PowerShell 7+, VS Code terminal, WSL)
- **Stop session chiude posizioni automaticamente** — non lascia trade orfani
- In live mode l'exchange adapter deve essere configurato in `_execution_state["exchange"]`
- Se exchange non configurato → fallback a chiusura in memoria (come paper)

---

**Ultima modifica:** 2026-06-03 — Cline
