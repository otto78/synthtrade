# Supervisor AI — Issue e Limitazioni Note

> **Tema trasversale** che emerge da: `docs/recap/2026-06-20_risk-controls-audit.md`, `docs/recap/2026-06-22_debug-analisi.md`, `docs/recap/MASTER_RECAP.md`.
> **Piano:** `docs/supervisor-implementation-plan.md`.

---

## 1. Issue note

| # | Issue | Prima osservata | Priorità |
|---|-------|----------------|----------|
| 1 | **Sync bug `strategy_selected` vs `strategy_executed`**: UI mostra strategia sbagliata (es. "Momentum Base") mentre i log mostrano `rsi_bollinger` | 20/06 | 🔴 Alta |
| 2 | **Bias `outcome_label`**: in mercato laterale, ogni `no_action` produce delta PnL ~0, dando falsa impressione di "decisioni corrette" | 22-23/06 | 🟢 Bassa |
| 3 | **Soglia dinamica senza decadimento**: `signal_strength_threshold` cambiata 5 volte in una sessione (8.0→6.0→5.5→7.5→10.5), persiste tra sessioni senza rivalutazione | 22-23/06 | 🟡 Media |
| 4 | **Supervisor non ha visibilità del blocco SHORT** nel system prompt — propone `update_threshold`/`change_strategy` quando il vero blocco è architetturale | 22-23/06 | 🟢 Bassa |
| 5 | **APScheduler job "missed" ripetuti**: chiamate AI sincrone bloccano il thread principale | 22-23/06 | 🟡 Media |
| 6 | **Assenza cooldown dopo consecutive losses**: trade riaperti 42s dopo stop_loss, nessuna pausa nonostante 3 perdite consecutive | 20/06, 25/06 | 🟡 Media |
| 7 | **Regime misclassification inaffidabile**: root cause di falling knife e mean-reversion contro-trend | 22-23/06 | 🔴 Alta |

---

## 2. Fix già applicati

| Fix | Quando | Impatto |
|-----|--------|---------|
| Cooldown 20 min su cambio strategia | 27-28/06 | Supervisor non oscilla più tra strategie |
| Whitelist regime→strategia | 27-28/06 | Supervisor non assegna `ema_cross` in regime `ranging` |
| Trend tracking Intelligence Score (log-only) | 22-23/06 | Dati disponibili per debug, non ancora usati operativamente |

---

## 3. Proposte non implementate

### 3.1 Job di riflessione periodica
Digest in tempo reale + job APScheduler periodico con tabella `supervisor_notes`.

### 3.2 Persistere decisioni BLOCK/REJECTED
Oggi l'informazione resta solo nei log testuali volatili. Le decisioni bloccate non sono interrogabili.

### 3.3 Isolare chiamate AI in ThreadPoolExecutor
Per risolvere gli APScheduler job missed (bug #5).

### 3.4 Meccanismo di decadimento soglia dinamica
Reset tra sessioni o a cambi di regime significativi (bug #3).

---

## 4. Collegamento con task

| Task | Cosa | Priorità |
|------|------|----------|
| TASK-903 | Isteresi RegimeDetector (K candele) | 🟡 Media |
| TASK-904 | StrategySelector DB-driven | 🟢 Bassa |
| TASK-908 | Resume Guard (palliativo short) | 🔴 Alta |
| TASK-INVEST-001 | Sync bug strategia | 🔍 Da Investigare |
| TASK-INVEST-014 | Blocco SHORT nel prompt | 🔍 Da Investigare |
| TASK-INVEST-015 | APScheduler job missed | 🔍 Da Investigare |
| TASK-INVEST-017 | Bias outcome_label | 🔍 Da Investigare |
| TASK-INVEST-018 | Soglia senza decadimento | 🔍 Da Investigare |

---

**Ultima modifica:** 2026-07-02 — Cline