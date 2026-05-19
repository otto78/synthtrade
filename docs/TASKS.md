# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato.
> I task completati sono spostati in [ARCHIVE_TASKS.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/BACKLOG.md).

---

## 🛠️ Fase 6A — Refactoring & Logica Applicativa

> **Obiettivo:** Risolvere il debito tecnico architetturale, configurazioni dinamiche e comunicazione in tempo reale.

### TASK-187 — 🟢 Fix `dashboard.page.ts` e `dashboard.service.ts`
**Status:** To Do  
**Priorità:** Alta  
**Dettagli:** Gestire correttamente la sottoscrizione ai dati del backend e i casi di errore/timeout.

### TASK-217 — 🔵 Refactor: `SignalResolver` iniettato nel costruttore
**Status:** In Progress  
**Priorità:** Media

### TASK-222 — 🔵 Refactor: intervalli configurabili da `Settings`
**Status:** In Progress  
**Priorità:** Media

### TASK-232 — 🔵 Refactor: `MarketRegimeDetector` con soglie configurabili
**Status:** In Progress  
**Priorità:** Media

### TASK-235 — 🔵 Refactor: template `.jinja2` separato da logica
**Status:** In Progress  
**Priorità:** Media

### TASK-238 — 🔵 Refactor: `@async_retry` decorator in `ai/retry.py`
**Status:** In Progress  
**Priorità:** Media

### TASK-245 — 🔵 Refactor: `MAX_CONCURRENT_EVALS` da `Settings`
**Status:** In Progress  
**Priorità:** Media

---

## 🧪 Fase 6B — Test Suite & Stabilità Frontend

> **Obiettivo:** Garantire la massima stabilità della UI ed eliminare regressioni tramite test E2E e unitari.

### TASK-176 — 🔴 E2E `auth.spec.ts` (login errato → errore; login corretto → /dashboard)
**Status:** To Do  
**Priorità:** Alta

### TASK-177 — 🔴 E2E `strategies.spec.ts` (attivazione e disattivazione end-to-end)
**Status:** To Do  
**Priorità:** Alta

### TASK-178 — 🔴 E2E `logs.spec.ts` (filtro level aggiorna lista)
**Status:** To Do  
**Priorità:** Alta

### TASK-186 — Unit Test `dashboard.page.spec.ts`
**Status:** To Do  
**Priorità:** Media

### TASK-421 — Unit Test `active-trade.page.spec.ts`
**Status:** To Do  
**Priorità:** Media

---

## 📈 EPIC-400 — Pipeline di Esecuzione (Finalizzazione)

> **Obiettivo:** Completare l'integrazione del motore di trading reale e la visualizzazione avanzata dei trade.

### TASK-419 — Componente `ActiveTradeRowComponent`
**Status:** To Do  
**Priorità:** Alta  
**Dettagli:**
- P&L unrealizzato aggiornato da WS price.
- Badge BUY/SELL con animazioni flash al cambio prezzo.
- Calcolo valore posizione in EUR in tempo reale.

### TASK-427 — ✅ Frontend: selezione multi-crypto nel form generazione
**Status:** Done
**Priorità:** Media
**Dettagli:**
- Form con aggiunta di più crypto e slider percentuale.
- Validazione: somma delle percentuali = 100%.
- Backend: AllocationItem model con validazione.
- Frontend: toggle AI auto-selection vs allocation manuale.

### TASK-429 — Gestione errori e retry per exchange failures nel signal loop
**Status:** To Do  
**Priorità:** Alta  
**Dettagli:** Gestione di `asyncio.gather` con `return_exceptions=True` e broadcast di errori via WebSocket.

### TASK-430 — Dashboard: KPI globali strategie attive e trade aperti
**Status:** To Do  
**Priorità:** Media  
**Dettagli:** Aggiunta di `active_strategies_count` e `total_active_pnl_pct` alle statistiche dashboard.
