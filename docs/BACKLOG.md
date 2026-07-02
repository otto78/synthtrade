# Backlog — SynthTrade

> **Indice strutturato** dei piani di sviluppo, idee future e reference architetturale.
> Le epiche e idee qui elencate sono punti di partenza per nuovi task in `TASKS.md`.
> I dettagli completi sono nei file di documentazione collegati.

---

## 🚀 Piani di Sviluppo

### 🚨 Migrazione Binance → OKX (PRIORITÀ ASSOLUTA)
- **Motivazione:** Binance ha chiuso i trade in Europa
- **Analisi:** `docs/analysis/okx-api-reference-analysis.md`
- **Architettura definitiva:** `docs/architecture/okx-migration-architecture.md`
- **Piano implementazione:** `docs/plans/okx-migration-implementation-plan.md`
- **Stato:** Architettura e task loom definiti — primo step TASK-1100 spike Demo Trading
- **Impatto:** Modifica strutturale dell'integrazione exchange (REST + WebSocket + autenticazione + OCO/TP-SL + margin)

### Short Selling (4 fasi)
- **Analisi:** `docs/analysis/short-selling-analysis.md`
- **Architettura:** `docs/architecture/short-selling-architecture.md`
- **Task corrente:** sospeso fino al cutover OKX; TASK-1000 e' superseded dal modello OKX
- **Recap:** `docs/recap/2026-06-25_mean-reversion-short.md`, `docs/recap/2026-06-26_trailing-stop-loss.md`

### Trailing Stop Loss Strategy ("Growth Strategy")
- **Analisi:** `docs/recap/2026-06-26_trailing-stop-loss.md`
- **Stato:** Solo proposta — nessun codice
- **Punti aperti:** collocazione codice, frequenza rivalutazione, interazione con Risk Manager

### Market Structure / Supporti-Resistenze
- **Proposta:** `docs/analysis/regime-detection-analysis.md` §4.2-4.3
- **Stato:** Nuovo collector `MarketStructureCollector` da progettare
- **Dipendenze:** dati OHLCV già disponibili

### Wallet Orchestrator
- **Task corrente:** sospeso; TASK-1000 era specifico per Binance Margin
- **Architettura:** snapshot→resolve→execute→verify, priorità Spot→Funding→Earn
- **Dettaglio:** `docs/analysis/short-selling-analysis.md` §3

### Supervisor AI — Miglioramenti
- **Analisi:** `docs/analysis/supervisor-analysis.md`
- **Piano:** `docs/architecture/supervisor-implementation-plan.md`
- **Task aperti:** TASK-903 (isteresi RegimeDetector), TASK-904 (DB-driven StrategySelector)

### Collector Intelligence — Fix
- **Analisi:** `docs/analysis/collector-intelligence-analysis.md`
- **Obiettivo:** Portare dal 30% al 100% i collector funzionanti

### OCO / Fee / Dust — Verifiche
- **Analisi:** `docs/analysis/oco-dust-fee-analysis.md`
- **Stato:** 4 patch da confermare su trade reale

---

## 🎯 Bug da Investigare (da MASTER_RECAP.md)

> 20 bug identificati nel consolidamento del 26/06/2026.
> **Status:** Da verificare se ancora aperti o già risolti senza documentazione.

Vedi `docs/TASKS.md` sezione "🎯 Task da Investigare (da MASTER_RECAP.md)":
- TASK-INVEST-001 → TASK-INVEST-020

---

## 📂 Struttura docs/

```
docs/
├── (7 standard loom)          ← ARCHIVE_TASKS, BACKLOG, CHANGELOG, HANDOFF, STORY, TASKS, TDD_LOG
├── analysis/ (6 analisi)      ← analisi tematiche consolidate e reference API
├── plans/ (1 piano)           ← piani implementativi attivi
└── recap/ (9 cronologici)     ← MASTER_RECAP + 8 recap sessioni
```

### `docs/analysis/` — Analisi tematiche

