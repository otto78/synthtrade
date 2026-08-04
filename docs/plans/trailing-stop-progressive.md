# TASK-1246 — Trailing Stop Progressivo (Post Break-Even)

> **Stato:** Piano revisionato — pronto per implementazione
> **Data:** 2026-08-04 (v2 — post review)
> **Prerequisito implementato:** TASK-1243 (Stop Loss Breakeven) — in produzione e validato.
> **Reviewer:** agente esterno (see review notes inline)

---

## Contesto e motivazione

Con TASK-1243 abbiamo implementato un singolo amend irreversibile: quando il trade raggiunge
+0.15% netto, lo SL viene alzato a +0.05% netto (break-even). Il trade non può più chiudersi
in perdita.

**Il problema che rimane:** se dopo il break-even il prezzo sale al +0.60% poi inverte, lasciamo
sul tavolo profitto già acquisito. Il trailing stop serve a proteggere progressivamente i guadagni
senza uscire troppo presto.

---

## Parametri configurabili (via `scalping_runtime_config`)

```yaml
# Step 0 — già esistente (TASK-1243), invariato
break_even_enabled: true
break_even_trigger_net_pct: 0.15
break_even_lock_net_pct: 0.05

# Trailing progressivo — nuovo
trailing_enabled: false             # feature flag off by default
trailing_step_net_pct: 0.15        # ogni quanto si avanza (default alzato da 0.10 a 0.15 — vedi sezione step size)
trailing_buffer_net_pct: 0.10      # distanza SL dal trigger corrente
trailing_safety_margin_net_pct: 0.10  # distanza minima da mantenere tra next_trigger e TP netto
```

> **Nota v2:** `trailing_max_steps` rimosso. Il cap è ora dinamico: un nuovo step è eleggibile
> solo se `next_trigger_net < tp_net_pct - trailing_safety_margin_net_pct`.
> Questo si adatta automaticamente se il Supervisor cambia il TP netto a runtime,
> ed è immune alla race condition SL > TP già vista in TASK-1127 (sCode 51280).

---

## Logica degli step — tabella corretta

Calcolata con `_exit_price_ratio()` su entry=55154.60, fee taker 0.10%+0.10%.
Formula: `prezzo = entry × (1 + net_pct/100) / ((1 - 0.001) × (1 - 0.001))`

| Step | Trigger netto | SL netto | Prezzo trigger (lordo) | Prezzo SL (lordo) |
|------|--------------|----------|------------------------|-------------------|
| 0 (BE) | +0.15% | +0.05% | ~55348 (+0.35%) | ~55292 (+0.25%) |
| 1 | +0.30% | +0.20% | ~55403 (+0.45%) | ~55348 (+0.35%) |
| 2 | +0.45% | +0.35% | ~55458 (+0.55%) | ~55403 (+0.45%) |
| 3 | +0.60% | +0.50% | ~55513 (+0.65%) | ~55458 (+0.55%) |
| TP netto | +0.80% | — | ~55824 (+1.00%) | — |

> **Correzione v2:** la tabella precedente aveva errori sistematici (~28 EUR per step).
> I prezzi corretti sono stati verificati contro il dato live di TASK-1243
> (newSL=55292.70 confermato su OKX). Usare sempre `_exit_price_ratio()` per
> qualsiasi calcolo manuale, mai sottrazioni approssimate.

---

## Scelta dello step size: 0.15% invece di 0.10%

Il reviewer ha evidenziato che con step da 0.10% (≈55 EUR su BTC a 55k), un movimento
di rumore su candele 1m può far scattare il trailing e poi staccare la posizione prima
del TP. Il trade live di TASK-1243 (90 minuti, +0.19% netto al trigger) lo conferma.

**Prima di buildare:** eseguire questa query sui trade `take_profit` storici per misurare
quanto spesso il prezzo, dopo aver toccato +0.25% netto, è rientrato di 0.10% prima
di arrivare al TP:

```sql
-- Approssimazione: trade TP con entry/exit disponibili, esclude sessioni pre-calibrazione
SELECT
  COUNT(*) as total_tp,
  AVG((exit_price - entry_price) / entry_price * 100) as avg_gross_pct,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY (exit_price - entry_price) / entry_price * 100) as p25_gross_pct
FROM scalping_trades
WHERE signal_reason = 'take_profit'
  AND side = 'BUY'
  AND status = 'closed'
  AND entry_price > 0
  AND exit_price > 0;
```

Se il p25 del gross pct sui TP è < 0.45%, alzare lo step a 0.20% o rivalutare ATR-based.
**Default conservativo per la v1: 0.15%.**

---

## Regola invariante di avanzamento

```
next_trigger_net = break_even_trigger_net_pct + (trailing_step + 1) × trailing_step_net_pct

Step eleggibile se:
  1. net_pct >= next_trigger_net                          (prezzo ha raggiunto il trigger)
  2. next_trigger_net < tp_net_pct - safety_margin        (almeno safety_margin sotto il TP)
  3. new_sl_net > trailing_last_sl_net_pct                (mai peggiorare lo SL)
  4. new_sl_price > float(pos.sl_price)                   (guard su prezzo assoluto)
```

---

## Restore: prezzo reale, non step count

**Problema identificato in review:** se `trailing_step_net_pct` cambia a runtime tra un
restart e l'altro, ricostruire il prezzo SL da `step_count × step_size` dà un valore
diverso da quello realmente confermato su OKX.

**Soluzione:** il campo `trailing_last_sl_price` (già in schema) è la fonte di verità.
Al restore:
- `pos.sl_price` = `trailing_last_sl_price` dal DB (già fatto da TASK-1243 per `sl_price`)
- Il guard "nuovo SL > SL attuale" usa sempre `float(pos.sl_price)`, indipendentemente
  da come è stato calcolato

