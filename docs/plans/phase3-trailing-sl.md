# TASK-1243 — Stop protettivo dopo break-even (OCO OKX)

> **Stato:** ✅ **COMPLETATO e validato in produzione** — 2026-08-04
> **Priorità:** alta dopo i risultati negativi delle sessioni recenti.

## 🧪 Prova live eseguita — 2026-08-04

**Sessione:** `6701e55b-8208-4dd2-a34f-0cf9552cbd14` | **algoId:** `3802582373171404800` | **Simbolo:** BTC-EUR

```
12:53:01  [BE] TRIGGER: entry=55154.6 current=55368.0 net_pct=+0.186% trigger=0.150%
          [AMEND_SL] newSlTriggerPx=55292.7 reqId=3ec5ad46b1ef45aa9c20fd9e47dc6c06
          [AMEND_SL] SUCCESS sCode=0 (latenza ~0.77s)
          [BE] SUCCESS: oldSL=54988.75 newSL=55292.70

13:08:04  Trade closed bracket_filled: BTC-EUR @ 55291.0 | PnL=+0.01 EUR (+0.05%)
```

Risultato: **+0.07 EUR salvati** rispetto alla perdita attesa ~-0.06 EUR se il vecchio SL fosse stato colpito.

---

## Decisione funzionale

Per ogni posizione spot long protetta da un OCO OKX, quando il rendimento **netto stimato all'uscita** raggiunge una soglia, l'app deve alzare lo Stop Loss dello **stesso OCO**. Non deve cancellare e ricreare l'OCO e non deve cercare un ordine per simbolo/lato.

Il risultato desiderato è conservativo: se il prezzo arriva vicino al TP e poi inverte, il trade deve uscire con una piccola protezione del profitto invece di tornare allo SL originale. Il TP resta invariato.

```text
entry -> +0.35% prezzo (circa +0.15% netto) -> amend stesso algoId
      -> nuovo SL circa +0.25% prezzo (circa +0.05% netto prima di slippage)
      -> TP originale +0.80% netto invariato
```

`profitto protetto` non significa profitto garantito: uno SL OCO a mercato (`slOrdPx=-1`) può eseguire sotto il trigger in un movimento rapido. Per questo il nuovo SL ha un margine rispetto al trigger ed il nome tecnico nei log deve essere `profit_lock_target`, non `guadagno_garantito`.

## Perché +0.30 / +0.35 non equivale al break-even

Le soglie di configurazione della strategia sono nette; il prezzo osservato è lordo. Con fee taker di ingresso/uscita 0.10% + 0.10%:

| Movimento lordo del prezzo | Rendimento netto stimato |
| --- | ---: |
| +0.2003% | circa 0.00% (break-even matematico) |
| +0.30% | circa +0.099% |
| +0.35% | circa +0.150% |
| SL che mira a +0.05% netto | circa +0.2506% dal prezzo di entry |

I calcoli non vanno duplicati con sottrazioni approssimate delle fee: usare sempre `_expected_net_pct_at_exit()` per valutare il trigger e `_exit_price_ratio()` (o un helper con nome esplicito) per ottenere il prezzo dell'uscita netta desiderata.

### Default raccomandato per la prima sperimentazione

```yaml
break_even_enabled: true
break_even_trigger_net_pct: 0.15   # circa +0.35% lordo con fee 0.10%+0.10%
break_even_lock_net_pct: 0.05      # nuovo SL circa +0.25% lordo
break_even_assumed_slippage_pct: 0.00 # informativo; non è una garanzia
```

Questo lascia circa 0.10 punti percentuali di spazio fra trigger e nuovo SL. Prima del live, il valore `lock` va scelto consapevolmente: maggiore lock = più protezione teorica ma minore tolleranza all'inversione; minore lock = più probabilità di un piccolo profitto reale dopo slippage. Le fee reali certificate della sessione, non un valore hard-coded, devono alimentare il calcolo.

## Invariante di identità OCO (anche per multi-sessione)

L'identità dell'ordine è il parent `algoId` memorizzato in `Position.oco_order_list_id` e in `scalping_trades.exchange_bracket_id`.

```text
sessione + posizione DB -> exchange_bracket_id (algoId)
                         -> amend-algos di quell'algoId
                         -> child ordId al fill
                         -> reconcile esatto già esistente
```

Non è ammesso usare `get_open_orders(symbol)[0]`, il primo SELL, o un match per simbolo/lato. Questa regola evita che una futura multi-sessione sullo stesso BTC-EUR modifichi l'OCO della posizione sbagliata. L'amend deve conservare l'`algoId`; se OKX restituisse un nuovo identificatore (da verificare in Demo), va aggiornato atomicamente nella posizione e nella riga DB prima di proseguire.

## Punto esatto di intervento

| Area | File | Intervento necessario |
| --- | --- | --- |
| Modello runtime | `scalping/engine/position_manager.py` | Aggiungere `break_even_triggered`, `break_even_activated_at`, `break_even_sl_price`; una transizione monotona/idempotente, non la chiamata HTTP. |
| Prezzo/trigger | `scalping/candle_processor.py` nel blocco che già elabora `pos = pm.get_open()` e pubblica `position_update` (circa righe 799-910) | Dopo aver calcolato il prezzo e prima del broadcast, valutare il trigger una sola volta e coordinare l'amend. Per v1: solo candela chiusa, non spike intra-candle. |
| OCO live | `execution/okx_exchange.py` | Nuovo metodo firmato `amend_exit_bracket_stop_loss(...)` verso `POST /api/v5/trade/amend-algos`, con `instId`, **exact `algoId`**, `newSlTriggerPx`, `newSlOrdPx: "-1"`, `reqId`. |
| Contratto provider | `execution/exchange_models.py` | Aggiungere il metodo al protocollo; l'adapter legacy Binance deve dichiarare esplicitamente il comportamento non supportato/fail-safe. |
| Persistenza | `scalping/db_ops.py` | Nuovo update mirato: `status=open AND exchange_bracket_id=<algoId>`. Aggiorna `sl_price` e i campi di audit. Mai update per solo simbolo o sessione. |
| Restore | `main.py` | Ripristinare i campi di attivazione dal DB, così un riavvio non invia un secondo amend. |
| UI/WS | `candle_processor.py` + frontend | Emettere `trailing_stop_activated` e includere stato/nuovo SL in `position_update`; mostrare “Profit lock attivo”, non “profitto garantito”. |

