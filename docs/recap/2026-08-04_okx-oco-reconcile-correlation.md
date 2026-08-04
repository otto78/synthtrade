# Reconcile OKX OCO post-offline — TASK-1244

## Problema osservato

Un trade BTC-EUR poteva chiudersi correttamente su OKX tramite OCO mentre SynthTrade era offline. Al riavvio l'app mostrava una chiusura con prezzo entry e/o orario di reconcile, oppure lasciava il trade aperto. Il pericolo maggiore era che un'altra vendita BTC-EUR venisse scelta come chiusura del trade.

## Root cause

`OkxExchangeAdapter.get_algo_orders_history()` richiamava prima `GET /api/v5/trade/fills` filtrato soltanto per simbolo. Quel payload è un elenco di fill di account; non era la relazione parent OCO → ordine di esecuzione. `_reconcile_position_with_exchange()` provava prima `algoId`, poi ricadeva su `side=sell` e infine su `entry_price`.

Questi ultimi due fallback sono incompatibili con operazioni manuali, più strategie sullo stesso simbolo e multi-sessione futura.

## Contratto implementato

Per una posizione protetta da OCO, l'unica chiusura accettata è:

```
scalping_trades.exchange_bracket_id (algoId)
    → GET /api/v5/trade/orders-algo-history?algoId=…&ordType=oco
    → ordId / ordIdList del child order
    → GET /api/v5/trade/fills?ordId=…
    → prezzo medio ponderato + ultimo fillTime
```

`actualSide` dell'OCO determina `take_profit` o `stop_loss`. Il `fillTime` viene convertito in ISO UTC e usato da tutti i call path di reconcile per DB, memoria e broadcast.

## Safety e multi-sessione

- L'identità è il `algoId`, non il simbolo, il lato o la quantità.
- La persistenza esistente salva già `exchange_bracket_id`, `exchange_tp_order_id` e `exchange_sl_order_id`; non serve migration.
- Quando il parent OCO o il child fill non sono ancora disponibili (propagazione API), il reconcile restituisce `None`: non viene scritto un PnL o timestamp falso. La posizione viene conservata per un retry.
- Le sessioni attuali restano singleton a livello di `_execution_state`; il giorno in cui saranno concorrenti dovranno avere uno state/position manager per sessione. Questa patch però impedisce già l'errore più grave: la cross-associazione di chiusure sullo stesso strumento.

## Test

I test verificano: OCO TP, OCO SL, saldo ancora aperto, fill di un altro OCO ignorato, fill assente non sintetizzato, failure del balance check e aggregazione ponderata dei partial fill del child order.

## Aggiornamento — polling REST e restore (04/08)

- Nel fallback REST per account OKX EU, un OCO pendente veniva inserito in
  `seen_algos`. Quando lo stesso `algoId` diventava `effective`, il fill veniva
  quindi scartato: è la causa diretta della posizione rimasta aperta sotto SL.
- Gli OCO pendenti non vengono più deduplicati come terminali. Il bootstrap del
  polling richiama inoltre una riconciliazione del solo bracket salvato.
- Il restore legge tutti i record `open`: quelli più vecchi sono chiusi soltanto
  dopo verifica del rispettivo `algoId`; se uno non è verificabile, la sessione
  viene messa in pausa per impedire un'entry duplicata.
