# SynthTrade — Piano di Migrazione OKX -> Bybit v2 (rivisto)

> Data: 13 luglio 2026
> Stato: pronto per avvio TASK-1200 — account Bybit creato e in verifica, chiavi in creazione
> Sostituisce/integra: `bybit-migration-architecture-and-plan.md` (v1, 11/07/2026)
> Riferimento tecnico invariato: `bybit-api-reference-analysis.md` — leggere PRIMA di questo documento
> Vincolo di contesto permanente: **operatività in Italia, account EU/MiCA**. Ogni riferimento a coppie USDT-only o a comportamenti non verificati su dominio `.eu` va trattato come ipotesi da confermare, mai come default.

---

## 0. Cosa cambia rispetto al piano v1 e perché

Il piano v1 (`bybit-migration-architecture-and-plan.md`) resta valido nell'impianto economico (§0, il calcolo R con dati reali da screenshot) e nel riuso del layer pluggable già costruito per OKX. Questa v2 aggiunge quattro correzioni di rotta, tutte motivate da pattern di errore già vissuti durante la migrazione OKX (TASK-1119 → TASK-1129), che vogliamo **non ripetere**:

| # | Problema osservato su OKX | Correzione in questo piano |
|---|---|---|
| 1 | ccxt ha instradato male le chiamate per l'account EU per 6+ bug consecutivi (50119 ricorrente), risolti uno alla volta con fallback REST aggiunti a posteriori (`_direct_place_market_order`, `_direct_place_exit_bracket`, `_direct_fetch_trade_fee`, `_fetch_fill_price_by_order_id`...) | Decisione REST-vs-ccxt presa **una sola volta, nello spike**, non accumulata bug dopo bug. Vedi §2. |
| 2 | Gli errori Bybit arrivavano nei log come messaggi troncati o generici finché non si è deciso di loggare il body completo (TASK-908/2026-06-29, fatto solo dopo settimane) | Wrapper di errore strutturato con body completo **da subito**, prima ancora del primo ordine di test. Vedi §3. |
| 3 | Il default symbol OKX (`OKB-EUR`) è stato scelto sulla carta, poi si è scoperto empiricamente non disponibile in Demo, poi si è scoperto che il fee reale rendeva lo SL insostenibile — tre sorprese in tre momenti diversi | Selezione del default symbol come **output esplicito e documentato** dello spike, con criteri di liquidità verificati, non una scelta a priori. Vedi §4. |
| 4 | Il piano collector-abbondanza per OKX (`collector-abbondanza-piano-okx.md`, TASK-1120→1124) non è mai stato implementato — tutti i task sono ancora `Pending`. Il piano Bybit v1 lo trattava come "si porta quasi senza modifiche", assumendo un lavoro che in realtà non esiste ancora | Redesign completo dei collector per Bybit, da zero, incorporando anche ciò che era stato pensato (ma mai scritto) per OKX. Vedi §6. |

Aggiunte minori: catalogo `retCode` Bybit da costruire empiricamente (§3.3), task esplicito di aggiornamento `.env` per SL/TP prima di qualunque trade reale (§7), gestione del lock 48h sull'account nuovo (§1.1 — **non più bloccante**, l'account è già in verifica).

---

## 1. Stato di partenza (13/07/2026)

