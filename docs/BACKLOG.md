# Backlog — SynthTrade

Idee, feature future e miglioramenti non ancora strutturati come task.

**Regola:** quando un'idea è matura, convertila in task in TASKS.md e rimuovila da qui.

---

## 🔥 Idee Prioritarie

### [IDEA-001] — Live trading (Fase 6+)
**Descrizione:** Passare da paper trading a ordini reali su Binance
**Requisiti da chiarire:**
- [ ] Gestione errori ordini parzialmente eseguiti
- [ ] Riconciliazione posizioni aperte al restart
- [ ] `OrderTracker` già pronto dalla Fase 4 — collegare a exchange reale
**Dipendenze:** Fase 6 hardening completata, smoke test superati

### [IDEA-002] — Multi-pair support
**Descrizione:** Estendere il generatore a ETH/USDT, SOL/USDT oltre BTC/USDT
**Effort stimato:** 2–4 ore (parametrizzare `PAIRS` in `strategy_generator.py`)

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

**Ultima modifica:** 2025-01-17 — Amazon Q
