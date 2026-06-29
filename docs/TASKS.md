# TASKS.md — SynthTrade Task Tracking

## Task Attivi

### TASK-901 — Livello 2: Context Builder storico (2026-06-29)

**Status:** Pending
**Priorità:** ALTA
**Dipendenze:** TASK-897 ✅ (vista `signal_outcome_by_strategy_regime`) + almeno 2 sessioni live con trade chiusi e `signal_log_id` popolato

**Obiettivo:** Creare un componente che legge la vista aggregata win rate (Livello 1) e produce un dict strutturato da iniettare nel prompt del supervisor ad ogni tick.

**File da creare:** `synthtrade/backend/app/scalping/supervisor/historical_context.py`

**Interfaccia:**
```python
async def build_historical_context() -> dict:
    # Legge signal_outcome_by_strategy_regime da Supabase
    # Filtra combinazioni con n_trades < 5 (campione insufficiente)
    # Cache TTL 5 minuti
    # Returns:
    {
        "historical_performance": {
            "rsi_bollinger/ranging": {"n_trades": 30, "win_rate_pct": 43.3, "avg_pnl": -0.12},
        },
        "best_combination": "rsi_bollinger/ranging",
        "worst_combination": "ema_cross/trending_down",
        "total_historical_trades": 70,
        "data_freshness": "2026-06-29T14:30:00Z"
    }
```

**Task:**
1. Implementare `build_historical_context()` con query su `signal_outcome_by_strategy_regime`
2. Cache in-process 5 minuti (evita query ad ogni tick del supervisor)
3. Combinazioni con n_trades < 5 → chiave `insufficient_data` nel risultato
4. Test unitario con mock Supabase

**Verifica:** Dopo 2+ sessioni live, il dict contiene dati reali in `historical_performance`.

---

### TASK-902 — Livello 3: Supervisor context-aware (2026-06-29)

**Status:** Pending
**Priorità:** ALTA
**Dipendenze:** TASK-901

**Obiettivo:** Integrare il contesto storico di TASK-901 nel prompt del supervisor. Oggi il supervisor conosce solo la sessione corrente — con questo task conoscerà le performance di tutte le sessioni passate per (strategia, regime).

**File da modificare:**
- `synthtrade/backend/app/ai/supervisor_context.py` — chiamare `build_historical_context()` e aggiungerlo al context dict
- `synthtrade/backend/app/scalping/supervisor/supervisor_client.py` — aggiungere sezione `=== PERFORMANCE STORICA ===` in `_format_context()`
- `_SUPERVISOR_SYSTEM_PROMPT` — aggiungere regola: se win_rate < 35% per la combo (regime, strategia) corrente con n_trades >= 10 → considera `change_strategy`

**Formato nel prompt:**
```
=== PERFORMANCE STORICA (tutte le sessioni) ===
rsi_bollinger/ranging:    30 trade | win_rate=43.3% | avg_pnl=-0.12 USDC
ema_cross/trending_down:  12 trade | win_rate=25.0% | avg_pnl=-0.45 USDC
[campione insufficiente:  ema_cross/ranging, stoch_rsi_bb_squeeze/volatile]
Migliore: rsi_bollinger/ranging | Peggiore: ema_cross/trending_down
```

**Verifica:** Nel log supervisor compare il blocco `=== PERFORMANCE STORICA ===` con dati reali.

---

### TASK-903 — RegimeDetector: isteresi K candele (2026-06-29)

**Status:** Pending
**Priorità:** MEDIA

**Problema:** Il regime cambia ad ogni candela se le soglie ATR/price_change oscillano vicino ai boundary → flickering → supervisor riceve contesti contraddittori → dati storici per regime inquinati.

**File da modificare:** `synthtrade/backend/app/scalping/engine/regime_detector.py`

**Implementazione:**
- Aggiungere `_pending_regime: Optional[str]` e `_pending_count: int`
- Il regime committed cambia SOLO se lo stesso candidato si osserva per K candele consecutive (default K=3, configurabile da `scalping_runtime_config`)
- Se il candidato cambia prima di K → reset counter
- Proprietà pubblica `pending_regime` per debug nel `/debug/pipeline` endpoint

**Verifica:** Su log di una sessione di 30 minuti, il regime non cambia più di 1 volta ogni 3 minuti.

---

### TASK-904 — StrategySelector DB-driven (2026-06-29)

**Status:** Pending
**Priorità:** BASSA
**Dipendenze:** TASK-902 (prerequisito logico — il supervisor context-aware è il consumatore principale)

**Problema:** Il mapping `regime → strategia_consentita` è hardcoded in due posti (`strategy_selector.py` e `supervisor_scheduler.py`). Il supervisor non può modificarlo senza deploy.

**File da modificare:**
- `synthtrade/backend/app/scalping/engine/strategy_selector.py` — leggere mapping da `scalping_runtime_config` con fallback agli attuali valori hardcoded
- `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py` — sostituire `REGIME_ALLOWED_STRATEGIES` dict hardcoded con lettura da DB
- Migration: aggiungere chiavi `regime_strategy_*` a `scalping_runtime_config`

**Verifica:** Modificare via DB la strategia per `ranging` e verificare che il selector la usi nella sessione successiva senza restart.

---

### TASK-898 — Analisi Trend basata su dati persistiti (2026-06-29)

**Status:** Pending
**Priorità:** BASSA — dipende da raccolta dati reali
**Dipendenze:** TASK-895 ✅ + almeno 20 trade chiusi con `signal_log_id` popolato e `trend_direction` non null

**Prerequisito:** Verificare con:
```sql
SELECT COUNT(*) FROM scalping_trades t
JOIN session_signal_log sl ON sl.id = t.signal_log_id
WHERE t.status = 'closed' AND sl.trend_direction IS NOT NULL;
```
Se < 20 → non partire.

**Obiettivo:** Verificare se `trend_direction` (converging/diverging/stable) al momento dell'apertura è predittivo dell'outcome.

**Query di analisi:**
```sql
SELECT sl.trend_direction, sl.regime, sl.strategy_type,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(AVG(t.pnl), 4) AS avg_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE sl.decision_type = 'execute' AND t.status = 'closed'
  AND sl.trend_direction IS NOT NULL
GROUP BY sl.trend_direction, sl.regime, sl.strategy_type
HAVING COUNT(t.id) >= 5
ORDER BY sl.trend_direction, sl.regime;
```

**Note:** combinazioni con n_trades < 5 → "campione insufficiente". Incrociare con `tech_signal` per ipotesi direzionali.

**File da creare:** `docs/trend_analysis_report.md`

---

## Task Archiviati

Vedi `docs/ARCHIVE_TASKS.md`
