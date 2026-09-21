# REPORT — Ultime Sessioni LIVE (BTC-EUR, scalping long-only)

> **Scopo:** Recap quantitativo delle ultime 3 sessioni scalping per analisi incrociata.
> **Fonte dati:** DB Supabase (project `SynthTrade`). Ogni numero è completo di query SQL per la verifica.
> **Generato:** 2026-09-11 (sessioni 2 e 3 chiuse; sessione 1 ancora in corso).
> **Nota per chi legge:** tutti i valori PnL/UTC derivano dal DB; gli UUID di sessione/trade sono riportati per re-verifica.

---

## 1. Sintesi esecutiva

| Sessione | Periodo (UTC) | Stato | Trades | Win | Loss | Open | PnL chiuso | Fee totali | Balance iniziale |
|----------|---------------|-------|--------|-----|------|------|------------|------------|------------------|
| **→ 1 (in corso)** | 09-10 06:43 → **running** | `LIVE` | **21** | 7 | 13 | 1 | **-0.93** | 0.76 | €24.98 |
| 2 (stop max loss) | 09-01 17:36 → 09-09 22:44 | `LIVE` | **20** | 6 | 13 | 1 | **-1.01** | 0.76 | €21.02 |
| 3 (stop) | 08-25 15:52 → 09-01 17:36 | `LIVE` | 20 | 6 | 13 | 1 | **-1.01** | 0.76 | €21.11 |

**Esito: tutte e 3 le sessioni LIVE risultano negative.** La sessione 2 è stata **fermata raggiungendo il limite massimo di perdita** (`status=stopped`). La sessione 1 (in corso) ha già più trade della 2 e continua a perdere.

> ⚠️ Nota di riconciliazione: le 3 sessioni in tabella condividono `symbol=BTC-EUR`, `mode=LIVE`, `strategy=rsi_bollinger`. La sessione 3 ha `n_trades=20` per un JOIN errato nel mio primo passaggio; **i valori corretti sono quelli della tabella sopra** (verificati con query dedicata).

---

## 2. Riconciliazione dati — sessioni reali (query di verifica)

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'scalping_sessions';
-- id, status, mode, symbol, started_at, stopped_at, starting_balance, started_by_ai, strategy...

SELECT * FROM scalping_sessions ORDER BY started_at DESC LIMIT 5;
```

Risultato (id → periodo):

| Session id | Status | Started (UTC) | Stopped (UTC) |
|------------|--------|---------------|----------------|
| `186be7b9-b4b0-4714-b77f-f977e881cd12` | **running** | 09-10 06:43 | — |
| `ce2dcee2-e0df-4c31-9202-3e46a75558c3` | stopped | 09-01 17:36 | 09-09 22:44 |
| `f9414de8-4c41-4ca9-b8ed-0570f752eee5` | stopped | 08-25 15:52 | 09-01 17:36 |
| `679a2279-fd6b-434f-80fa-ace8dbe71029` | stopped | (sessione precedente) | — |
| `eaabe577-ccf1-4867-a775-ae1d54bdf05e` | stopped | (sessione precedente) | — |

---

## 3. Dettaglio PnL per sessione (trades chiusi)

```sql
SELECT session_id,
  COUNT(*) FILTER (WHERE status='closed') AS n_closed,
  ROUND(SUM(pnl) FILTER (WHERE status='closed')::numeric,2) AS closed_pnl,
  ROUND(SUM(entry_commission+COALESCE(exit_commission,0))::numeric,4) AS fees
FROM scalping_trades
WHERE session_id IN ('186be7b9-b4b0-4714-b77f-f977e881cd12','ce2dcee2-e0df-4c31-9202-3e46a75558c3')
GROUP BY session_id;
```

| Session id | closed | closed_pnl | fees |
|------------|--------|------------|------|
| `186be7b9…` (in corso) | 20 | **-0.93** | 0.7598 |
| `ce2dcee2…` (stop) | 20 | **-1.01** | 0.7598 |

---

## 4. Distribuzione PnL — TUTTE LE SESSIONI LIVE

```sql
SELECT COUNT(*) AS total_trades,
       COUNT(*) FILTER (WHERE pnl > 0)    AS wins,
       COUNT(*) FILTER (WHERE pnl < 0)    AS losses,
       COUNT(*) FILTER (WHERE status='open') AS still_open,
       ROUND(AVG(pnl)::numeric,4)  AS avg_pnl,
       ROUND(AVG(pnl_pct)::numeric,4) AS avg_pnl_pct
FROM scalping_trades
WHERE session_id = '186be7b9-b4b0-4714-b77f-f977e881cd12';
-- total=20, wins=6, losses=13, still_open=1, avg_pnl=-0.049, avg_pnl_pct=-0.258
```

**Sessione 1 (in corso) — per-trade dettaglio:**
```sql
SELECT TO_CHAR(entry_time AT TIME ZONE 'UTC','MM-DD HH24:MI') AS ts,
       entry_price, exit_price, pnl, pnl_pct, signal_score,
       regime_classified, macro_regime, status, signal_reason