| File | Contenuto | Fonti |
|------|-----------|-------|
| `docs/analysis/regime-detection-analysis.md` | Regime misclassification, Falling Knife, MarketStructureCollector | 4 recap |
| `docs/analysis/short-selling-analysis.md` | Short selling roadmap, dettagli tecnici, decisioni aperte | 3 recap |
| `docs/analysis/supervisor-analysis.md` | Issue note del Supervisor, fix applicati, proposte | 3 recap |
| `docs/analysis/collector-intelligence-analysis.md` | Stato 8 collector, priorità di fix | 2 recap |
| `docs/analysis/oco-dust-fee-analysis.md` | Bug fee/OCO/dust risolti e da verificare | 3 recap |
| `docs/analysis/okx-api-reference-analysis.md` | Reference tecnico OKX e differenze Binance | Ricerca API |

### `docs/architecture/` — Piani e architetture

| File | Contenuto |
|------|-----------|
| `docs/architecture/oco-flow-architecture.md` | Specifica definitiva flusso OCO + User Data Stream (v2.1) |
| `docs/architecture/scalping-dataflow-architecture.md` | Data flow completo modulo scalping |
| `docs/architecture/scalping-module-plan.md` | Piano implementazione modulo scalping v2.0 |
| `docs/architecture/short-selling-architecture.md` | Architettura short selling a 4 fasi |
| `docs/architecture/supervisor-implementation-plan.md` | Piano implementazione supervisor AI |
| `docs/architecture/okx-migration-architecture.md` | Architettura definitiva migrazione Binance -> OKX |
| `docs/architecture/roadmap-considerazioni.md` | Indice sintetico + approfondimenti unici (session log schema, criteri testnet→mainnet, audit Risk Control) |

### `docs/plans/` — Piani implementativi

| File | Contenuto |
|------|-----------|
| `docs/plans/okx-migration-implementation-plan.md` | Piano operativo TASK-1100 -> TASK-1113 per migrazione OKX |

### `docs/recap/` — Recap storici

| File | Contenuto |
|------|-----------|
| `docs/recap/MASTER_RECAP.md` | Consolidamento completo di 8 sessioni (20-28/06/2026) |
| `docs/recap/2026-06-20_risk-controls-audit.md` | Audit Risk Controls, fix updated_at |
| `docs/recap/2026-06-22_debug-analisi.md` | Bug OCO, SignalScoreEngine, trend tracking |
| `docs/recap/2026-06-25_mean-reversion-short.md` | Mean-Reversion Bug, Short Selling pianificazione |
| `docs/recap/2026-06-26_trailing-stop-loss.md` | Proposta Trailing Stop Loss Strategy |
| `docs/recap/2026-06-29_errori-notturni.md` | Bug tasks_alive, watchdog, rumore DNS |
| `docs/recap/2026-06-29_logging-decisionale.md` | Piano implementazione logging decisionale (5 fasi) |
| `docs/recap/2026-07-01_epica-memory-learning.md` | Epica Memory & Learning completata |
| `docs/recap/2026-07-01_review-memory-learning.md` | Review superset con query Supabase |

---

## 💡 Idee da Esplorare

### [IDEA-004] — Supabase Realtime al posto del WebSocket custom
**Descrizione:** Usare Supabase Realtime su `operation_logs` invece di `api/ws.py` per ridurre il debito tecnico

### [IDEA-MULTI] — Strategie Multi-Asset (Portfolio Diversificato)
**Descrizione:** Supporto per strategie su più asset con allocazione pesata del capitale

### [IDEA-LEARN] — AI Learning Engine + Scheduler Notturno
**Descrizione:** Sistema di memoria storica per strategie e pre-generazione notturna

---

## 🧪 Esperimenti

### [EXP-001] — Strategia ML-based
**Ipotesi:** modello LSTM su OHLCV batte le strategie rule-based

---

**Ultima modifica:** 2026-07-02 — Architettura definitiva e piano task migrazione OKX