### Schema DB proposto

Una migration aggiunge a `scalping_trades`:

```sql
break_even_triggered boolean not null default false,
break_even_activated_at timestamptz null,
break_even_sl_price numeric null
```

`sl_price` continua a contenere lo SL effettivamente registrato su OKX. I tre campi aggiuntivi rendono l'operazione auditabile e impediscono una nuova modifica dopo restart.

## Sequenza sicura dell'operazione

1. Solo posizione `OPEN`, live, con `oco_order_list_id` valorizzato e `break_even_triggered == false`.
2. Calcolare `net_pct = _expected_net_pct_at_exit(entry, last_price, side, fees)`. Il trigger è soddisfatto solo quando `net_pct >= break_even_trigger_net_pct`.
3. Calcolare il nuovo SL dal target netto; quantizzarlo con `SymbolRules.tick_sz` usando `Decimal`. Per un long il nuovo SL deve essere strettamente maggiore dello SL attuale; non è mai consentito allentare uno stop. Implementare anche la simmetria SELL, pur restando oggi il prodotto long-only.
4. Acquisire un lock async per posizione/algoId e ricontrollare lo stato. Verificare che l'algoId specifico sia ancora pending/live, senza selezionare altri OCO del simbolo.
5. Inviare l'amend. Considerarlo riuscito soltanto con HTTP riuscito, payload top-level `code == "0"` e risultato individuale `sCode == "0"`.
6. **Solo dopo la conferma OKX**, aggiornare memoria e DB. Se il DB fallisce dopo la conferma exchange, lasciare lo stop già protetto, registrare errore critico e ritentare esclusivamente la persistenza dell'algoId esatto.
7. Inviare evento WS e log strutturato con session id, algoId, vecchio/nuovo SL, trigger netto, lock netto e `reqId`.

In caso di timeout/reject di amend, non modificare memoria/DB e non cancellare l'OCO. Il retry deve prima verificare lo stato dello stesso `algoId`. Un protocollo cancel-and-recreate non fa parte di questa fase: tra cancellazione e nuova creazione lascerebbe la posizione scoperta (o introdurrebbe rischio di doppia vendita).

## Validazione obbligatoria prima del live

La documentazione API ufficiale espone `POST /api/v5/trade/amend-algos`, ma la compatibilità effettiva dell'amend con l'OCO spot BTC-EUR dell'account EU va provata, non dedotta dalla documentazione generica.

1. Aggiungere uno spike `scripts/test_okx_demo.py` o test dedicato che in **OKX Demo**: apre una quantità minima, crea OCO, conserva `algoId`, emenda solo SL, legge `orders-algo-pending` e verifica stesso `algoId`, TP invariato e nuovo SL esatto.
2. Verificare il comportamento di `reqId`, dei codici `sCode`, del tick rounding e del caso ordine già in esecuzione.
3. Solo se lo spike è verde, attivare la feature flag in paper; poi un solo trade live piccolo con monitoraggio dei log e della pagina OKX.

Riferimento: [OKX API v5 — Amend algo order](https://app.okx.com/docs-v5/en/).

## Test richiesti

- Pricing: con fee 0.10%+0.10%, le quattro soglie della tabella sopra rispettano il calcolo netto; test BUY e SELL.
- Trigger: al primo close sopra soglia viene inviato un solo amend; close successivi non inviano ulteriori amend; prima della soglia resta lo SL originario.
- Sicurezza: nessun amend senza `algoId`, nessun amend che peggiori lo SL, errore OKX o DB non muta lo stato locale erroneamente.
- Adapter: path, body firmato, `newSlOrdPx=-1`, controllo sia `code` sia `sCode`.
- Persistenza/restore: update ristretto a `exchange_bracket_id`; dopo restart non avviene un secondo amend.
- Integrazione: il reconcile della chiusura successiva continua a seguire `algoId -> child ordId -> fill` e attribuisce la chiusura alla sola riga corretta.

## Fuori scope della prima versione

- Trailing continuo dietro ogni massimo. Questa è una singola promozione irreversibile dello SL a profit lock.
- Trigger tick-by-tick. La v1 usa chiusura candela per evitare amend su spike; un requisito intrabar richiederà un percorso WS dedicato, rate limiting e nuovi test.
- Fallback automatico cancel/recreate dell'OCO.

## Criteri di accettazione

1. L'OCO su OKX resta uno solo, ha lo stesso `algoId` ed il TP originale dopo l'amend.
2. Al trigger, lo SL mostrato da OKX, DB, REST e dashboard coincide dopo refresh/restart.
3. La perdita di rete/app dopo l'amend non consente un secondo amend e il reconcile attribuisce l'eventuale fill al trade corretto.
4. Un test Demo e test automatici verdi precedono qualsiasi attivazione live.
