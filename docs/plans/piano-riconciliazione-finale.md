# Riconciliazione posizione — stato reale e gap residuo

> Sostituisce i documenti precedenti. Dopo lettura diretta di `router.py`, la funzione
> `_reconcile_position_with_exchange()` esiste già ed è correttamente agganciata quasi
> ovunque. Resta un solo gap concreto, individuato e descritto sotto.

## 1. Flusso di riconciliazione — architettura attuale (già implementata, corretta)

`_reconcile_position_with_exchange(symbol, pos_side, entry_price, quantity, exchange, bracket_id)`

Priorità di ricerca del dato, in ordine:

1. **Holdings/balance check**: se `total_bal >= min_qty` → posizione ancora aperta, return None
   (nessuna azione). Se `< min_qty` → posizione chiusa esternamente, si procede sotto.
2. **Algo history via `bracket_id`** (priorità 1a): cerca l'algoId esatto in
   `get_algo_orders_history()`, stato `"effective"` → fill_price da `avgPx`/`fillPx`,
   reason da `ordType` (tp/sl), `source="fills"`. **Questo è esattamente il meccanismo
   proposto: un solo ordine, deterministico, nessuna ambiguità.**
3. **Match per exit side** (priorità 1b, fallback se 1a non trova nulla): cerca nello stesso
   storico algo un fill con side opposto all'apertura — copre chiusure non associate
   all'algoId originale (es. emergency market close).
4. **Entry price fallback** (ultima istanza): solo se nessuna delle due sopra produce un
   prezzo valido, con log esplicito `PnL will be inaccurate!`.
5. **Retry automatico**: se il balance check stesso fallisce (es. rete instabile durante
   lo startup), c'è già un retry a 3 tentativi con `sleep(1.5s)` tra un tentativo e l'altro
   sulla ricerca in algo history, prima di arrendersi.

Punti di innesco già agganciati:

- **Startup / restore_mode** (`_start_ws_broadcast`, blocco `FIX-2026-07-16`): reconcile
  eseguito dopo che il WS è connesso, con calcolo PnL reale, update DB, broadcast
  `position_reconciled_externally`.
- **`_on_uds_reconnect_sync`**: reconcile ad ogni riconnessione dello User Data Stream
  (ordini), stesso schema completo (PnL, DB, broadcast).
- **`_live_close_position` Scenario 1**: se il balance è già sotto `min_qty` al momento di
  un tentativo di chiusura manuale, usa lo stesso helper invece di ticker/entry_price.

**Conclusione:** l'impianto "algoId come fonte di verità primaria, poi fallback per side,
poi entry_price come ultima istanza" — cioè esattamente la logica discussa — è già
implementato e corretto. Non serve riscriverlo.

## 2. Il gap reale: gate `status == "running"` nel restart del watchdog

Il watchdog delle candele (dentro `_candle_processor`, funzione interna `_full_restart`,
innescata quando non arrivano candele da >180s — tipicamente dopo sleep/standby del PC)
esegue:

```python
if _execution_state["session"]["status"] == "running":
    await _start_ws_broadcast(symbol, restore_mode=True)
```

Tutta la logica di reconcile allo startup vive **dentro** `_start_ws_broadcast` in
`restore_mode=True`. Se la sessione era in stato `"paused"` nel momento in cui il PC va
in sleep (evento comune: il supervisor AI mette in pausa molto spesso), questo blocco non
scatta affatto. Risultato osservato in produzione:

- WS fermato e task cancellati (`RESTART_WS: Stopping old client... / Cancelling old
  tasks...`)
- ma **mai ricreato**, perché `_start_ws_broadcast` non viene richiamato
- nessun reconcile eseguito
- health check fallisce per 40+ minuti (`ws_connected`, `tasks_alive` sempre False)
- l'unica via d'uscita osservata è stata il riavvio manuale completo dell'app, che passa
  dal path di startup (quello sì, sempre eseguito)

## 3. Fix

**File:** `router.py`, dentro `_candle_processor` → `_full_restart()`.

```python
# Prima
if _execution_state["session"]["status"] == "running":
    await _start_ws_broadcast(symbol, restore_mode=True)

# Dopo
if _execution_state["session"]["status"] in ("running", "paused"):
    await _start_ws_broadcast(symbol, restore_mode=True)
```

**Perché è sicuro e sufficiente:**

- `_candle_processor` già filtra a valle con `if status != "running": SKIP` prima di
  processare qualunque segnale — quindi permettere il restart anche in pausa non riattiva
  il trading, riattiva solo WS/pipeline/reconcile.
- Se lo stato è `"idle"` (sessione davvero fermata dall'utente), il restart resta
  correttamente escluso: non è nella tupla.
- Non serve nessun nuovo helper, nessun nuovo trigger point, nessuna nuova colonna DB:
  l'unico problema era che il meccanismo esistente restava spento nel caso più comune
  (pausa + sleep del PC).

## 4. Cosa NON serve più (rispetto ai piani precedenti)

- ❌ Nuovo step "fills_history su range di sessione" — già coperto dal match per exit
  side su algo history (punto 1b sopra), sufficiente per il caso emergency market close.
- ❌ Campo `pnl_reliable` — non presente nel codice attuale; può restare un nice-to-have
  futuro ma non è necessario per chiudere il bug reale di ieri notte.
- ❌ Nuovo job periodico indipendente — il watchdog di staleness candele (>180s) già
  funge da rete di sicurezza periodica; il problema era solo il gate che lo disattivava
  in pausa.
- ❌ Riscrittura dell'helper di reconcile — è già corretto e ben strutturato.

## 5. Verifica dopo il fix

1. Simulare lo scenario esatto: sessione in `"paused"`, sospendere la rete/il PC per
   >3 minuti, poi ripristinare — verificare che `_full_restart` venga eseguito anche con
   `status="paused"` (log atteso: `RESTART_WS: Calling _start_ws_broadcast
   (restore_mode=True)...`).
2. Se nel frattempo una posizione aperta è stata chiusa da TP/SL su OKX, verificare che il
   reconcile in `restore_mode` la rilevi correttamente (log atteso: `source=fills` con
   `reason=take_profit` o `stop_loss`, non `entry_price_fallback` salvo casi patologici).
3. Verificare che l'health check torni `ws_connected=True`, `tasks_alive=True` entro pochi
   secondi dal restart, invece di restare in fallimento per decine di minuti.
