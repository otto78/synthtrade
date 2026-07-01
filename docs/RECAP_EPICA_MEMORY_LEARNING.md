# REPORT COMPLETO - EPICA MEMORY & LEARNING SUPERVISOR AI

**Data:** 2026-07-01  
**Status:** ✅ COMPLETATA (livello 1-3 implementati)  
**Versione:** v1.0

---

## 🎯 **OBIETTIVO DELL'EPICA**

Implementare un sistema di memoria e apprendimento per il Supervisor AI che permetta di:
1. **Apprendere dai dati passati** (performance storiche per strategy/regime)
2. **Evitare loop decisionali** (memoria delle ultime decisioni)
3. **Migliorare le decisioni future** basandosi su evidence storiche

---

## 📊 **ARCHITETTURA DELLA MEMORIA**

### **Livello 1: Vista Aggregata (TASK-897) ✅**
**File:** `supabase/migrations/20260629000002_create_signal_outcome_view.sql`

**Funzionalità:**
- Vista SQL `signal_outcome_by_strategy_regime` aggrega performance per (strategy_type, regime)
- Calcola: n_trades, n_wins, win_rate_pct, avg_pnl, total_pnl
- Filtra solo decisioni `execute` con trade `closed`
- Join tra `session_signal_log` e `scalping_trades` via `signal_log_id`

**Query structure:**
```sql
SELECT
    sl.strategy_type,
    sl.regime,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(COUNT(t.id) FILTER (WHERE t.pnl > 0)::numeric / NULLIF(COUNT(t.id), 0) * 100, 1) AS win_rate_pct,
    ROUND(AVG(t.pnl), 4) AS avg_pnl,
    ROUND(SUM(t.pnl), 4) AS total_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE sl.decision_type = 'execute' AND t.status = 'closed'
GROUP BY sl.strategy_type, sl.regime;
```

---

### **Livello 2: Historical Context Builder (TASK-901) ✅**
**File:** `synthtrade/backend/app/scalping/supervisor/historical_context.py`

**Funzionalità:**
- Funzione `build_historical_context()` legge dalla vista aggregata
- Cache in-process con TTL 5 minuti (evita query ad ogni tick)
- Filtra combinazioni con n_trades < 5 (campione insufficiente)
- Tracking best/worst combinations per win rate
- Gestione errori con fallback a empty context

**Interfaccia:**
```python
async def build_historical_context() -> dict:
    return {
        "historical_performance": {
            "rsi_bollinger/ranging": {"n_trades": 30, "win_rate_pct": 43.3, "avg_pnl": -0.12},
        },
        "best_combination": "rsi_bollinger/ranging",
        "worst_combination": "ema_cross/trending_down",
        "total_historical_trades": 70,
        "data_freshness": "2026-06-29T14:30:00Z"
    }
```

**Caratteristiche tecniche:**
- Cache globale `_historical_cache` con timestamp `_cache_timestamp`
- Funzione `clear_historical_cache()` per testing e refresh manuale
- Async wrapper con `asyncio.to_thread()` per query DB non bloccanti
- Log dettagliati per debug e monitoraggio

---

### **Livello 3: Supervisor Context-Aware (TASK-902) ✅**
**File modificati:**
- `synthtrade/backend/app/ai/supervisor_context.py`
- `synthtrade/backend/app/scalping/supervisor/supervisor_client.py`

**Funzionalità:**
- Integrazione di `build_historical_context()` nel context builder
- Sezione `=== PERFORMANCE STORICA ===` nel prompt supervisor
- Regole decisionali basate su win_rate storico

**Nuove regole nel system prompt:**
```
⚠️ REGOLA PERFORMANCE STORICA (TASK-902):
- Se PERFORMANCE STORICA mostra win_rate < 35% per la combo (regime, strategia) corrente con n_trades >= 10 → considera fortemente change_strategy
  (la combinazione storica ha sottoperformato significativamente, cambiare approccio)
- Se PERFORMANCE STORICA mostra win_rate > 70% per la combo (regime, strategia) corrente con n_trades >= 10 → evita change_strategy
  (la combinazione storica ha funzionato bene, mantenerla)
```

