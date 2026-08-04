# TASK-1246 — Trailing Stop Progressivo (Post Break-Even)

> **Stato:** Proposta di design — da revisionare
> **Data:** 2026-08-04
> **Prerequisito implementato:** TASK-1243 (Stop Loss Breakeven) — già in produzione e validato.

---

## Contesto e motivazione

Con TASK-1243 abbiamo implementato un singolo amend irreversibile: quando il trade raggiunge +0.15% netto, lo SL viene alzato a +0.05% netto (break-even). Il trade non può più chiudersi in perdita.

**Il problema che rimane:** se dopo il break-even il prezzo sale al +0.40%, poi inverte e tocca lo SL a +0.05%, lasciamo sul tavolo 0.35 punti percentuali di profitto che potevamo catturare. Il trailing stop serve esattamente a questo: proteggere progressivamente i guadagni già acquisiti senza uscire troppo presto.

**L'obiettivo non è massimizzare il profitto per trade, è minimizzare il profitto sprecato su trade vincenti.**

---

## Architettura proposta

### Estensione del modello break-even esistente

TASK-1243 ha già costruito tutta l'infrastruttura:
- `break_even.py` — modulo trigger/amend
- `amend_exit_bracket_stop_loss()` — chiamata OKX firmata
- `_update_break_even_in_db()` — persistenza per algoId
- Campi `break_even_triggered/activated_at/sl_price` su `scalping_trades`
- Restore al riavvio

Il trailing stop è un'**estensione** di questo modulo, non una riscrittura. Riusa gli stessi metodi, aggiunge una logica di step multipli.

---

## Logica degli step proposta

### Struttura a livelli netti (fee 0.10%+0.10% già incluse)

| Step | Trigger netto | Nuovo SL netto | Delta guadagno protetto |
|------|--------------|----------------|-------------------------|
| 0 (BE) | +0.15% | +0.05% | break-even già implementato |
| 1 | +0.25% | +0.15% | +0.10% protetti |
| 2 | +0.35% | +0.25% | +0.20% protetti |
| 3 | +0.45% | +0.35% | +0.30% protetti |
| 4 | +0.55% | +0.45% | +0.40% protetti |
| ... | ogni +0.10% | SL = trigger - 0.10% | sempre 0.10% di buffer |

**Regola invariante:** `nuovo_SL = trigger_corrente - step_buffer`
dove `step_buffer` è configurabile (default: 0.10% netto).

### Parametri configurabili (via `scalping_runtime_config`)

```yaml
# Step 0 — già esistente (TASK-1243)
break_even_enabled: true
break_even_trigger_net_pct: 0.15
break_even_lock_net_pct: 0.05

# Trailing progressivo — nuovo
trailing_enabled: false           # feature flag off by default
trailing_step_net_pct: 0.10      # ogni quanto si avanza (trigger step)
trailing_buffer_net_pct: 0.10    # distanza SL dal trigger (protezione inversione)
trailing_max_steps: 10           # cap di sicurezza (evita loop infiniti)
```

### Esempio concreto con BTC-EUR, entry 55154.60

```
entry:           55154.60
fee round-trip:  +0.2003% lordo = 0% netto

Step 0 (BE):    trigger @55348 (+0.35% lordo, +0.15% netto) → SL → 55265 (+0.25% lordo, +0.05% netto)
Step 1:         trigger @55403 (+0.45% lordo, +0.25% netto) → SL → 55320 (+0.35% lordo, +0.15% netto)
Step 2:         trigger @55458 (+0.55% lordo, +0.35% netto) → SL → 55375 (+0.45% lordo, +0.25% netto)
Step 3:         trigger @55513 (+0.65% lordo, +0.45% netto) → SL → 55430 (+0.55% lordo, +0.35% netto)
TP originale:   55824 (+1.20% lordo, +0.80% netto) — invariato
```

Ogni step = un `amend_exit_bracket_stop_loss()` separato verso OKX.

---

## Cosa cambia rispetto a TASK-1243

### Dati aggiuntivi su `Position` (in memory)

```python
trailing_step: int = 0                    # quanti step sono stati applicati
trailing_last_sl_net_pct: float = 0.05    # ultimo SL netto impostato (inizia dal BE lock)
```

### Dati aggiuntivi su `scalping_trades` (DB)

```sql
ALTER TABLE scalping_trades
  ADD COLUMN trailing_step int NOT NULL DEFAULT 0,
  ADD COLUMN trailing_last_sl_price numeric NULL;
```

### Logica in `break_even.py`

La funzione `_check_and_apply_break_even` viene estesa (o affiancata da `_check_and_apply_trailing`) con questa logica:

```
Se break_even_triggered == False → esegui logica BE (già esistente, invariata)
Se break_even_triggered == True AND trailing_enabled == True:
    next_trigger = break_even_trigger_net_pct + (trailing_step + 1) * trailing_step_net_pct
    Se net_pct >= next_trigger AND trailing_step < trailing_max_steps:
        new_sl = next_trigger - trailing_buffer_net_pct
        Se new_sl > trailing_last_sl_net_pct:  (mai peggiorare lo SL)
            amend OKX → aggiorna DB → trailing_step += 1
```

---

## Sequenza sicura (identica a TASK-1243)

1. Solo posizione OPEN, live, con `oco_order_list_id`, su **candela chiusa**.
2. Calcola `net_pct` con `_expected_net_pct_at_exit()`.
3. Verifica che il nuovo SL sia strettamente > SL attuale.
4. Acquisisce lock async per algoId.
5. Invia amend. Successo solo con `code=="0"` AND `sCode=="0"`.
6. Solo dopo conferma OKX: aggiorna memoria e DB.
7. Broadcast WS `trailing_stop_updated`.