`trailing_step` è usato **solo per telemetria e UI** (mostrare "Step 2" nel frontend).
Non partecipa a nessun calcolo di prezzo al restore.

---

## Gate obbligatorio pre-implementazione: spike rate limit

Il progetto ha sempre eseguito uno spike isolato prima di costruire su endpoint OKX nuovi
(demo spike OCO, spike short, spike amend TASK-1243). Questo è mancante per chiamate
ripetute su `amend-algos`.

**Script da scrivere:** `scripts/test_okx_amend_rate.py`
- Apre una posizione minima su OKX Demo con OCO
- Invia 6 amend consecutivi con intervallo 10-20s tra l'uno e l'altro
- Verifica: nessun HTTP 429, nessun sCode di rate limit, algoId invariato a ogni step

Solo dopo esito verde di questo spike si procede con l'implementazione.

---

## Cosa cambia rispetto a TASK-1243

### Dati aggiuntivi su `Position` (in memory)

```python
trailing_step: int = 0                  # numero step applicati (solo UI/telemetria)
# trailing_last_sl_price non serve come campo separato:
# pos.sl_price è già aggiornato dopo ogni amend confermato
```

### Migration DB

```sql
ALTER TABLE scalping_trades
  ADD COLUMN trailing_step int NOT NULL DEFAULT 0;
-- trailing_last_sl_price non serve: sl_price è già la fonte di verità
```

### config_loader.py

```python
"TRAILING_ENABLED": False,
"TRAILING_STEP_NET_PCT": 0.15,
"TRAILING_BUFFER_NET_PCT": 0.10,
"TRAILING_SAFETY_MARGIN_NET_PCT": 0.10,
```

### break_even.py — estensione post-BE

```python
async def _check_and_apply_trailing(pos, current_price, session):
    """Chiamata su ogni candela chiusa, solo se break_even_triggered==True."""
    if not pos.break_even_triggered:
        return
    if not cfg.get("TRAILING_ENABLED"):
        return

    step = pos.trailing_step
    trigger_net = be_trigger + (step + 1) * step_net
    tp_net = cfg.get("TAKE_PROFIT_NET_PCT", 0.80)  # dal risk_config

    # Guard dinamico: non superare TP - safety_margin
    if trigger_net >= tp_net - safety_margin:
        return

    net_pct = _expected_net_pct_at_exit(entry, current_price, side, ef, xf)
    if net_pct < trigger_net:
        return

    new_sl_net = trigger_net - buffer_net
    new_sl_price = quantized price for new_sl_net

    # Guard: mai peggiorare lo SL (confronto su prezzo assoluto)
    if new_sl_price <= float(pos.sl_price):
        return

    # amend → conferma OKX → aggiorna pos.sl_price, pos.trailing_step += 1
    # broadcast: tipo "trailing_stop_updated", payload include step number
```

### Evento WS

- `trailing_stop_activated` — step 0 (break-even, già implementato)
- `trailing_stop_updated` — step 1+ (nuovo)
  - payload: `{ step, old_sl, new_sl, trigger_net_pct, current_net_pct }`

### Frontend

- Banner: "🔒 STOP LOSS BREAKEVEN ATTIVO" (step 0) / "🔒 TRAILING STOP — Step N" (step 1+)
- La barra usa sempre `pos.stop_loss_price` dal payload `position_update` — già corretto
  perché il backend aggiorna `pos.sl_price` dopo ogni amend confermato e lo include nel broadcast.
  **Da verificare esplicitamente nei test frontend:** che dopo il secondo amend la barra si sposti.
- `formatReason`: aggiungere `stop_loss_trailing` per trade chiusi da trailing step 1+

---

## Piano di implementazione (ordinato)

1. **Query storica** — validare step size 0.15% sui trade storici (query sopra)
2. **Spike rate limit** — `scripts/test_okx_amend_rate.py` su OKX Demo
3. **Migration DB** — `trailing_step int default 0` su `scalping_trades`
4. **Position dataclass** — `trailing_step: int = 0`
5. **config_loader.py** — 4 chiavi `TRAILING_*`
6. **break_even.py** — `_check_and_apply_trailing()` + chiamata in `candle_processor.py`
7. **db_ops.py** — estendere `_update_break_even_in_db` o nuovo `_update_trailing_in_db`
8. **main.py restore** — ripristinare `trailing_step` dal DB
9. **Frontend** — banner step-aware, `trailing_stop_updated` WS, `formatReason`
10. **Test** — estendere `test_task_1243.py` con casi trailing
11. **Validazione** — ≥20 trade paper con `trailing_enabled=true` prima del live

---

## Criteri di accettazione

1. Ogni step è idempotente: un restart non reinvia amend già confermati.
2. Il guard dinamico `next_trigger < tp_net - safety_margin` impedisce SL > TP in qualsiasi configurazione, anche con TP modificato dal Supervisor a runtime.
3. Il restore usa `sl_price` dal DB come fonte di verità, non ricostruisce da `trailing_step × step_size`.
4. In caso di errore OKX su uno step, lo stato locale non cambia e il retry è alla candela successiva.
5. `trailing_enabled=false` disabilita il trailing senza toccare il break-even.
6. Il frontend mostra il numero di step corrente nel banner e la barra riflette lo SL reale aggiornato.
7. Lo spike rate limit è verde prima di qualsiasi attivazione live.

---

## Fuori scope (v1)

- Trailing tick-by-tick intra-candle
- ATR-based trailing (v2 se i dati storici lo giustificano)
- Trailing su posizioni short