**Formato nel prompt:**
```
=== PERFORMANCE STORICA (tutte le sessioni) ===
rsi_bollinger/ranging:    30 trade | win_rate=43.3% | avg_pnl=-0.12 USDC
ema_cross/trending_down:  12 trade | win_rate=25.0% | avg_pnl=-0.45 USDC
[campione insufficiente:  ema_cross/ranging, stoch_rsi_bb_squeeze/volatile]
Migliore: rsi_bollinger/ranging | Peggiore: ema_cross/trending_down
Totale trade storici: 42
```

---

## 🧠 **MEMORIA CROSS-SESSION (ESISTENTE - TASK-847)**

**File:** `synthtrade/backend/app/ai/supervisor_context.py`

**Funzionalità:**
- Recupera ultime 10 decisioni da `supervisor_memory` per symbol
- **Filtro CROSS-SESSION**: `.eq("symbol", symbol)` (NON per session_id)
- Include decisioni di tutte le sessioni precedenti dello stesso simbolo
- Mostra nel prompt come `=== DECISIONI PRECEDENTI (ultime 10) ===`

**Design originale:**
```python
resp = supabase.table("supervisor_memory") \
    .select("action, reason, decided_at, was_applied, market_bias") \
    .eq("symbol", symbol) \        # ✅ CROSS-SESSION MEMORY
    .order("decided_at", desc=True) \
    .limit(10) \
    .execute()
```

**Obiettivo:** 
- Evitare loop decisionali immediati
- Apprendere da errori di sessioni precedenti
- Contesto delle ultime decisioni per il simbolo

---

## 🗄️ **PERSISTENZA DATI (ESISTENTE - TASK-846)**

**File:** `supabase/migrations/20260616_supervisor_memory.sql`

**Tabella:** `supervisor_memory`

**Campi principali:**
- `session_id` - ID sessione corrente
- `symbol` - Simbolo trading
- `decided_at` - Timestamp decisione
- `action` - Tipo decisione (change_strategy, update_params, etc.)
- `reason` - Motivazione decisione
- `confidence` - Livello confidenza
- `market_bias` - Bias mercato
- `market_context` - JSONB con contesto completo (regime, funding, cvd, score, patterns)
- `session_perf` - JSONB con performance sessione (total_trades, win_rate, pnl)
- `was_applied` - Se decisione è stata applicata
- `blocked_reason` - Motivo blocco (se non applicata)
- `outcome_verified_at`, `outcome_pnl_delta`, `outcome_label` - Outcome verifica (TASK-848)

**Indici ottimizzati:**
- `idx_supervisor_memory_symbol_decided` - Query per symbol
- `idx_supervisor_memory_session` - Query per sessione
- `idx_supervisor_memory_action_applied` - Query per tipo azione
- `idx_supervisor_memory_outcome_pending` - Decisioni da verificare

---

## 🔄 **FLUSSO COMPLETTO DELLA MEMORIA**

### **1. Salvataggio Decisioni (Sessione Corrente)**
```
SupervisorScheduler._tick() 
  → calcola contesto (snapshot, score, ta_patterns, vol_anomaly)
  → chiama supervisor_client.decide()
  → supervisor prende decisione
  → _save_decision_to_memory() salva su DB
  → market_context arricchito (TASK-910) ✅
  → session_perf calcolato da trade_history (TASK-858) ✅
```

### **2. Recupero Memoria per Nuova Decisione**
```
supervisor_client.decide()
  → build_scalping_context()
    → recupera performance sessione corrente (TASK-860) ✅
    → recupera decisioni precedenti cross-session (TASK-847) ✅
    → recupera performance storica aggregata (TASK-901) ✅
  → _format_context()
    → formatta performance sessione
    → formatta decisioni precedenti
    → formatta performance storica (TASK-902) ✅
  → invia prompt completo all'AI
```