---

## Considerazioni critiche da valutare

### Pro
- **Nessun nuovo rischio di posizione scoperta.** Ogni step è un amend dello stesso OCO — stessa garanzia di TASK-1243.
- **Completamente reversibile.** `trailing_enabled=false` disabilita tutto senza toccare il codice BE.
- **Costo zero aggiuntivo** in termini di fee (nessun ordine nuovo, solo amend).
- **Compatibile con multi-sessione futura.** L'identità è sempre l'algoId esatto.

### Contro / Rischi da pesare
- **Rate limit OKX amend-algos.** Ogni step = una chiamata REST firmata. Su candele da 1 minuto e step ogni 0.10%, in un movimento violento si potrebbero inviare 5-6 amend in pochi minuti. Da verificare se OKX ha limiti su `amend-algos` in sequenza ravvicinata.
- **Slippage amplificato.** Più è alto lo SL, più è probabile che un'inversione rapida esegua tra trigger e fill. Il buffer di 0.10% è conservativo ma va calibrato sulla volatilità reale di BTC-EUR.
- **Step troppo fitti = uscite premature.** Con 0.10% di step su BTC a 55k, ogni step vale ~55 EUR di movimento. Nel noise normale di una candela 1m, il trailing potrebbe staccare presto. Valutare step_net_pct=0.15% o 0.20% come alternativa.
- **Restore al riavvio.** `trailing_step` deve essere ripristinato dal DB esattamente come `break_even_triggered`, altrimenti al restart il trailing riparte da 0 e invia amend già inviati.

---

## Domande aperte prima dell'implementazione

1. **Step fisso o ATR-based?** Lo step di 0.10% fisso è semplice da implementare. Un buffer basato sull'ATR della candela corrente sarebbe più intelligente (si adatta alla volatilità) ma richiede più logica.

2. **Cap al TP o prima?** Conviene fermare il trailing quando lo SL supera l'80% del range verso il TP, per non rischiare di portare lo SL sopra il TP stesso (impossibile su OKX, ma da gestire via guard nel codice).

3. **Solo post-BE o anche indipendente?** La proposta attuale prevede il trailing solo *dopo* che il BE è stato attivato. Un'alternativa è usare il trailing *invece* del BE fisso — ma questo complica la logica e rimuove la semplicità del "singolo step irreversibile".

4. **Notifica diversa nel WS?** Il frontend deve distinguere `trailing_stop_activated` (primo step = BE) da `trailing_stop_updated` (step successivi). Il banner dovrebbe mostrare lo step corrente?

---

## Piano di implementazione (se approvato)

### Step 1 — Migration DB
```sql
ALTER TABLE scalping_trades
  ADD COLUMN trailing_step int NOT NULL DEFAULT 0,
  ADD COLUMN trailing_last_sl_price numeric NULL;
```

### Step 2 — Position dataclass
Aggiungere `trailing_step: int = 0` e `trailing_last_sl_net_pct: float = 0.0`.

### Step 3 — config_loader.py
Aggiungere `TRAILING_ENABLED=false`, `TRAILING_STEP_NET_PCT=0.10`, `TRAILING_BUFFER_NET_PCT=0.10`, `TRAILING_MAX_STEPS=10`.

### Step 4 — break_even.py
Estendere `_check_and_apply_break_even()` con il loop trailing post-BE. Alternativa: nuovo `_check_and_apply_trailing()` separato chiamato in sequenza.

### Step 5 — db_ops.py
Estendere `_update_break_even_in_db()` o aggiungere `_update_trailing_in_db()`.

### Step 6 — main.py restore
Ripristinare `trailing_step` e `trailing_last_sl_net_pct` dal DB.

### Step 7 — Frontend
Aggiornare `position-ticker`: mostrare step corrente nel banner (es. "TRAILING STOP — Step 2").
Aggiornare `formatReason`: aggiungere `stop_loss_trailing` per i trade chiusi da trailing.

### Step 8 — Test
Estendere `tests/test_task_1243.py` con casi trailing:
- Step 1 scatta quando netto >= trigger_1
- Step 2 non scatta se step 1 non è ancora avvenuto
- Nessun amend se SL nuovo <= SL attuale
- Cap a trailing_max_steps rispettato
- Restore: trailing_step=2 dal DB non reinvia step 1 e 2

### Step 9 — Validazione
Almeno 20 trade con `trailing_enabled=true` in paper prima del live.
Monitorare: numero medio di amend per trade, tasso di uscita per trailing vs TP naturale.

---

## Criteri di accettazione

1. Ogni step è idempotente: un restart non reinvia amend già confermati.
2. Il TP originale resta invariato dopo ogni amend.
3. Il nuovo SL è sempre strettamente > SL precedente.
4. In caso di errore OKX su uno step, lo stato locale non cambia e il retry avviene alla candela successiva.
5. `trailing_enabled=false` disabilita il trailing senza toccare il break-even.
6. Il frontend mostra lo step corrente e il motivo di chiusura (`Stop Loss Trailing`).

---

## Fuori scope

- Trailing tick-by-tick intra-candle (richiede WS dedicato + rate limiting separato).
- ATR-based trailing (v2 eventuale).
- Trailing su posizioni short (simmetrico ma fuori scope fino a implementazione short selling).