- Account Bybit EU: **creato, in verifica**.
- API key: **da creare** — prossimo step immediato, fuori da questo piano (azione manuale dell'utente).
- Nessun codice Bybit scritto. Il layer pluggable esistente (OKX) resta la base architetturale di riferimento.
- OKX resta **operativo come legacy** durante tutta questa migrazione — non si spegne nulla finché Bybit non è validato end-to-end. `EXCHANGE_PROVIDER` continuerà a supportare `binance`, `okx`, `bybit` in coesistenza.

### 1.1 — Lock 48h nuovo account

Non è più un rischio da pianificare: l'account è già stato creato e la verifica è in corso, quindi il lock (se applicabile) sta già scadendo in parallelo a questo lavoro di pianificazione. **Appena le chiavi sono pronte**, si parte direttamente da TASK-1200 senza attese aggiuntive.

---

## 2. Decisione REST-diretto vs ccxt — presa una volta sola, nello spike

### 2.1 Principio

Su OKX il pattern è stato: parte tutto su ccxt → un endpoint alla volta fallisce con `50119` per account EU → si aggiunge un fallback REST diretto per quell'endpoint specifico → si ripete per il prossimo endpoint. Risultato: `okx_exchange.py` oggi contiene **sia** i metodi ccxt **sia** i loro doppioni `_direct_*`, con logica di fallback sparsa (TASK-1123, 1124, 1126, 1129). Doppio lavoro, doppia superficie di bug, e il fallback è stato scoperto necessario solo dopo un trade fallito in produzione.

Per Bybit **non ripetiamo questo pattern**. La firma Bybit è più semplice di OKX (niente passphrase, solo HMAC-SHA256 su `timestamp+apiKey+recvWindow+body`), quindi il costo di scrivere REST diretto da subito è basso e il beneficio (zero ambiguità su dove ccxt instrada le richieste per un account `.eu`) è alto.

### 2.2 Processo decisionale (dentro TASK-1200, non dopo)

1. Lo script di spike (`scripts/test_bybit_demo.py`) **non usa ccxt come primo tentativo**. Ogni chiamata (balance, instruments, fee rate, order, OCO, WS auth) viene fatta con `httpx` + firma HMAC scritta a mano, esattamente come già fatto con successo per `historical_loader.py` OKX (`_load_from_okx` riscritto con httpx diretto — "zero ccxt fragility", commit `53f225f`).
2. Solo **se e quando** un endpoint REST diretto si rivela più complesso del previsto (es. parsing di risposte binarie, WebSocket signing non documentato), si valuta ccxt **per quel solo endpoint**, con una nota esplicita nello spike report che motiva l'eccezione.
3. Al termine dello spike, `docs/analysis/bybit-demo-spike-results.md` deve contenere una riga di decisione esplicita: *"Bybit adapter: REST diretto per tutti i metodi"* oppure *"REST diretto tranne [lista], motivo: [...]"*. Non si scrive `BybitExchangeAdapter` prima che questa riga esista.
4. **Se REST diretto risulta scomodo su tutta la linea** (poco probabile viste le premesse, ma va detto): si passa a ccxt **per intero**, non un ibrido. Il criterio è "una libreria sola, una volta decisa" — mai il doppio binario che abbiamo su OKX oggi.

### 2.3 Conseguenza pratica su TASK-1202/1203

`BybitExchangeAdapter` avrà una sola implementazione per metodo (`get_balance`, `place_market_order`, `place_exit_bracket`, ecc.), non una coppia ccxt+`_direct_*`. Questo riduce anche la superficie di test: un solo path da coprire per metodo invece di due.

---

## 3. Error Handling — strutturato dal primo commit, non accumulato a bug scoperti

### 3.1 Principio

Su OKX abbiamo dovuto introdurre a posteriori (TASK-908, fine giugno) il logging del body completo delle eccezioni CCXT, perché all'inizio si loggava solo `str(e)` troncato e passavano settimane prima di capire se un `Live trade failed` fosse per saldo insufficiente, LOT_SIZE, o altro. Per Bybit questo si scrive **prima** del primo ordine di test, non dopo il primo trade live fallito.

### 3.2 Wrapper di richiesta centralizzato

Ogni chiamata REST passa da un singolo metodo privato `_request()` in `BybitExchangeAdapter`, che:

```python
async def _request(self, method: str, path: str, params: dict | None = None,
                    body: dict | None = None, signed: bool = True) -> dict:
    """
    Unico punto di ingresso per ogni chiamata REST Bybit.
    - Firma automaticamente se signed=True
    - Logga SEMPRE: endpoint, http_status, retCode, retMsg, tempo di risposta
    - Solleva BybitApiError con il body RAW completo, mai troncato
    - Non interpreta né nasconde retCode != 0: la decisione su come reagire
      resta al chiamante (es. bracket fallito -> emergency close), qui si
      garantisce solo che l'informazione arrivi intatta
    """
    ...
    if data.get("retCode", 0) != 0:
        logger.error(
            "[BYBIT_API_ERROR] %s %s -> retCode=%s retMsg=%s http_status=%s raw=%s",
            method, path, data.get("retCode"), data.get("retMsg"),
            resp.status_code, data,
        )
        raise BybitApiError(
            ret_code=data.get("retCode"),
            ret_msg=data.get("retMsg"),
            http_status=resp.status_code,
            endpoint=path,
            raw_body=data,
        )
    return data
```

### 3.3 Catalogo retCode — costruito empiricamente, non copiato dalla doc

Su OKX ci sono voluti mesi sparsi (TASK-1126 sCode=50014, TASK-1127 sCode=51280, FIX-2026-07-10 sCode=51020, TASK-1128 sCode=51008) per scoprire uno alla volta i codici di errore reali che contano per il nostro flusso. Per Bybit, lo spike (TASK-1200) deve **provocare deliberatamente** almeno questi scenari e documentare il `retCode` reale osservato, prima di scrivere il router:

| Scenario da provocare nello spike | Cosa documentare |
|---|---|
| Ordine market con quantità sotto `minOrderQty` | retCode + retMsg esatti |
| Ordine market con importo sotto `minOrderAmt` | retCode + retMsg esatti |
| OCO con `stopLoss` price dalla parte sbagliata rispetto al last price (replica del bug 51280 OKX) | retCode + retMsg esatti — verificare se Bybit ha lo stesso tipo di validazione lato server |
| Saldo insufficiente per l'ordine richiesto | retCode + retMsg esatti |
| API key con permessi insufficienti (es. solo lettura) | retCode + retMsg esatti |
| Richiesta con timestamp fuori `recvWindow` | retCode + retMsg esatti |
| Simbolo non esistente o non tradeable | retCode + retMsg esatti |

Output: tabella in `docs/analysis/bybit-demo-spike-results.md`, sezione dedicata "Catalogo retCode osservati", nello stesso stile della sezione fee tier già presente nel report OKX. Questa tabella diventa la base per i messaggi di errore user-facing e per le decisioni automatiche del router (es. quali errori sono retry-able, quali sono bloccanti).

### 3.4 Eccezione strutturata, non stringa

```python
class BybitApiError(Exception):
    def __init__(self, ret_code: int, ret_msg: str, http_status: int,
                 endpoint: str, raw_body: dict):
        self.ret_code = ret_code
        self.ret_msg = ret_msg
        self.http_status = http_status
        self.endpoint = endpoint
        self.raw_body = raw_body
        super().__init__(f"Bybit API error [{ret_code}] {ret_msg} @ {endpoint}")
```

Questo va oltre `ExchangeOrderError` generico già esistente (che su OKX ha dovuto essere esteso a posteriori con `original_exception`/`original_details`, TASK-908/2026-06-30): qui il dettaglio strutturato c'è **fin dalla prima riga**, non viene aggiunto dopo aver perso informazione nei log per settimane. Il router continua a ricevere `ExitProtectionError`/`ExchangeOrderError` per l'interfaccia provider-neutral esistente, ma `BybitApiError` viene propagato come `original_exception` fin dal primo commit, non aggiunto in un secondo momento.

### 3.5 Nessun fallback silenzioso su valori di dominio

Regola esplicita, coerente con `fee_tier_certified` già introdotto per OKX: se `get_trade_fee()` fallisce, il sistema non deve mai sostituire silenziosamente un valore hardcoded (0.001/0.001) senza segnalarlo. Stesso pattern `certified: bool` va nel `FeeTier` di Bybit fin dal primo commit, non aggiunto dopo aver scoperto (come su OKX) che un fee tier non certificato produceva calcoli SL/TP sbagliati.

---

## 4. Default Symbol — selezione EU-only, basata su dati reali, non su assunzione USDT

### 4.1 Vincolo di contesto (da NON perdere mai in questa migrazione)

SynthTrade opera per un utente **in Italia**, quindi sotto le regole EU/MiCA. Qualunque riferimento a `BTCUSDT` come coppia operativa di default è, salvo verifica esplicita, un'ipotesi non allineata a questo vincolo — un conto tenuto in USDT espone l'utente a un asset la cui natura regolatoria e la cui liquidità reale per un conto retail EU vanno verificate, non assunte per comodità implementativa. Il dominio `bybit.eu` esiste specificamente per la compliance MiCA: la coppia di default operativa deve essere una coppia **EUR**, salvo che lo spike dimostri che nessuna coppia EUR ha liquidità sufficiente per lo scalping — in quel caso è una scoperta da documentare esplicitamente, non un default silenzioso.

### 4.2 Processo di selezione (output obbligatorio dello spike, TASK-1200)

1. Interrogare `GET /v5/market/instruments-info?category=spot` sull'ambiente realmente usato (`api.bybit.eu` se l'accesso custom è confermato, altrimenti l'ambiente di test disponibile).
2. Filtrare per `quoteCoin=EUR` e `status=Trading`.
3. Per ogni coppia EUR candidata, recuperare volume 24h e spread bid/ask reale (`GET /v5/market/tickers`) — stessa metodologia già usata per confermare `OKB-EUR`/`BNB-USDC` non disponibili su OKX Demo.
4. Ordinare per liquidità (volume 24h decrescente, spread relativo crescente).
5. Scegliere come default la coppia EUR più liquida. Se il testnet non espone le stesse coppie del mainnet EU (come già successo su OKX Demo vs Live), documentare separatamente i due cataloghi — **stesso problema già noto** (TASK-1116.G "instrument discovery deve essere environment-aware", mai risolto per OKX e da non ripetere qui: la cache/validazione strumenti per Bybit deve essere ambiente-consapevole fin da subito, non aggiunta dopo la prima sessione fallita).
6. **Se nessuna coppia EUR ha liquidità sufficiente** (spread anomalo, volume vicino a zero): documentarlo esplicitamente come limite strutturale di Bybit EU per lo scalping, e valutare — prima di scrivere altro codice — se la migrazione ha ancora senso o se conviene la coppia EUR meno peggio con parametri di rischio più larghi (size più piccola, no scalping stretto). Questa è una decisione di prodotto, non tecnica: va presa con Andrea, non assunta dall'agente.

### 4.3 Output atteso in `docs/analysis/bybit-demo-spike-results.md`

Tabella con tutte le coppie EUR trovate, volume, spread, e la riga di decisione finale: *"Default symbol: XXXEUR — motivo: [liquidità/spread osservati]"*. Stesso identico formato già usato per `BTC-EUR` su OKX (`okx-demo-spike-results.md` §2), che si è dimostrato utile.

---

## 5. SL/TP — task esplicito di aggiornamento config, non solo calcolo su carta

Il piano v1 calcola (§0.4) i target netti coerenti col fee reale Bybit (opzione B: SL netto 0,75% / TP netto 1,10%, R:R 1,47:1) ma non lo trasforma in un task che tocchi effettivamente `.env`/`scalping_runtime_config`. Questo va fatto **prima** della prima sessione demo con trade reali, non dopo — è esattamente l'errore che ha reso OKX insostenibile (SL a 0,3% mai ricalibrato sul fee reale finché non si è fatta l'analisi retroattiva sui 69 trade storici).