### **3. Verifica Outcome (Background Job - TASK-848)**
```
verify_supervisor_outcomes_job() (ogni 5 min)
  → query decisioni applicate 25-35 min fa senza outcome
  → calcola variazione PnL post-decisione
  → classifica: positive/negative/neutral
  → aggiorna outcome_verified_at, outcome_pnl_delta, outcome_label
```

---

## 📈 **CAPACITÀ DI APPRENDIMENTO IMPLEMENTATE**

### **1. Apprendimento da Performance Sessione Corrente**
**Regole esistenti (TASK-861):**
- `< 5 trade totali` → no_action (troppo presto per valutare)
- `win_rate > 60% e total_pnl > 0` → no_action (strategia funziona)
- `ultime 3 decisioni uguali` → no_action (evita loop)
- `coverage < 50%` → no_action (dati insufficienti)

### **2. Apprendimento da Performance Storica (NUOVO - TASK-902)**
**Nuove regole:**
- `win_rate < 35% per combo corrente con n_trades >= 10` → considera change_strategy
- `win_rate > 70% per combo corrente con n_trades >= 10` → evita change_strategy

### **3. Apprendimento da Decisioni Precedenti (ESISTENTE - TASK-847)**
**Meccanismo:**
- Ultime 10 decisioni mostrate nel prompt
- AI può vedere pattern e evitare ripetizioni
- Cross-session: include sessioni precedenti dello stesso simbolo

### **4. Apprendimento da Outcome (ESISTENTE - TASK-848)**
**Meccanismo:**
- Verifica automatica outcome decisioni dopo 30 min
- Classificazione positive/negative/neutral
- Potenziale uso futuro per reinforcement learning

---

## 🧪 **TEST IMPLEMENTATI**

**File:** `synthtrade/backend/tests/unit/test_historical_context.py`

**Test cases:**
1. `test_build_historical_context_empty_data` - Gestione dati vuoti
2. `test_build_historical_context_with_data` - Elaborazione dati reali
3. `test_build_historical_context_cache` - Funzionamento cache
4. `test_clear_historical_cache` - Clear cache function
5. `test_get_empty_context` - Struttura empty context

**Copertura:**
- ✅ Mock Supabase client
- ✅ Async test con pytest-asyncio
- ✅ Verifica cache TTL
- ✅ Gestione errori
- ✅ Filtraggio dati insufficienti

---

## 📁 **FILE CREATI/MODIFICATI**

### **Nuovi File:**
1. `synthtrade/backend/app/scalping/supervisor/historical_context.py` (147 righe)
2. `synthtrade/backend/tests/unit/test_historical_context.py` (146 righe)

### **File Modificati:**
1. `synthtrade/backend/app/ai/supervisor_context.py` (+19 righe)
2. `synthtrade/backend/app/scalping/supervisor/supervisor_client.py` (+37 righe, +4 righe system prompt)

### **File Database:**
1. `supabase/migrations/20260629000002_create_signal_outcome_view.sql` (esistente)

---

## 🎯 **RISULTATI ATTESI**

### **Scenario 1: Nuova Sessione**
1. Supervisor carica performance storica da tutte le sessioni passate
2. Se combo (regime, strategy) ha win_rate < 35% → consider change
3. Se combo ha win_rate > 70% → mantenere strategia
4. Ultime 10 decisioni mostrate per evitare loop

### **Scenario 2: Sessione in Corso**
1. Performance sessione corrente calcolata da trade in-memory
2. Se win_rate > 60% → no_action (non interferire)
3. Decisioni salvate in `supervisor_memory` con contesto completo
4. Outcome verificato automaticamente dopo 30 min

