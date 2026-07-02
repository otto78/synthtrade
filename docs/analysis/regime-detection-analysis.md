# Regime Detection — Analisi Consolidata

> **Tema trasversale** che emerge da: `docs/recap/2026-06-20_risk-controls-audit.md`, `docs/recap/2026-06-22_debug-analisi.md`, `docs/recap/2026-06-25_mean-reversion-short.md`, `docs/recap/2026-06-27_strategie-scalping.md` (eliminato, contenuto in MASTER_RECAP).
> **Consolidato in:** `docs/recap/MASTER_RECAP.md` §3 (bug #11, #12, #13) e §4.

---

## 1. Il problema

Il RegimeDetector classifica il mercato in `ranging`/`trending_up`/`trending_down`. Le soglie ATR/price_change sono statiche, causando:

1. **Misclassificazione**: breakdown con volume spike vengono classificati come `ranging` invece di `trending_down` — root cause di:
   - Falling Knife Protection (bug #12)
   - Mean-reversion contro-trend che apre BUY in piena discesa (bug #11)
   - Supervisor che riceve contesti contraddittori
   - Dati storici per regime inquinati

2. **Flickering**: il regime cambia ad ogni candela se le soglie oscillano vicino ai boundary.

---

## 2. Evidenze dalle sessioni

| Data | Evidenza | Impatto |
|------|----------|---------|
| 20/06 | Regime `ranging` accettato mentre il prezzo scendeva verticalmente | 4 stop_loss consecutivi |
| 22-23/06 | `trend_direction` classificato `stable` anche con variazioni +0.3/+0.4 in pochi minuti | Soglia di sensibilità troppo larga |
| 25/06 | 4° stop_loss: regime `ranging`, ma era un breakdown con volume confermato | Mean-reversion BUY contro trend |
| 27-28/06 | Supervisor assegnava `ema_cross` in regime `ranging` (fixato con whitelist) | Sintomo, non causa |

---

## 3. Fix parziali già applicati

| Fix | Quando | File |
|-----|--------|------|
| Whitelist regime→strategia | 27-28/06 | `supervisor_scheduler.py`, `supervisor_client.py` |
| Trend tracking Intelligence Score (log-only) | 22-23/06 | `SignalScoreEngine` con `trend_5m`, `velocity`, `trend_direction` |
| Soglie RSI/BB abbassate | 27-28/06 | `rsi_bollinger.py` |
| Soglia `tradeable` dinamica | 27-28/06 | `signal_score_engine.py` |

---

## 4. Proposte non implementate

### 4.1 Isteresi K candele (TASK-903)
Aggiungere `_pending_regime` + `_pending_count` in `regime_detector.py`. Il regime "committed" cambia solo dopo K candele consecutive dello stesso candidato (default K=3). Se il candidato cambia prima → reset counter.

**Stato:** Pending in TASKS.md

### 4.2 Volume confirmation per breakout
Proposto come flag nel futuro `MarketStructureCollector`:
- Rottura con volume >1.5-2x media recente → breakout reale
- Avvicinamento senza volume anomalo → probabile test/rimbalzo
- Dati OHLCV già disponibili (nessuna nuova fonte dati)

**Stato:** Solo proposta (MASTER_RECAP §4.3)

### 4.3 MarketStructureCollector (supporti/resistenze)
Nuovo collector che deriva livelli da swing high/low, clusterizza livelli vicini pesati per numero di "touch". Uso: evitare entry contro resistenza forte, piazzare SL oltre livello strutturale invece che a % fissa.

**Stato:** Solo proposta (MASTER_RECAP §4.3)

### 4.4 Falling Knife Protection
Bloccare mean-reversion BUY durante crolli verticali usando `trend_direction == "diverging"` combinato con velocità (`trend_5m <= -X`). Soglia da validare con dati reali (atteso prossimo episodio con trend-logging attivo nel ramo mean-reversion).

**Stato:** TASK-906 Pending (in attesa dati reali)

---

## 5. Collegamento con task

| Task | Cosa | Priorità |
|------|------|----------|
| TASK-903 | Isteresi K candele | 🟡 Media |
| TASK-906 | Falling Knife Protection | 🔴 Alta (attesa dati) |
| TASK-INVEST-011 | Verificare regime misclassification su log live | 🔍 Da Investigare |
| TASK-INVEST-013 | Verificare sensibilità trend_direction | 🔍 Da Investigare |

---

**Ultima modifica:** 2026-07-02 — Cline