**TASK-1211.A** (nuovo, si inserisce prima di TASK-1211 validazione E2E):
- Aggiornare `SCALPING_STOP_LOSS_PCT` e `SCALPING_TAKE_PROFIT_PCT` in `.env` (o via `scalping_runtime_config` se si preferisce runtime) con i valori ricalcolati sul fee tier **realmente certificato** da Bybit (non lo screenshot statico — il valore va letto da `get_trade_fee()` a session start, come da §5.0 del piano v1, e i target vanno derivati da quel valore a runtime, non hardcoded una volta per tutte).
- Verificare che `_net_to_gross_pct()` con fee Bybit positive (non rebate, confermato §0.1) produca segno atteso — stesso tipo di bug già preso (TASK-1127 sCode 51280 su OKX: SL calcolato dalla parte sbagliata per assunzione errata sul segno del risultato). Va scritto un test esplicito con i fee reali Bybit (0,10%/0,25% o 0,15%/0,25% a seconda della coppia scelta in §4) **prima** del primo trade demo, non scoperto a bracket rifiutato.
- Nessuna sessione con `mode=live` può partire se questo task non è chiuso.

---

## 6. Collector Intelligence — redesign completo (non un porting, perché il lavoro OKX non esiste ancora)

### 6.1 Correzione di prospettiva