### **Scenario 3: Riavvio Backend**
1. Carica decisioni cross-session per symbol
2. Carica performance storica aggregata
3. Cache 5 minuti evita query ripetute
4. Supervisor mantiene memoria persistente

---

## 🚀 **VANTAGGI IMPLEMENTATI**

### **1. Evidence-Based Decision Making**
- Decisioni basate su dati storici quantitativi
- Win rate per (strategy, regime) invece di intuizioni
- Evita cambi strategia non necessari

### **2. Loop Prevention**
- Memoria ultime 10 decisioni
- Regole anti-loop nel system prompt
- Cross-session memory per pattern a lungo termine

### **3. Adaptive Behavior**
- Soglie dinamiche basate su performance
- Cambio strategia quando necessario
- Mantenimento strategie che funzionano

### **4. Performance Tracking**
- Aggregazione automatica via SQL view
- Cache per efficienza
- Verification automatica outcome

---

## ⚠️ **LIMITAZIONI NOTE**

### **1. Dipendenza da Dati Storici**
- Richiede almeno 2 sessioni live con trade chiusi
- Combinazioni con n_trades < 5 marcate insufficienti
- Win rate affidabile solo con campione sufficiente

### **2. No Reinforcement Learning**
- Outcome verificato ma non usato per training
- Classificazione positive/negative/neutral manuale
- Potenziale espansione futura con RL

### **3. Frontend Integrato (TASK-911 ✅)**
- ✅ Endpoint GET `/scalping/supervisor/history?session_id={session_id}` per fetch storico
- ✅ `SupervisorLogComponent` carica decisioni sessione corrente al mount
- ✅ Nuove decisioni via WS si accodano in cima allo storico
- ✅ Visualizzazione decisioni bloccate (`was_applied=False`, `blocked_reason`)
- ✅ `SupervisorApiService` per fetch REST

### **4. Context Window Limitato**
- Ultime 10 decisioni solo
- No full history analysis
- Potenziale espansione con RAG

---

## 📊 **METRICHE DI SUCCESSO**

### **Qualitative:**
- ✅ Supervisor ha accesso a performance storiche
- ✅ Decisioni basate su evidence invece di solo contesto attuale
- ✅ Sistema anti-loop funzionale
- ✅ Persistenza completa decisioni

### **Quantitative (da verificare):**
- [ ] Riduzione cambi strategia non necessari
- [ ] Miglioramento win rate dopo N sessioni
- [ ] Riduzione loop decisionali
- [ ] Cache hit rate > 90%

---

## 🔮 **PROSSIMI SVILUPPI POTENZIALI**

### **TASK-911 (Frontend):**
- Endpoint GET `/scalping/supervisor/history?session_id={session_id}`
- Caricamento decisioni sessione corrente in SupervisorLog
- Visualizzazione storico decisioni

### **Reinforcement Learning:**
- Usare outcome verification per training
- Reward function basata su PnL
- Policy improvement iterativa

### **RAG System:**
- Full history analysis con vector DB
- Semantic search per pattern simili
- Context window espansa

### **Explainability:**
- Dashboard performance storica
- Analisi decisioni AI
- Attribution analysis

---

## 🎉 **CONCLUSIONI**

L'epica Memory & Learning è **completata ai livelli fondamentali** (1-3). Il supervisor ora ha:

1. ✅ **Memoria cross-session** (ultime 10 decisioni)
2. ✅ **Memoria storica aggregata** (win rate per strategy/regime)
3. ✅ **Regole di apprendimento** dai dati passati
4. ✅ **Persistenza completa** con contesto arricchito
5. ✅ **Verification automatica** outcome decisioni

Il sistema è **funzionalmente completo** per l'apprendimento basato su evidence storica. Le prossime espansioni (frontend, RL, RAG) possono aggiungere ulteriori capacità ma non sono necessarie per il funzionamento base.

**Status:** ✅ **PRODOTTO READY PER PRODUZIONE**