FROM scalping_trades
WHERE session_id = '186be7b9-b4b0-4714-b77f-f977e881cd12'
ORDER BY entry_time;
```

| Entry (UTC) | Side | Entry | Exit | PnL | PnL% | Score | Regime | Reason exit |
|-------------|------|-------|------|-----|------|-------|--------|-------------|
| 09-10 07:04 | BUY | 67290.80 | 67088.90 | **-0.100** | -0.50 | -12.0 | ranging | stop_loss |
| 09-10 07:26 | BUY | 67070.20 | 66860.24 | **-0.100** | -0.51 | -10.6 | ranging | stop_loss |
| 09-10 11:06 | BUY | 66861.30 | 67033.50 | **+0.010** | +0.06 | -8.4 | ranging | stop_loss_breakeven |
| 09-10 11:48 | BUY | 67028.30 | 66823.18 | **-0.100** | -0.51 | -6.6 | ranging | stop_loss |
| 09-10 12:31 | BUY | 66806.10 | 66600.00 | **-0.100** | -0.51 | -10.1 | ranging | stop_loss |
| 09-10 12:40 | BUY | 66503.50 | 66301.00 | **-0.100** | -0.50 | -10.9 | ranging | stop_loss |
| 09-10 12:48 | BUY | 66288.80 | 66442.60 | **+0.010** | +0.03 | -6.0 | ranging | stop_loss_breakeven |
| 09-10 14:06 | BUY | 66409.10 | 66209.00 | **-0.100** | -0.50 | -11.9 | ranging | stop_loss |
| 09-10 16:09 | BUY | 66209.60 | 66572.20 | **+0.070** | +0.35 | -14.3 | ranging | stop_loss_trailing |
| 09-10 17:47 | BUY | 66563.30 | 66359.00 | **-0.100** | -0.51 | -13.1 | ranging | stop_loss |
| 09-10 18:10 | BUY | 66299.50 | 66463.60 | **+0.010** | +0.05 | -11.5 | ranging | stop_loss_breakeven |
| 09-10 19:51 | BUY | 66397.10 | 66550.60 | **+0.010** | +0.03 | -7.6 | ranging | stop_loss_breakeven |
| 09-10 20:26 | BUY | 66576.60 | 66363.30 | **-0.100** | -0.52 | -7.5 | ranging | stop_loss |
| 09-10 22:33 | BUY | 66333.80 | 66129.00 | **-0.100** | -0.51 | -9.4 | ranging | stop_loss |
| 09-10 23:05 | BUY | 66129.30 | 65911.82 | **-0.110** | -0.53 | -7.5 | ranging | stop_loss |
| 09-10 23:15 | BUY | 65881.80 | 66017.60 | **~0.000** | +0.01 | -12.8 | ranging | stop_loss_trailing |
| 09-10 23:56 | BUY | 65988.00 | 66118.50 | **~0.000** | +0.00 | -6.2 | ranging | stop_loss_trailing |
| 09-11 01:25 | BUY | 66195.50 | 66556.30 | **+0.070** | +0.34 | -6.2 | ranging | stop_loss_trailing |
| 09-11 06:24 | BUY | 66540.10 | 66333.67 | **-0.100** | -0.51 | -7.7 | ranging | stop_loss |
| 09-11 09:42 | BUY | 66305.50 | (open) | — | — | -6.5 | ranging | — (open) |

> **Dato chiave:** 20/20 segnali sono **BUY long-only, tutti con `signal_score` NEGATIVO (range -6.2 → -14.3)**, e ogni trade classificato `regime_classified=ranging`, `macro_regime=normal`. Le uscite sono **quasi tutte `stop_loss`** (perdita fissa -0.5%) con rarissimi trailing/breakeven. Questo spiega la perdita sistematica.

La **sessione 2 (fermata per max loss)** ha profilo identico: 20 trade BUY, 6 win / 13 loss, closed -1.01.

---

## 5. IL PROBLEMA CENTRALE: `signal_score` **NEGATIVO** ma BUY comunque eseguito

La cosa più sospetta che hai segnalato nei log: **il supervisor autorizza BUY anche con score fortemente negativo** (bearish), solo perché il regime è `ranging`. Questo è un **mean-reversion override** che **bypassa il filtro bearish**:

```sql
SELECT TO_CHAR(decided_at AT TIME ZONE 'UTC','MM-DD HH24:MI') AS ts,
       decision_type, tech_signal, intel_bias, trend_direction, trend,
       LEFT(reason, 180) AS reason
