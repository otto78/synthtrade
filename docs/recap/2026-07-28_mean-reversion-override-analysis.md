# Mean-Reversion Override — Win Rate Analysis per Bucket Bias

**Data:** 2026-07-28
**Autore:** AI Agent (TASK-1232)
**Dipendenze:** TASK-1233 (verifica integrità signal_log_id)

---

## 1. Risultato Generale

| Metrica | Valore |
|---------|--------|
| Trade totali (mean-reversion override BUY) | 12 (1 ancora aperto) |
| Win rate | 25.0% (3/11 chiusi) |
| Avg PnL per trade | -€0.04 |
| PnL totale | -€0.44 |
| Avg intel_score (bias) | -14.6 (tutti bearish) |

**Verdetto:** il pattern "bias bearish → override BUY → stop loss" **regge parzialmente** con i dati disponibili, ma il campione è troppo piccolo per conclusions statisticamente significative.

---

## 2. Win Rate per Bucket di Bias

| Bucket intel_score | Trades | Wins | Win Rate | Avg PnL € | Avg PnL % |
|-------------------|--------|------|----------|-----------|-----------|
| `[-5, -10]` (bearish lieve) | 2 | 0 | **0.0%** | -0.105 | -0.53% |
| `(-10, -15]` (bearish moderato) | 5 | 1 | **20.0%** | -0.063 | -0.32% |
| `(-15, -20]` (bearish forte) | 2 | 1 | **50.0%** | +0.030 | +0.14% |
| `(-20, -∞)` (bearish estremo) | 3 | 1 | **33.3%** | -0.013 | -0.07% |

### Osservazioni

1. **Il bucket peggiore è `[-5, -10]`** (0% win rate) — bias bearish lieve, dove il mercato non è abbastanza sbilanciato da giustificare una mean-reversion.
2. **Il bucket migliore è `(-15, -20]`** (50% win rate, PnL positivo) — bias forte abbastanza da creare condizioni di mean-reversion reali.
3. **`(-20, -∞)`** (estremo) ha 33% win rate — qui il bias è così forte che la mean-reversion potrebbe non verificarsi (il trend è troppo forte).
4. Il pattern suggerisce una **zona ottimale** tra -15 e -20, ma con solo 2 trade non è generalizzabile.

---

## 3. Dettaglio per Sessione

| Sessione | Trades | Wins | Win Rate | PnL Totale | Avg Bias |
|----------|--------|------|----------|------------|----------|
| `e16b2113` (24/07) | 1 | 0 | 0.0% | -€0.21 | -12.2 |
| `94a66daa` (24/07) | 3 | 1 | 33.3% | -€0.04 | -21.8 |
| `4a42133e` (27/07) | 7 | 2 | 28.6% | -€0.19 | -12.0 |
| `2af74bab` (28/07) | 1 | — | (aperto) | — | -13.5 |

### Osservazioni

- **Sessione 94a66daa** ha il bias più forte (-21.8 avg) e il win rate migliore (33.3%), coerente con l'ipotesi che bias estremi favoriscano mean-reversion.
- **Sessione 4a42133e** (la più campionata, 7 trade) ha il win rate più basso (28.6%) — ma qui il bias è moderato (-12.0).
- La sessione 2af74bab (oggi) ha 1 trade ancora aperto — non计入 nel calcolo win rate.

---

## 4. Elenco Completo Trade

| # | Data | Sessione | Entry | Exit | Bias | PnL € | PnL % | Risultato |
|---|------|----------|-------|------|------|-------|-------|-----------|
| 1 | 24/07 09:28 | e16b2113 | 57056.80 | 56567.70 | -12.2 | -0.21 | -1.06% | SL |
| 2 | 24/07 13:31 | 94a66daa | 56538.40 | 56366.80 | -20.6 | -0.10 | -0.50% | SL |
| 3 | 24/07 13:53 | 94a66daa | 56307.00 | 56137.10 | -22.6 | -0.10 | -0.50% | SL |
| 4 | 24/07 14:19 | 94a66daa | 56086.40 | 56649.90 | -22.2 | +0.16 | +0.80% | TP ✓ |
| 5 | 27/07 08:35 | 4a42133e | 57170.40 | 56986.30 | -15.1 | -0.10 | -0.52% | SL |
| 6 | 27/07 12:33 | 4a42133e | 56999.30 | 57576.20 | -12.0 | +0.16 | +0.81% | TP ✓ |
| 7 | 27/07 13:59 | 4a42133e | 57325.80 | 57150.80 | -12.2 | -0.10 | -0.50% | SL |
| 8 | 27/07 14:22 | 4a42133e | 57221.00 | 57046.00 | -8.9 | -0.10 | -0.51% | SL |
| 9 | 27/07 15:19 | 4a42133e | 56809.90 | 56633.76 | -11.3 | -0.10 | -0.51% | SL |
| 10 | 27/07 15:38 | 4a42133e | 56633.90 | 57199.90 | -16.1 | +0.16 | +0.80% | TP ✓ |
| 11 | 27/07 19:46 | 4a42133e | 57099.40 | 56907.36 | -8.6 | -0.11 | -0.54% | SL |
| 12 | 28/07 07:22 | 2af74bab | 55838.70 | — | -13.5 | — | — | Aperto |

---

## 5. Conclusione

### Il pattern regge?

**Parzialmente, ma con caveat importanti:**

1. **Tutti i 12 trade sono BUY** — confermato: il mean-reversion override genera solo long. Il bias bearish crea condizioni di "oversold" che il sistema interpreta come opportunità di acquisto.

2. **Win rate globale basso (25%)** — il bias bearish da solo non è un indicatore sufficiente di mean-reversion riuscita. La maggior parte dei trade si chiude a SL.

3. **Zona ottimale possibile: [-15, -20]** — qui il win rate è 50% (2 trade), ma il campione è minuscolo. Ipotesi: bias estremo ma non troppo estremo favorisce mean-reversion reale.

4. **Bias estremo (-20+) potrebbe essere controproducente** — quando il trend è troppo forte, la mean-reversion non si verifica. Il trade 2 (bias -20.6) e trade 3 (bias -22.6) sono entrambi SL.

5. **Il campione è insufficiente per conclusions definitive.** Servono almeno 50-100 trade per stabilire se la relazione bias→win rate è statisticamente significativa.

### Raccomandazioni

- **Non modificare la soglia dell'override** basandosi su questi dati — il campione è troppo piccolo.
- **Monitorare** le prossime sessioni raccogliendo dati su altri 30-50 trade mean-reversion.
- **Valutare** se introdurre un filtro: mean-reversion override solo se `intel_score` ∈ [-15, -20] (zona potenzialmente ottimale).
- **TASK-1234** (logging conferma esplicita) diventa ancora più importante per raccogliere dati affidabili sulle prossime sessioni.

---

## 6. Note Tecniche

- **Dati:** Supabase `scalping_trades` + `session_signal_log` via SQL JOIN su `signal_log_id`
- **Filtro:** `decision_type = 'mean_reversion_override'` AND `side = 'BUY'`
- **Bucket:** casistiche su `intel_score`: [-5,-10], (-10,-15], (-15,-20], (-20,-∞)
- **Sessioni coinvolte:** 4 (una ancora attiva con 1 trade aperto)
- **Verifica integrità:** TASK-1233 ha confermato che tutti i trade hanno `signal_log_id` non-NULL