Il piano v1 assumeva che il lavoro di "abbondanza collector" fatto per OKX si potesse portare su Bybit "quasi senza modifiche". In realtà, verificando `docs/plans/collector-abbondanza-piano-okx.md` e `docs/TASKS.md`, **TASK-1120 → TASK-1124 (whale enable, OrderBookImbalanceCollector, SpreadCollector, funding/OI nativo OKX, spike long/short ratio) sono ancora tutti `Pending`**. L'unico lavoro realmente completato per OKX è il TASK-1125 (diagnostica coverage, log-only, zero nuovi collector) e il graceful-skip dei 3 collector Binance-Futures-bound per simboli EUR (TASK-1116). Quindi per Bybit non c'è nulla da "portare": va progettato da zero, tenendo però tesoro delle idee già scritte per OKX (che restano valide concettualmente, solo mai implementate).

### 6.2 Stato di partenza reale dei collector per un simbolo EUR spot (OKX o Bybit, stesso problema)

| Collector | Dipendenza | Stato per spot-EUR senza perpetual reale |
|---|---|---|
| `funding_rate` | Futures/perpetual del simbolo | Strutturalmente `None` — nessun exchange ha funding rate per uno spot-only EUR pair |
| `open_interest` | Futures/perpetual del simbolo | Idem |
| `long_short_ratio` | Futures/perpetual del simbolo | Idem |
| `cvd` | Trade stream pubblico | **Disponibile ovunque** — Bybit espone `publicTrade` con campo lato taker (`S`, da verificare empiricamente come già notato per OKX `side`) |
| `fear_greed` | Alternative.me, indipendente da exchange | Disponibile sempre |
| `whale` | Whale Alert RSS + Blockchair, indipendente da exchange | Disponibile sempre, oggi disabilitato di default (`SCALPING_WHALE_ENABLED=false`) |
| `sentiment` | CryptoCompare/NewsAPI, indipendente da exchange | Disponibile sempre, soggetto a intermittenza DNS già nota |
| `onchain` | Blockchain.com/Blockchair/Dune, indipendente da exchange | Disponibile sempre, peso attuale 0 nello score |

