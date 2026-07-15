# Fix Riconciliazione Posizione

## Problema
- **Step 6** (main.py:140-198) ripristina la posizione in memoria leggendo solo dal DB, senza controllare l'exchange → imposta `has_open_position = True`
- **Step 7** (main.py:277-416) ha la logica corretta di verifica exchange ma è bloccata da `if not has_open_position:` → mai eseguita
- **`_live_close_position` Scenario 1** (router.py:548-563) usa solo ticker price, non chiama `get_algo_orders_history()`
- **`_on_uds_reconnect_sync`** (router.py:929-968) ha logica inline duplicata con PnL sempre a 0

## Soluzione

### 1. Nuovo helper `_reconcile_position_with_exchange()` in router.py

**Posizione:** dopo `_get_fee_rate` (riga 67), prima di `logger = ...` (riga 69).

```python
async def _reconcile_position_with_exchange(
    symbol: str,
    pos_side: str,
    entry_price: float,
    quantity: float,
    *,
    exchange=None,
    bracket_id: str | None = None,
) -> Optional[Dict[str, Any]]:
```

**Logica:**
1. Ottieni exchange da param o `_execution_state["exchange"]`. Se None → return None
2. Parsing symbol → SymbolRef, get `min_qty` da `get_symbol_rules()`
3. `total_bal = await exchange.get_balance(sym_ref.base)`
4. Se `total_bal >= min_qty` → posizione ancora aperta → log `[POSITION_RECONCILE] still open` → return None
5. Se `total_bal < min_qty` → posizione chiusa esternamente:
   - **a.** Se `bracket_id` → `get_algo_orders_history(symbol)`, cerca fill con `algoId == bracket_id` e `state == "effective"`. Se trovato: `fill_price = avgPx/fillPx`, reason da `ordType` ("tp"→take_profit, "sl"→stop_loss), source="algo_history"
   - **b.** Se non trovato → `get_ticker_price()`, source="ticker", reason da confronto fill vs entry
   - **c.** Se ticker fallisce → `entry_price`, source="entry_price_fallback", reason="external_close_unknown_price"
6. Log esplicito `[POSITION_RECONCILE] closed | fill=X source=Y reason=Z`
7. Return dict con `fill_price`, `source`, `reason`

### 2. Modifiche a main.py Step 6 (righe 173-195)

Sostituire il blocco `pm.open_position()` con:
- Import: `from app.scalping.router import _reconcile_position_with_exchange, broadcast_scalping_event, _get_fee_rate`
- Prima di `pm.open_position()`, chiamare `_reconcile_position_with_exchange()`
- Se ritorna dict → calcola PnL con `_get_fee_rate()`, aggiorna DB a `status='closed'`, broadcast `position_reconciled_externally`, `has_open_position` resta False
- Se ritorna None → restore normale con `pm.open_position()` (codice esistente)

### 3. Eliminare Step 7 (righe 277-416)

Tutto il blocco `if not has_open_position:` diventa dead code → eliminare. Mantenere solo `guard.complete_phase("position_phase")` alla riga 418.

### 4. Modifiche a `_live_close_position` Scenario 1 (router.py:548-563)

Sostituire il blocco ticker/entry_price con chiamata a `_reconcile_position_with_exchange()`. Se ritorna dict → usa `fill_price`. Se None (non dovrebbe succedere) → fallback `entry_price`.

### 5. Modifiche a `_on_uds_reconnect_sync` (router.py:929-968)

Sostituire la logica inline OKX (righe 932-968) con chiamata a `_reconcile_position_with_exchange()`. Ora calcola PnL reale invece di passare 0. Broadcast `position_reconciled_externally`.

### 6. WS Broadcast

- `main.py` startup reconcile → broadcast `"position_reconciled_externally"`
- `_on_uds_reconnect_sync` → broadcast `"position_reconciled_externally"`
- `_live_close_position` → NO broadcast (il caller gestisce UI update)
- Shape: `{symbol, side, entry_price, exit_price, quantity, pnl, pnl_pct, source, reason, timestamp}`

## File da modificare

| File | Azione |
|------|--------|
| `synthtrade/backend/app/scalping/router.py` | Aggiungere helper dopo riga 67; modificare Scenario 1 (548-563) e `_on_uds_reconnect_sync` (929-968) |
| `synthtrade/backend/app/main.py` | Modificare Step 6 (173-195); eliminare Step 7 (277-416); aggiungere import |

## Verifica

1. `ruff check` e `pyright` sui file modificati
2. Test esistente `test_1111e_restore_reconcile_already_closed` in `tests/integration/test_okx_integration.py` deve passare
3. Log al startup con SL/TP scattato: deve mostrare `[POSITION_RECONCILE] source=algo_history` o `source=ticker`, non `entry_price`
4. Manuale: avviare sessione live, aprire posizione, chiudere su OKX manualmente, riavviare bot → DB deve mostrare `closed` con PnL reale
