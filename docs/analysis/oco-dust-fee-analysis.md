# OCO, Dust e Fee — Analisi Consolidata

> **Tema trasversale** che emerge da: `docs/recap/2026-06-22_debug-analisi.md`, `docs/recap/2026-06-25_mean-reversion-short.md`, `docs/recap/MASTER_RECAP.md`.
> **Specifica OCO:** `docs/oco-flow-spec.md`.

---

## 1. Problemi risolti

| Problema | Fix | Quando | Stato |
|----------|-----|--------|-------|
| **Fee hardcoded 0.1%** in 6 punti di `router.py` | Sostituite con lettura da `_execution_state["fee_tier"]` | 24-25/06 | ✅ Verificato, nessun residuo |
| **Commissione reale non catturata** da WS | `user_data_stream.py` ora cattura `n`/`N` dal payload | 24-25/06 | ✅ Applicato |
| **`get_trade_fee()` mancante** | Implementato in `exchange.py`, chiamato all'avvio sessione live | 24-25/06 | ✅ Applicato |
| **Target netti TP/SL** | `stop_loss_pct_net`/`take_profit_pct_net` calcolati e broadcast | 24-25/06 | ✅ Applicato |
| **OCO sync falso stop-loss** | Guard su `oco_order_list_id` prima dello sync | 22-23/06 | ✅ Applicato |
| **Dust OCO / quantità disallineate** | Comportamento auto-correttivo accettato come corretto | 22-23/06 | ✅ Chiuso concettualmente |
| **Match "aperto/chiuso" su entry_price** | Match primario via `oco_order_list_id` invece di float | 22-23/06 | ✅ Fix proposto, da verificare |
| **SignalScoreEngine duplicato** | Pattern singleton `get_or_create()` | 22-23/06 | ✅ Applicato |

---

## 2. Problemi da verificare (patch non confermate)

| # | Problema | Patch scritta | Non confermata |
|---|----------|---------------|----------------|
| 1 | `Position.entry_commission` non popolato (TASK-876) | `exchange.py`, `position_manager.py`, `router.py` | ❌ |
| 2 | `get_trade_fee()` fallback silenzioso a 0.001 | Flag `fee_tier_certified: bool` | ❌ |
| 3 | `GET /position` non converte BNB→USDC per `entry_commission_asset` | Conversione nell'endpoint async | ❌ |
| 4 | Verifica end-to-end fee/PnL su trade reale chiuso | Nessuna patch, serve test manuale | ❌ |

---

## 3. Dettaglio tecnico: LOT_SIZE rounding

Il campo "Investito" mostra un valore inferiore al budget configurato (es. 20 USDC → 19.44 USDC). **Non è la fee.** La causa è il LOT_SIZE rounding: la quantità calcolata viene troncata (floor) allo `stepSize` di Binance prima dell'invio dell'ordine.

```
qty_raw = 20 / entry_price      # es. 0.0344...
qty_precise = floor(qty_raw, step_size=0.001)  # es. 0.034
investito_reale = qty_precise * entry_price    # es. 19.44
```

**Suggerimento:** valutare `quoteOrderQty` sugli ordini market per lasciare a Binance il calcolo della qty a precisione massima.

---

## 4. Collegamento con task

| Task | Cosa | Priorità |
|------|------|----------|
| TASK-INVEST-005 | Verificare entry_commission popolato | 🔍 Da Investigare |
| TASK-INVEST-006 | Verificare fee_tier_certified | 🔍 Da Investigare |
| TASK-INVEST-007 | Verificare conversione BNB→USDC in /position | 🔍 Da Investigare |
| TASK-INVEST-009 | Verificare fix insufficient funds minNotional | 🔍 Da Investigare |

---

**Ultima modifica:** 2026-07-02 — Cline