Conclusione: **3 collector su 8 sono strutturalmente impossibili** per un simbolo EUR spot-only, su qualunque exchange — non è un problema Bybit specifico, è la natura dello strumento (esattamente come già scritto per OKX in TASK-1116.B). Passare da OKX a Bybit non cambia questo numero. La vera "abbondanza" recuperabile viene da due fonti: (a) attivare quello che già esiste ma è spento (whale), (b) collector nuovi che usano dati sempre presenti su un order book spot, exchange-agnostici per design.

### 6.3 Lavoro da fare — in ordine di rischio/impatto

**TASK-1209.A — Attivare whale + verificare sentiment (zero rischio, zero codice nuovo)**
Stesso identico contenuto già scritto per OKX in TASK-1120 (`collector-abbondanza-piano-okx.md`), semplicemente mai eseguito. Vale per Bybit esattamente come varrebbe per OKX, perché questi due collector sono indipendenti dall'exchange:
- `SCALPING_WHALE_ENABLED=true` in `.env`.
- Verificare se `sentiment` risponde regolarmente con Bybit attivo (il problema DNS intermittente osservato su OKX non è legato all'exchange, va comunque riverificato).

**TASK-1209.B — OrderBookImbalanceCollector (nuovo, exchange-agnostico per design)**
Stessa logica già pensata per OKX in `collector-abbondanza-piano-okx.md` TASK-1121, riscritta per l'endpoint Bybit:
```
GET https://api.bybit.eu/v5/market/orderbook?category=spot&symbol={symbol}&limit=25
```
(o l'host che risulterà corretto dallo spike, §2). Calcola lo squilibrio bid/ask sui primi N livelli:
```python
imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
score = clamp(imbalance * 100, -100, 100)
```
Nessuna autenticazione richiesta, nessuna dipendenza da futures. Funziona identico su qualunque coppia spot, EUR inclusa — è il candidato con il miglior rapporto sforzo/beneficio per colmare il buco lasciato dai 3 collector strutturalmente assenti.

**TASK-1209.C — SpreadCollector (nuovo, exchange-agnostico per design)**
Stessa logica già pensata per OKX in TASK-1122, riscritta per Bybit:
```
GET https://api.bybit.eu/v5/market/tickers?category=spot&symbol={symbol}
```
Spread relativo rispetto a una media mobile recente, come segnale di cautela (non di bias direzionale — stesso avvertimento di design già scritto per OKX: va deciso se integrarlo nel weighted score o come moltiplicatore separato sul gate `tradeable`, non assumere).

**TASK-1209.D — Funding rate/OI via derivati Bybit, solo se si opera su un simbolo con perpetual reale**
Se la coppia di default scelta in §4 finisce per essere una coppia EUR (probabile, vista la §4.1), questo task **non si applica** — nessun perpetual Bybit è quotato in EUR, esattamente come su OKX (`BTC-USDT-SWAP`, mai `BTC-EUR-SWAP`). Va scritto solo come opzione futura se si decidesse di operare su una coppia con base asset che ha un perpetual Bybit reale (es. BTC, ETH), con lo stesso avvertimento già dato per OKX in TASK-1123: il funding rate riflette il sentiment sull'asset base, non sulla coppia quotata specifica, e va documentato come tale.

**TASK-1209.E — Spike: esiste un equivalente Bybit per long/short ratio?**
Stessa domanda aperta già lasciata in sospeso per OKX (TASK-1124 del piano collector OKX). Da verificare sulla doc Bybit v5 (famiglia endpoint simile a `market/account-ratio` se esiste) prima di aprire un task di implementazione — se non esiste, va documentato come strutturalmente assente, non lasciato "da fare" a tempo indeterminato.

### 6.4 Wiring nel SignalScoreEngine

`SignalScoreEngine` va reso **provider-aware fin da subito per Bybit** (a differenza di OKX, dove TASK-1116.C — "collector adapter provider-aware" — è ancora `Pending` a distanza di settimane). Poiché stiamo scrivendo il codice ex novo, non c'è motivo di introdurre di nuovo il debito tecnico "i collector chiamano un host fisso ignorando `EXCHANGE_PROVIDER`":

```python
active_collectors = {
    "cvd":              (cvd_calculator,       0.25),
    "fear_greed":       (fear_greed_collector, 0.15),
    "order_book_imbalance": (obi_collector,    0.20),   # nuovo
    "spread":           (spread_collector,     0.10),   # nuovo, o gate separato — vedi 6.3.C
    "sentiment":        (sentiment_collector,  0.10),
    "whale":            (whale_collector,      0.10),   # ora abilitato
    "onchain":          (onchain_collector,    0.10),
    # funding_rate / open_interest / long_short_ratio: assenti per design
    # su simboli EUR spot-only — esclusi dal denominatore, non a peso 0 fantasma
}
```

I pesi sopra sono **provvisori** — vanno ricalibrati con la stessa metodologia già applicata per OKX (log diagnostico `[COVERAGE_REAL]`, TASK-1125, che invece è stato effettivamente completato e va riusato tale e quale per Bybit) prima di considerarli definitivi. Non assegnare pesi a intuito: prima si osservano 2-3 sessioni reali, poi si ridistribuisce sui numeri osservati.

### 6.5 Cosa NON fare

Non riattivare `funding_rate`/`open_interest`/`long_short_ratio` puntati su Binance Futures "perché tanto rispondono" — è esattamente il bug che ha inquinato la coverage su OKX (TASK-1116.B, OKB-EUR non in `FUTURES_SYMBOL_MAP`, 400 Bad Request silenziosi). Per Bybit, questi 3 collector devono avere fin dal primo commit un `is_symbol_supported()` esplicito (stesso pattern TASK-1125) che ritorna `False` per qualunque coppia EUR, senza mai tentare la chiamata.

---

## 7. Provider Model — configurazione (invariato da v1, riportato per completezza)

```env
EXCHANGE_PROVIDER=bybit
TRADING_MODE=test

BYBIT_API_KEY=
BYBIT_SECRET_KEY=
BYBIT_BASE_URL=https://api.bybit.eu        # da confermare nello spike; fallback testnet se EU bloccato

BYBIT_API_KEY_LIVE=
BYBIT_SECRET_KEY_LIVE=

ALLOW_LIVE_MODE=false
```

Nessuna passphrase (differenza positiva rispetto a OKX). `exchange_provider` computed field esteso con branch `bybit`, stesso pattern già usato per `okx` in TASK-1101.

---

## 8. Ordine di Task Rivisto (TASK-1200 → TASK-1213+)

### TASK-1200 — Spike Bybit EU/Demo (bloccante per tutto il resto)

Sottotask, in ordine di esecuzione:

1. **1200.A — Verifica accesso API custom EU** (punto critico #1 di `bybit-api-reference-analysis.md`). Con le chiavi appena create: generare una API key HMAC "System-generated" con permessi Trade su Spot, tentare una prima chiamata autenticata read-only (`GET /v5/account/wallet-balance`). Se fallisce con un errore legato a "Connect to Third-Party Applications" o simile, documentarlo **subito** come blocco e fermarsi qui prima di procedere oltre.
2. **1200.B — Decisione REST vs ccxt** (§2). Scrivere `scripts/test_bybit_demo.py` con chiamate REST dirette (httpx + HMAC manuale) come primo tentativo per ogni endpoint.
3. **1200.C — Server time / recvWindow** — verificare drift oraio, stesso tipo di controllo già fatto per OKX (`GET /v5/public/time` se esiste, o equivalente).
4. **1200.D — Instrument discovery EU-only** (§4) — query completa coppie EUR, volume, spread, output tabellare.
5. **1200.E — Fee tier reale** — `GET /v5/account/fee-rate?category=spot&symbol=...` sulla coppia scelta in 1200.D, confrontato numericamente con l'ultimo fee OKX reale (screenshot 0,20%/0,35%).
6. **1200.F — Market order minimo** sulla coppia scelta, documentare fill price, quantity, commission, commission asset.
7. **1200.G — OCO Spot** — piazzare un bracket TP/SL Market-al-trigger, documentare `stopOrderType`/`ocoTriggerBy` nella risposta.
8. **1200.H — Catalogo retCode** (§3.3) — provocare deliberatamente tutti gli scenari di errore elencati in tabella, documentare i retCode reali.
9. **1200.I — WS privato `order`** — ascoltare il fill dell'OCO piazzato in 1200.G, confermare se un solo topic basta per ordini normali + TP/SL o se serve un canale separato (come su OKX). Verificare se l'accesso WS privato è bloccato per EU come già visto su OKX (60032) — se sì, prevedere da subito lo stesso pattern REST-polling fallback già implementato in `OkxOrderEventStream`.
10. **1200.J — WS pubblico `publicTrade`** — verificare campo lato taker per CVD.
11. **1200.K — Decisione finale documentata** in `docs/analysis/bybit-demo-spike-results.md`: REST vs ccxt, default symbol, fee reale, catalogo retCode, esito WS privato EU.

**Blocco:** nessun task successivo parte se 1200.A fallisce senza soluzione, o se 1200.E rivela che le fee reali non giustificano economicamente la migrazione (confronto esplicito con R_okx=0,70% già noto).

---

### TASK-1201 — Config provider Bybit
Estensione `config.py`/`.env.example` con le variabili §7. Stesso pattern TASK-1101 OKX. Nessuna sorpresa attesa qui.

### TASK-1202 — BybitExchangeAdapter REST-diretto (decisione da 1200.B applicata)
Implementa `ExchangeAdapterProtocol` esistente. Un solo path di implementazione per metodo (§2.3), wrapper `_request()` centralizzato con error handling strutturato (§3.2). Nessun metodo `_direct_*` duplicato: se REST diretto è la scelta, è l'unica via.

### TASK-1203 — Exit bracket Bybit
`place_exit_bracket()` con OCO Spot nativo (`stopOrderType=OcoOrder`), TP/SL sempre Market al trigger (mai Limit, per il rischio di gamba scoperta già documentato in `bybit-api-reference-analysis.md` §7). Emergency close se il bracket fallisce, `ExitProtectionError` con `BybitApiError` come `original_exception`.

### TASK-1204 — BybitWSClient market data
Canali `kline.{interval}.{symbol}` e `publicTrade.{symbol}` su `wss://stream.bybit.com/v5/public/spot` (o host EU se diverso, da confermare in 1200.J). Verificare se esiste la stessa separazione public/business già vista su OKX (probabile di no, da confermare — non assumere).

### TASK-1205 — BybitOrderEventStream
Un solo topic WS privato `order` per ordini normali + OCO (se confermato in 1200.I), oppure REST polling fallback se il WS privato è bloccato per EU.

### TASK-1206 — Estensione exchange_factory + router (nessun refactor strutturale)
Nuovo branch `bybit` nelle funzioni builder già provider-neutral (`_build_exchange_adapter`, `_build_market_ws`, `_build_order_event_stream`).

### TASK-1207 — Verifica/estensione CHECK constraint DB
Controllare se `exchange_provider` ha un vincolo esplicito ai soli valori `('binance','okx')` — se sì, migration minima. Stesso tipo di bug già trovato per `mode='TEST'` su OKX (TASK-1116.D), da anticipare qui invece di scoprirlo al primo insert fallito.

### TASK-1208 — Frontend exchange-neutral
Dropdown simboli filtrato sul catalogo EU reale (§4), badge `BYBIT DEMO`/`BYBIT LIVE`, label saldo.

### TASK-1209 — Collector Intelligence (redesign completo, §6)
Sottotask 1209.A → 1209.E come descritti in §6.3, in quell'ordine di priorità.

### TASK-1210 — Test integration con fake Bybit adapter
Stesso pattern `fake_okx_adapter.py` + `test_okx_integration.py`: happy path, bracket failure, stop session, restore open/closed, fee/net pricing con fee Bybit reali (non rebate).

### TASK-1211.A — Aggiornamento SL/TP in config (§5) — nuovo, bloccante prima di 1211
Aggiornare i target netti sul fee tier Bybit certificato, test esplicito sul segno di `_net_to_gross_pct()` con fee positive Bybit.

### TASK-1211 — Validazione Demo/Testnet end-to-end
Sessione scalping completa con trade minimo, verificando anche i retCode del catalogo (§3.3) su eventuali errori reali incontrati.

### TASK-1212 — Verifica economica finale
Confronto esplicito N sessioni Bybit (SL/TP ricalibrati da 1211.A) vs baseline storica OKX (18 sessioni, 70 trade, 34.3% win rate, -3.05 USDC). Risposta esplicita alla domanda "la migrazione ha risolto il problema economico?" — se no, la conclusione onesta potrebbe essere rivedere i parametri di rischio piuttosto che cambiare ancora exchange (nota già presente in v1 §12, confermata qui).

### TASK-1213 — Cutover
`EXCHANGE_PROVIDER=bybit` default, runbook operativo (stesso formato `okx-live-runbook.md`), safety gates invariati (`ALLOW_LIVE_MODE=false` di default).

---

## 9. Definition of Done (aggiornata)

Rispetto a v1, aggiungo esplicitamente:

- [ ] 1200.A ha una risposta empirica positiva documentata (accesso API EU confermato) — condizione di partenza per tutto il resto.
- [ ] La decisione REST-vs-ccxt è scritta una volta in `bybit-demo-spike-results.md` e rispettata in tutto `BybitExchangeAdapter` — nessun metodo con doppia implementazione.
- [ ] Il catalogo retCode (§3.3) esiste e copre almeno i 7 scenari elencati prima del primo trade demo.
- [ ] Il default symbol è una coppia EUR scelta su dati di liquidità reali, oppure l'assenza di liquidità EUR sufficiente è documentata esplicitamente come limite, non aggirata in silenzio con USDT.
- [ ] SL/TP in config sono stati aggiornati sul fee tier Bybit certificato **prima** di qualunque sessione con `mode=live` (TASK-1211.A chiuso).
- [ ] I collector `order_book_imbalance` e `spread` sono implementati e attivi, non solo pianificati.
- [ ] `funding_rate`/`open_interest`/`long_short_ratio` ritornano `is_symbol_supported()=False` per la coppia EUR scelta senza mai tentare una chiamata di rete.
- [ ] Il confronto economico finale (TASK-1212) è documentato con un verdetto esplicito, non lasciato implicito nei numeri grezzi.

---

## 10. Prossimo passo immediato

Appena le chiavi API Bybit sono pronte: avviare **TASK-1200.A** (verifica accesso). È l'unico gate realmente bloccante — tutto il resto di questo piano presuppone che quel punto risponda positivamente. Se la chiave sblocca correttamente `GET /v5/account/wallet-balance`, si procede in sequenza 1200.B → 1200.K nello stesso spike script, senza aprire task separati per ogni sottopunto (stesso ritmo già tenuto per `test_okx_demo.py`).
