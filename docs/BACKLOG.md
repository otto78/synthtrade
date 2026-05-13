# Backlog — SynthTrade

Idee, feature future e miglioramenti non ancora strutturati come task.

**Regola:** quando un'idea è matura, convertila in task in TASKS.md e rimuovila da qui.

---

## 🔥 Idee Prioritarie

### [FEATURE-MULTI] — Strategie Multi-Asset (Portfolio Diversificato)

**Descrizione:** Aggiungere supporto per strategie che operano su più asset contemporaneamente con allocazione percentuale del capitale in base al rischio di ogni asset. Oggi ogni strategia opera su un singolo pair (es. BTC/USDT). Un portfolio strategy alloca il budget su 2-10 asset con pesi calcolati in base a volatilità/Sharpe/correlazione.

**Cosa cambia:**
- `StrategyParams` avrà un campo opzionale `allocations: list[PortfolioAllocation]`
- Se `allocations` è None → strategia single-asset (comportamento attuale)
- Se popolato → strategia multi-asset con specifica di (asset, weight, signal_params)
- Backtest multi-asset: esegue il segnale su ogni asset indipendentemente, P&L pesato
- Frontend: badge "📊 Multi" / "📈 Single" nella pagina Strategie
- Form di generazione: checkbox "Multi-Asset" + slider numero asset (1-10)
- Una volta approvate: stesso flusso di oggi (nessuna distinzione in "Approvate"/"Attive")

**Task associati:** TASK-PORTFOLIO-001 → 008

---

### [FEATURE-LEARN] — AI Learning Engine + Scheduler Notturno

**Descrizione:** Aggiungere un sistema di memoria che impara dalle strategie generate in passato per migliorare la selezione futura, più uno scheduler notturno che pre-genera strategie mentre l'utente non usa il sistema.

**Cosa serve:**
- `TemplatePerformanceRegistry`: traccia per ogni combinazione (template, pair, timeframe, params) lo score medio storico e quante volte è stata approvata
- Generatore "intelligente": esclude automaticamente combinazioni che storicamente hanno performato male, e prova parametri più fini per quelle promettenti
- Scheduler notturno (02:00): genera strategie per tutti i risk_level e num_assets, salva le migliori nella tabella `pre_generated_strategies`
- API `GET /api/pipeline/pre-generated`: se ci sono strategie pre-generate valide → restituiscile subito (zero attesa), altrimenti genera on-demand
- Feedback loop: approvazione/rifiuto utente aggiorna il registry in tempo reale
- Badge frontend "⚡ Pre-generata" se la strategia viene dalla cache notturna

**Task associati:** TASK-LEARN-001 → 008

---

## 💡 Idee da Esplorare

### [IDEA-003] — Notifiche Telegram
**Descrizione:** Bot Telegram per notifiche su BUY/SELL/BLOCK in tempo reale
**Domande aperte:** libreria `python-telegram-bot` vs webhook diretto?

### [IDEA-004] — Supabase Realtime al posto del WebSocket custom
**Descrizione:** Usare Supabase Realtime su `operation_logs` invece di `api/ws.py`
**Vantaggio:** meno codice da mantenere, già incluso in Supabase

### [IDEA-005] — Dashboard mobile-friendly
**Descrizione:** Layout responsive per monitorare da smartphone
**Nota:** attualmente il design è ottimizzato solo per desktop

---

## 🧪 Esperimenti

### [EXP-001] — Strategia ML-based
**Ipotesi:** un modello LSTM su OHLCV batte le strategie rule-based in backtest
**Successo se:** Sharpe > 1.5 su 180 giorni BTC/USDT 5m
**Tempo massimo:** 1 giornata

---

## 🔧 Debito Tecnico

### [TECH-001] — `TEMPLATES` configurabile via JSON
**Problema:** parametri strategie hardcoded in `strategy_generator.py`
**Soluzione:** caricare da `config/templates.json`
**Urgenza:** Bassa (refactor Fase 1)

### [TECH-002] — Backoff esponenziale nel cascade AI
**Problema:** retry immediati possono aggravare rate limit
**Soluzione:** iniettare `sleep` come dipendenza (0.5s, 1s) senza rallentare i test
**Urgenza:** Media (Fase 5 refactor)

---

**Ultima modifica:** 2026-05-13 — Cline