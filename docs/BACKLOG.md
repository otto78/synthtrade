# Backlog — SynthTrade

Idee, feature future e miglioramenti non ancora strutturati come task.

**Regola:** quando un'idea è matura, convertila in task in TASKS.md e rimuovila da qui.

---

## 🚀 Prossime Epiche (Recuperate da Storico)

### [EPIC-500] — AI Evaluator (Evoluzione Fase 5)
**Descrizione:** Sistema di valutazione avanzata delle strategie tramite LLM per filtrare segnali di scarsa qualità e ottimizzare la selezione.

**Task definiti:**
*   Configurazione `cascade_models` in `app/config.py`.
*   Definizione schema `EvalResult` (Pydantic).
*   Test e implementazione `_call_model()` con decoratore `@async_retry`.
*   Test e implementazione `evaluate_strategy()` (con fallback cascade).
*   Validazione `EvalResult` e integrazione `build_market_context()`.
*   Integrazione pipeline AI in `run_pipeline.py`.
*   Broadcast WS `eval_complete` con `strategy_id`, `verdict`, `score`.
*   Test di integrazione (Pipeline AI + fallback + cache).

### [EPIC-600] — Modulo Scalping (Alta Frequenza)
**Descrizione:** Implementazione motore di trading per alta frequenza/scalping.

**Task definiti:**
*   Implementazione `ScalpingEngine` (bassa latenza).
*   Logica Order Book Depth / Level 2 data.
*   Gestione latenza esecuzione (WebSocket-first).
*   Test di performance su simulatore tick-by-tick.

### [EPIC-700] — Hardening & Deploy
**Descrizione:** Preparazione alla produzione e messa in sicurezza del sistema.

**Task definiti:**
*   Error handling globale e logging strutturato JSON.
*   Dockerfile multi-stage ottimizzato per produzione.
*   Setup Nginx + HTTPS.
*   Configurazione Supabase RLS su tutte le tabelle.
*   Configurazione Supabase Realtime su `operation_logs`.
*   Smoke test post-deploy.

---

## 🔥 Idee Prioritarie

### [FEATURE-MULTI] — Strategie Multi-Asset (Portfolio Diversificato)
**Descrizione:** Supporto per strategie su più asset con allocazione pesata del capitale.

### [FEATURE-LEARN] — AI Learning Engine + Scheduler Notturno
**Descrizione:** Sistema di memoria storica per strategie e pre-generazione notturna.

---

## 💡 Idee da Esplorare

### [IDEA-004] — Supabase Realtime al posto del WebSocket custom
**Descrizione:** Usare Supabase Realtime su `operation_logs` invece di `api/ws.py` per ridurre il debito tecnico

---

## 🧪 Esperimenti

### [EXP-001] — Strategia ML-based
**Ipotesi:** modello LSTM su OHLCV batte le strategie rule-based.


---

**Ultima modifica:** 2026-05-19