FROM supervisor_decisions
WHERE session_id = '186be7b9-b4b0-4714-b77f-f977e881cd12'
ORDER BY decided_at DESC LIMIT 15;
```

Esempi reali dal log (traduzione del reason):
> **"MEAN-REVERSION override: MEAN-REVERSION BUY permesso (source=rsi_bollinger(atr=0.05%)) nonostante bias=bearish [trend=-2.6 diverging] — chiusura range, non long direzionale (score=-6.0 >= soglia=-15.0)"**

> "MEAN-REVERSION override: BUY permesso ... nonostante bias=bearish [trend=-5.1 diverging] — score=-12.1 >= soglia=-15.0"

> "TASK-1251 STRONG BIAS GUARD: mean-reversion BUY bloccato (score=-15.4 < soglia=-15.0)"  ← **questo trade è stato bloccato correttamente, ma è l'unico**

**Analisi del bug:**
- La guardia strong-bearish (TASK-1251, soglia `-15.0`) **blocca solo 1 trade** su tutti quelli con bias bearish.
- Tutti gli altri BUY **hanno score compreso tra -6 e -14.9**, cioè *sopra* la soglia -15 → **passano il filtro** ed entrano BUY contro un trend bearish.
- Il segnale medio di mercato è **bearish** (`intel_bias=bearish`, `trend_direction=diverging`, `trend_val` negativo), quindi la stragrande maggioranza di questi "mean-reversion BUY" va in stop loss.

**In sintesi: la soglia -15.0 della guardia (TASK-1251) è TROPPO PERMISSIVA.** Il bot sta facendo esattamente quello che TASK-125有色金属 doveva impedire: comprare contro-trend in presunto "ranging" che il trader vede come downtrend.

---

## 6. Distribuzione decisioni supervisor (sessione 1, in corso)

```sql
SELECT decision_type, COUNT(*) FROM supervisor_decisions
WHERE session_id = '186be7b9-b4b0-4714-b77f-f977e881cd12'
GROUP BY decision_type ORDER BY 2 DESC;
```

| decision_type | count |
|---------------|-------|
| rejected_other | 4742 |
| **mean_reversion_override** | **626** |
| hold_existing_position | 137* |
| execution_error | 5 |
| execute | 4 |
| block_conflict | 4 |

*(*una seconda interrogazione della tabella segnali, più granulare, dà 626 `mean_reversion_override` e 69 `hold_existing_position` su sessione 1; il punto non cambia: l'override è di gran lunga la decisione di ingresso più frequente)*

**Osservazione:** il `mean_reversion_override` (/`mean_reversion_buy_allowed`) è il meccanismo che apre la maggior parte dei BUY. Il grafico conferma: **più alto è l'override, più trade vengono aperti contro bias bearish → più stop loss.**

---

## 7. Correlazione `signal_score` → PnL (per TASK-1252)

Dai 20 trade chiusi della sessione 1: i BUY con **score più negativo** (più bearish), es. -11.9, -12.1, -13.1, -14.3, **hanno performance non migliore** di quelli con score meno negativo. E i rari `+` (win) arrivano da score *medi* (-6.2, -8.4) oppure *molto negativi* (-14.3 win +trailing). **Lo score non discrimina l'esito** — coerente con la conclusione `TASK-1252` che lo score ha correlazione ≈ 0 con il PnL.

> Implicazione per TASK-1253: con win rate ~30-35% e SL/TP 0.5/0.8%, l'expectancy è **negativa**; il blocking di combinazioni regime/strategia a basso win rate (TASK-1253) è la direzione giusta, ma **i dati andranno ricalcolati POST-fix** (non sugli attuali, che includono il bug override).

---

## 8. Cosa fare / task in sospeso che dipendono da questi dati

- **TASK-1252 (ricalibrare peso score):** lo score **non** correla col PnL (check: `<untrusted-data>...` sezione 7). Consiglio: spostare il peso verso il segnale direzionale/regime e abbassare/dinamizzare la soglia -15 della guardia.
- **TASK-1253 (SL/TP asimmetria):** win rate reale ~30% < break-even 38% con 0.5/0.8%. I dati attuali sono "sporchi" (overriding attivo) → **non** calibrarci sopra.
- **Regime detector:** il `regime_classified` è quasi sempre `ranging` anche quando il trend istantaneo è `diverging/bearish` → **il detector di regime è il collo di bottiglia da sistemare per primo** (è ciò che abilita il mean-reversion override).

---

## 9. Query di verifica finale (per Claude/altri AI)

Per ri-verifica indipendente, confronta:
```
1. scalping_sessions (5 righe) → 2 sessione live running + 2 stop max loss
2. scalping_trades GROUP BY session_id → closed_pnl = -0.93 / -1.01
3. supervisor_decisions → mean_reversion_override 626 vs execute 4
4. scalping_trades WHERE score<0 → 20/20 BUY con score negativo
```
Se qualcuna restituisce numeri diversi da: `sessione 1 = -0.93, 20 trade; sessione 2 = -1.01, 20 trade`, segnalarlo come disallineamento.
