# Trend Analysis Report — TASK-898

> **Data:** 2026-07-16 | **Sample:** 19 trade chiusi con trend data | **Periodo:** sessioni live BNBUSDC + BTC-EUR

---

## Riepilogo

| Metrica | Valore |
|---------|--------|
| Trade chiusi totali | 184 |
| Con `signal_log_id` | 56 |
| Con `trend_direction` non null | **19** |
| Win rate complessivo | 10.5% (2W / 17L) |
| PnL totale | -1.5600 |
| Correlazione trend_value vs PnL | **0.004** (nessuna) |

---

## PnL per trend_direction

| Direction | Trades | Win Rate | Avg PnL | Total PnL |
|-----------|--------|----------|---------|-----------|
| **diverging** | 9 | 22.2% (2W/7L) | -0.0233 | -0.2100 |
| **converging** | 3 | 0.0% (0W/3L) | -0.0633 | -0.1900 |
| **stable** | 7 | 0.0% (0W/7L) | -0.1657 | -1.1600 |

### Osservazioni

1. **DIVERGING ha il miglior PnL medio** (-0.0233) nonostante il nome. Questo perché i trade "diverging" avevano `trend_value` sia negativo (-3.5 a -0.7) sia positivo (13.1, 13.5). I due unici take_profit sono nel gruppo diverging.

2. **STABLE è il peggiore** (-0.1657 avg). Tutti i trade stable avevano `trend_value` vicino a 0.0 (±0.3), indicando mercato piatto — ma tutti erano BUY in condizioni neutre/ribassiste → stop loss.

3. **CONVERGING** (trend_value positivo, score che sale) ha 0% win rate su 3 trade.

4. **Tutti i 19 trade sono BUY** — nessun SELL nel dataset. I trade SELL non hanno `signal_log_id` collegato.

---

## Distribuzione exit reason

| Exit Reason | Count | % |
|-------------|-------|---|
| stop_loss | 16 | 84% |
| take_profit | 2 | 11% |
| session_stop | 1 | 5% |

L'84% dei trade è stato chiuso da stop loss. Questo conferma che il sistema stava prendendo posizioni long in condizioni sfavorevoli.

---

## Regime

Tutti i 19 trade hanno `regime_classified = unknown`. Il regime non era stato classificato al momento dell'entry. Questo indica che la regime detection potrebbe non essere stata attiva o che i trade risalgono a un periodo precedente all'implementazione.

---

## Correlazione trend_value vs PnL

```
Pearson r = 0.004 (p ≈ 0.99)
```

**Nessuna correlazione significativa.** Il `trend_value` da solo non predice l'outcome del trade. Questo è atteso con un sample di 19 trade dove:
- Tutti sono BUY
- Tutti hanno regime "unknown"
- Il 84% è stop loss

---

## Conclusione

### Il problema identificato
Il sistema stava entrando in posizioni LONG durante mercati sfavorevoli. Il 100% dei trade analizzati è BUY, il 84% è stop loss, e il regime era "unknown" in tutti i casi.

### Impact di TASK-906 (Falling Knife Protection)
La guard implementata in `signal_aggregator.py` blocca i mean-reversion BUY quando:
- `trend_direction == "diverging"` (score si allontana da zero)
- `trend_5m < -20.0` (drop di 20+ punti in 5 minuti)

Questo avrebbe bloccato almeno 7 dei 9 trade "diverging" con trend_value negativo (tutti tranne 2 con tv > -20).

### Raccomandazioni

1. **TASK-903 (RegimeDetector isteresi):** Implementare per avere regime classificato su tutti i trade. Attualmente il 100% è "unknown".

2. **TASK-908 (Resume Guard):** Già implementato. Blocca resume in regime bearish senza posizione — avrebbe evitato le re-entrata dopo stop loss.

3. **Raccogliere più dati:** Con 19 trade il sample è troppo piccolo per conclusioni statistiche. Serve almeno 100 trade con trend data per avere potenza statistica.

4. **Monitorare TASK-906 in live:** La guard appena implementata ridurrà significativamente i trade in falling knife. Verificare dopo 50+ trade se il win rate migliora.

---

## Dati grezzi (19 trade)

```
   Direction  TrendVal     PnL  Side  Symbol    Exit
   diverging    -3.50  -0.0500  BUY  BNBUSDC   stop_loss
   diverging    -3.30  +0.1000  BUY  BNBUSDC   take_profit  ← win
   diverging    -2.70  -0.0900  BUY  BNBUSDC   stop_loss
   diverging    -1.60  -0.0500  BUY  BNBUSDC   stop_loss
   diverging    -1.30  -0.0500  BUY  BNBUSDC   stop_loss
   diverging    -1.00  -0.0500  BUY  BNBUSDC   stop_loss
   diverging    -0.70  +0.0800  BUY  BNBUSDC   take_profit  ← win
     stable     -0.30  -0.0600  BUY  BNBUSDC   stop_loss
     stable     -0.10  -0.0900  BUY  BNBUSDC   stop_loss
     stable      0.00  -0.2000  BUY  BTC-EUR   session_stop
     stable      0.00  -0.3400  BUY  BTC-EUR   stop_loss
     stable      0.00  -0.3400  BUY  BTC-EUR   stop_loss
     stable     +0.20  -0.0500  BUY  BNBUSDC   stop_loss
     stable     +0.30  -0.0800  BUY  BNBUSDC   stop_loss
  converging    +1.40  -0.0900  BUY  BNBUSDC   stop_loss
  converging    +1.60  -0.0600  BUY  BNBUSDC   stop_loss
  converging    +2.10  -0.0400  BUY  BNBUSDC   stop_loss
   diverging   +13.10  -0.0500  BUY  BNBUSDC   stop_loss
   diverging   +13.50  -0.0500  BUY  BNBUSDC   stop_loss
```
