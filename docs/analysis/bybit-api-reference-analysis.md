# Bybit API v5 — Reference Tecnico per SynthTrade

> Scopo: documento di riferimento da consultare PRIMA di scrivere codice sull'integrazione Bybit, per evitare di procedere a tentativi — stesso principio già seguito per `docs/analysis/okx-api-reference-analysis.md`.
> Copre solo ciò che serve a SynthTrade (spot, TP/SL/OCO nativi, WebSocket per CVD, fee reali).
> Data compilazione: Luglio 2026. Verificare sempre https://bybit-exchange.github.io/docs/v5/intro per eventuali aggiornamenti prima di implementare.
> **Non ancora verificato empiricamente** — tutto ciò che segue va confermato con chiamate reali (Bybit Demo Trading o Testnet) prima di fidarsi al 100%, esattamente come richiesto per OKX (TASK-1100).

---

## 0. Perché Bybit e motivazione del cambio

Il motivo del cambio da OKX a Bybit non è normativo (MiCA è già risolto con l'entità EU di OKX), ma **economico**: con OKX, lo Stop Loss configurato allo 0.3% viene eroso dal costo di round-trip delle fee al punto da rendere lo scalping matematicamente non sostenibile — per coprire le fee servirebbe uno SL più largo del prezzo di acquisto stesso in alcuni scenari limite, il che non ha senso operativo ed è anche tecnicamente non implementabile (uno SL sopra l'entry per un LONG non è uno stop loss).

**Punto critico da verificare subito, prima di qualunque altro lavoro:** dalla ricerca preliminare, Bybit **spot** ha un fee standard non-VIP di **0.10% maker / 0.10% taker** (nessun rebate, a differenza del tier OKX Demo osservato in `okx-demo-spike-results.md` che era -0.2%/-0.35%, cioè un rebate netto). Un round-trip BUY market + SELL market a fee standard costerebbe quindi **0.20%** — che è già i due terzi di uno SL allo 0.3%, lasciando margine ancora più risicato di quanto sperato. Questo NON conferma automaticamente che Bybit risolva il problema di fondo: **il primo compito dello spike Bybit deve essere verificare il fee tier reale applicabile all'account (non VIP di default, ma verificare se ci sono sconti per referral/BIT token/volume) e ricalcolare se lo SL configurato ha senso economico**, esattamente come già fatto per OKX in `okx-demo-spike-results.md` §3.

Se il fee reale finisce per essere comparabile o peggiore rispetto a OKX, la soluzione strutturale del problema originale (SL 0.3% eroso dalle fee) non è "cambiare exchange" ma **allargare lo SL/TP oppure ridurre la frequenza di round-trip** (es. filtri di ingresso più selettivi) — un punto da tenere presente indipendentemente dall'esito della migrazione.

---

## 1. Base URL e ambienti

| Ambiente | Base URL REST | Base URL WS pubblico | Base URL WS privato/trade |
|---|---|---|---|
| Globale (mainnet) | `https://api.bybit.com` (mirror: `api.bytick.com`) | `wss://stream.bybit.com/v5/public/spot` | `wss://stream.bybit.com/v5/private`, `wss://stream.bybit.com/v5/trade` |
| Testnet | `https://api-testnet.bybit.com` | `wss://stream-testnet.bybit.com/v5/public/spot` | `wss://stream-testnet.bybit.com/v5/private` |
| **EEA (EU) — MiCA** | `https://api.bybit.eu` | verificare (non documentato esplicitamente per EU nella pagina Connect) | verificare |

**Punto critico #1 (bloccante, da verificare EMPIRICAMENTE prima di qualunque riga di codice):** la documentazione ufficiale Bybit dichiara esplicitamente:

> "EEA users: use https://api.bybit.eu for mainnet (**EU site API only support "Connect to Third-Party Applications" feature for API broker user**)"

Questo è potenzialmente un blocco strutturale equivalente (o peggiore) rispetto al blocco WS-private-EU che abbiamo già incontrato su OKX (TASK-1100.G). "Connect to Third-Party Applications" nel pannello Bybit è il flusso pensato per collegare bot/piattaforme già whitelistate da Bybit stesso (es. 3Commas, Bitsgap, Insilico) selezionandole da un menu a tendina — non è chiaro dalla documentazione se generi comunque una coppia key/secret HMAC standard utilizzabile da un client custom (il nostro backend FastAPI), oppure se sia vincolato all'app selezionata lato Bybit (whitelisting IP/app-level).

**Evidenza aggiuntiva preoccupante trovata durante la ricerca:** la documentazione di supporto di 3Commas (un aggregatore di bot già integrato ufficialmente con Bybit) dichiara testualmente: **"Bybit EU accounts cannot be connected to 3Commas via Fast Connect or API keys."** Se un partner ufficiale e whitelistato non riesce a collegarsi via API key a un account Bybit EU, è un segnale forte che l'account Bybit EU (dominio `bybit.eu`, sotto licenza MiCA) abbia **l'accesso API per trading automatizzato di terze parti disabilitato lato piattaforma**, non solo "limitato a un menu a tendina".

**Azione obbligatoria prima di TASK-1200 (spike):** verificare con un account Bybit EU reale se:
1. è possibile generare una API key di tipo "System-generated" con permessi Trade su Spot, utilizzabile da un client HMAC custom (non da un'app whitelistata);
2. se la risposta è no, valutare se Bybit offre comunque un'entità non-EU utilizzabile legalmente da un residente italiano (storicamente Bybit ha ristretto l'accesso retail per utenti UE al solo dominio `.eu` dopo la MiCA — verificare lo stato a luglio 2026, dato che l'articolo di settore trovato durante la ricerca conferma: "Bybit is migrating EEA clients to its MiCA licensed entity, bybit.eu, with a hard cutover during 2026");
3. in assenza di soluzione, questa sarebbe una condizione di **stop non aggirabile** — a differenza del blocco OKX (dove il WS privato era bloccato ma il REST/trading funzionava con un workaround REST polling), qui il rischio è che **l'intera pipeline REST di trading** sia preclusa per un utente retail EU con API custom.

Non procedere oltre TASK-1200 (spike) se questo punto non è risolto con una osservazione diretta (screenshot pannello API Bybit EU + tentativo di creazione chiave + primo REST call autenticato riuscito).

---

## 2. Autenticazione REST

Bybit v5 supporta due tipi di chiave:
- **HMAC (System-generated)** — la più comune, coppia API key + secret generata da Bybit.
- **RSA (Self-generated)** — l'utente genera la propria coppia di chiavi e fornisce solo la pubblica a Bybit.

Per ogni richiesta autenticata sono richiesti 4 header:

```
X-BAPI-API-KEY: <api_key>
X-BAPI-SIGN: <firma HMAC-SHA256 o RSA-SHA256, hex lowercase per HMAC>
X-BAPI-TIMESTAMP: <millisecondi Unix>
X-BAPI-RECV-WINDOW: <finestra di validità in ms, default 5000>
```

**Stringa da firmare:**
- Per GET: `timestamp + apiKey + recvWindow + queryString`
- Per POST: `timestamp + apiKey + recvWindow + jsonBodyString`

Vincolo temporale (equivalente al `50102` di OKX): la richiesta è respinta se `timestamp` non rientra in `[server_time - recv_window, server_time + 1000)`. Usare sempre UTC e sincronizzare l'orologio locale — punto già rilevante nel progetto per il drift Windows osservato con OKX.

**Nessuna passphrase terza richiesta** (a differenza di OKX) — solo key + secret. Questo semplifica la configurazione rispetto a OKX (`OKX_PASSPHRASE` non ha equivalente qui).

---

## 3. Vincoli operativi recenti (2026) da non ignorare

Dalla ricerca emergono alcuni cambiamenti Bybit specifici del 2026 rilevanti per un'integrazione nuova:

- **Blocco creazione API key nelle prime 48 ore dalla registrazione dell'account** — per risk control. Se l'account Bybit EU di Andrea è nuovo, pianificare questo ritardo prima di poter fare qualunque test.
- **Creazione API key possibile solo da browser desktop**, non da app mobile.
- **Dal 10 febbraio 2026**, le whitelist IP e i permessi legati a operazioni fiat sulle API key **non sono più modificabili via API** (solo via browser) — impatta l'endpoint "Modify Master API Key" se il progetto avesse mai pensato di automatizzare la rotazione chiavi.
- **Rate limit sull'endpoint Transaction Log** ridotto da 50 a 30 richieste/secondo per user ID (5 febbraio 2026) — rilevante solo se si costruisce un job di riconciliazione fee ad alta frequenza (sconsigliato comunque, coerente con l'approccio già usato per OKX con cache/backoff).
- Ordini su **XAU/XAG perpetual** richiedono un endpoint di accettazione contrattuale dedicato prima di poter tradare — non rilevante per lo scalping spot pianificato, ma da tenere a mente se in futuro si guardasse ai derivati.

---

## 4. Modello Account — passaggio preliminare obbligatorio

Come per OKX (account mode Spot/Futures/Multi-currency margin), Bybit richiede la scelta tra:
- **Account Classic** (legacy, per-prodotto separato)
- **Unified Trading Account (UTA)** — l'equivalente concettuale del "Trading Account unificato" di OKX, dove spot/derivati/opzioni condividono lo stesso margine.

**Azione pratica:** verificare via `GET /v5/account/wallet-balance` con `accountType=UNIFIED` se l'account è già in UTA. Molte integrazioni di terze parti (3Commas, Bitsgap) richiedono esplicitamente UTA per funzionare — verificarlo anche per il nostro caso, dato che SynthTrade opera solo spot e un errore di account mode è una causa comune di 401/10001 generici.

---

## 5. Market Data — Instrument Discovery

Endpoint: `GET /v5/market/instruments-info?category=spot`

Restituisce, per ogni simbolo spot: `symbol`, `status` (`Trading`/`Closed`/...), `baseCoin`, `quoteCoin`, `lotSizeFilter` (`basePrecision`, `quotePrecision`, `minOrderQty`, `maxOrderQty`, `minOrderAmt`, `maxOrderAmt`), `priceFilter` (`tickSize`).

**Analogia con il modello OKX già implementato:** il nostro `ExchangeAdapterProtocol.get_symbol_rules()` esistente (da `okx-migration-architecture.md` §3) mappa concettualmente 1:1 su questi campi — `lotSz→basePrecision`, `minSz→minOrderQty`, `tickSz→tickSize`, `maxMktAmt→maxOrderAmt`. Il refactor per Bybit userà lo stesso `SymbolRules` dataclass già esistente in `exchange_models.py`, solo con un parser diverso.

**Simbolo di riferimento:** Bybit usa simboli concatenati senza separatore (`BTCUSDT`, `BTCEUR` se disponibile), diversamente da OKX (`BTC-EUR`) e più vicino al formato Binance originale (`BTCUSDC`). Questo **semplifica** la normalizzazione rispetto a OKX: se Bybit espone coppie EUR dirette (da verificare — la liquidità EUR su Bybit è storicamente più bassa di quella USDT), il nostro `SymbolRef.compact` esistente può mappare quasi 1:1 senza bisogno del parsing con trattino introdotto per OKX.

**Da verificare nello spike:** quali coppie EUR sono realmente quotate e liquide su Bybit spot (candidate: `BTCEUR`, `ETHEUR`, `USDTEUR` se esiste) — oppure se conviene restare su una coppia USDT (es. `BTCUSDT`) e gestire la conversione EUR solo a livello di dashboard/reportistica, come già previsto concettualmente in `okx-migration-architecture.md` §9 per il balance provider-neutral.

---

## 6. Piazzare Ordini — Spot

Endpoint unico: `POST /v5/order/create` con `category=spot`.

| Campo | Valori | Note |
|---|---|---|
| `category` | `spot` | Distingue spot da linear/inverse/option nello stesso endpoint unificato |
| `symbol` | es. `BTCUSDT` | Nessun trattino, a differenza di OKX |
| `side` | `Buy` / `Sell` | Notare il casing PascalCase, diverso sia da Binance (`BUY`/`SELL`) che da OKX (`buy`/`sell`) — punto di attenzione per il refactor dell'adapter |
| `orderType` | `Market` / `Limit` | |
| `qty` | quantità | Per market **buy**, Bybit converte automaticamente in IOC limit order per protezione da slippage; verificare comportamento equivalente al `tgtCcy=quote_ccy` di OKX per comprare a budget in quote currency — parametro `marketUnit: baseCoin|quoteCoin` (aggiunto in un changelog recente) sembra essere l'equivalente diretto |
| `price` | solo per limit | |
| `timeInForce` | `GTC` / `IOC` / `FOK` / `PostOnly` | |
| `orderLinkId` | ID cliente custom, max 36 caratteri | Analogo a `clOrdId` — utile per idempotenza e per matching lato nostro sistema |

**Nota importante sul market order:** Bybit converte gli ordini market in un IOC limit order interno per protezione da slippage eccessivo; se non ci sono livelli di order book entro la soglia di slippage, l'ordine può risultare parzialmente o per nulla eseguito. Da verificare empiricamente l'impatto su simboli a bassa liquidità (es. eventuali coppie EUR).

---

## 7. TP/SL e OCO — modello Bybit Spot (UTA)

Questo è il punto architetturalmente più vicino a ciò che serve a SynthTrade (equivalente all'OCO nativo Binance e all'`order-algo` OKX).

Dalla documentazione e changelog v5, il modello Bybit per Spot (UTA) espone tre concetti tramite il campo `stopOrderType`:

| `stopOrderType` | Significato |
|---|---|
| `""` (vuoto) | Ordine normale |
| `tpslOrder` | Ordine TP/SL singolo (non OCO) |
| `Stop` | Ordine condizionale (conditional order) |
| `OcoOrder` | **OCO nativo Spot** — introdotto specificamente per Unified Trading Account |

Esiste inoltre il campo di risposta `ocoTriggerBy` con valori `OcoTriggerByUnknown` / `OcoTriggerByTp` / `OcoTriggerBySl`, che indica quale gamba dell'OCO ha innescato l'esecuzione — l'equivalente diretto del campo `leg` che abbiamo già introdotto in modo provider-neutral per OKX (`take_profit`/`stop_loss`) in `_on_order_update`.

**Somiglianza forte con Binance nativo:** a differenza di OKX (dove serve un endpoint `/trade/order-algo` separato dall'ordine principale), il modello Bybit Spot OCO sembra concettualmente più vicino a quello che SynthTrade già conosce da Binance (`place_oco_order`) — un singolo ordine composito con due gambe collegate, non un ordine "algo" indipendente. Questo potrebbe **ridurre il refactor rispetto a quanto fatto per OKX**, se confermato dallo spike.

**Comportamento su TP/SL Limit (rilevante per il rischio di esecuzione):** la documentazione Bybit segnala esplicitamente che se si usano ordini TP/SL di tipo Limit (non Market) sullo spot, la gamba opposta viene cancellata immediatamente al trigger dell'altra, **anche se l'ordine Limit non è ancora stato riempito** — in caso di rimbalzo di prezzo, si rischia di restare scoperti (né TP né SL attivi). **Raccomandazione:** usare TP/SL come ordini **Market** al trigger (non Limit), coerente con la scelta già fatta per OKX (`tpOrdPx="-1"`/`slOrdPx="-1"` = market a trigger).

**Da verificare nello spike (equivalente a TASK-1100.F per OKX):**
1. Se l'OCO Spot va creato con un parametro dedicato in `POST /v5/order/create` (es. `orderFilter=OcoOrder` o simile) oppure con un endpoint separato.
2. Se il posizionamento del TP/SL è "attached" all'ordine di apertura (come `attachAlgoOrds` di OKX) o indipendente (come il flusso attuale SynthTrade, che apre prima il market buy e poi piazza l'OCO separatamente) — la nostra architettura attuale presuppone il secondo modello, quindi va confermato che Bybit lo supporti altrettanto bene.
3. Limiti minimi di quantità/importo per un OCO spot (equivalente al `minSz` OKX per il bracket).

---

## 8. WebSocket — canali rilevanti per SynthTrade

Bybit v5 usa **tre famiglie di endpoint WS** distinte, analogamente a OKX ma con nomi diversi:

| Endpoint | Uso | Autenticazione |
|---|---|---|
| `wss://stream.bybit.com/v5/public/spot` | Market data pubblico: `orderbook`, `publicTrade`, `kline`, `tickers` | Nessuna |
| `wss://stream.bybit.com/v5/private` | Account, ordini (`order` topic), esecuzioni (`execution` topic), wallet | Login richiesto (messaggio `auth` con firma) |
| `wss://stream.bybit.com/v5/trade` | **WebSocket Trade API** — permette di piazzare/modificare/cancellare ordini via WS invece che REST | Login richiesto |

**Differenza architetturale importante rispetto a OKX:** su OKX gli aggiornamenti degli ordini "algo" (TP/SL/OCO) vivono su un WS **business** separato da quello privato standard — punto che ci ha causato un bug reale (TASK-1100.G, evento fill mai ricevuto perché si ascoltava il canale sbagliato). **Su Bybit, secondo la documentazione consultata, sia gli ordini normali sia gli ordini TP/SL/OCO/condizionali sembrano transitare sullo stesso topic privato `order`** (il campo `stopOrderType` nel payload distingue il tipo, non serve un canale diverso). Questo, se confermato, elimina un'intera classe di bug già vista su OKX — ma **va confermato empiricamente con un OCO spot reale in demo/testnet prima di dare per assodato**, esattamente come fatto per il payload OKX in `okx-demo-spike-results.md`.

### 8.1 Canale `publicTrade` (per CVD)

Payload osservato (canale pubblico, nessuna autenticazione):

```json
{
  "topic": "publicTrade.BTCUSDT",
  "type": "snapshot",
  "ts": 1672304486868,
  "data": [
    {
      "T": 1672304486865,
      "s": "BTCUSDT",
      "S": "Buy",
      "v": "0.001",
      "p": "16578.50",
      "L": "PlusTick",
      "i": "20f43950-d8dd-5b31-9112-a178eb6023af",
      "BT": false
    }
  ]
}
```

Il campo `S` (`Buy`/`Sell`) rappresenta il lato del trade. **Da verificare empiricamente se `S` rappresenta il lato del taker** (come richiesto dal nostro `CVDCalculator`, che ha bisogno di sapere se il trade è stato un buy aggressivo o un sell aggressivo) — la convenzione generale sugli exchange (inclusi altri progetti che integrano Bybit, es. `tardis-node`) mappa `S=="Buy"` a un trade taker-buy. Non dare per scontato senza un test diretto sul book reale, stesso principio già applicato per il campo `side` di OKX.

### 8.2 Canale `order` e `execution` (privati)

Il topic `order` (WS privato) restituisce eventi con `stopOrderType` e (per Spot UTA) `ocoTriggerBy` — sufficienti per determinare se un fill riguarda la gamba TP o SL di un OCO, analogamente al campo `leg` già introdotto per OKX in `_on_order_update`.

Il topic `execution` fornisce il dettaglio del fill (prezzo, quantità, fee, `execFee`, `feeRate`) — utile per popolare `commission`/`commission_asset` come già fatto per Binance/OKX.

### 8.3 WebSocket Trade API (`/v5/trade`)

Bybit offre la possibilità di piazzare/modificare/cancellare ordini **direttamente via WebSocket** invece che REST, con un modello richiesta/risposta simile a REST ma su socket persistente. Questo **non è disponibile su OKX né era mai stato usato per Binance** nel nostro progetto — è un'opzione aggiuntiva, non un requisito. Per il primo porting, mantenere il flusso REST classico (`place_market_order`, poi bracket) per limitare il numero di variabili nuove introdotte in un colpo solo (coerente con "one change at a time"); valutare la Trade WS API come ottimizzazione di latenza in una fase successiva, se la latenza REST risultasse un collo di bottiglia reale per lo scalping.

### 8.4 Rate limit e keep-alive WS

- Ping/pong ogni 20 secondi raccomandato per mantenere la connessione pubblica attiva; se non c'è traffico né ping/pong per 10 minuti la connessione viene chiusa.
- Parametro opzionale `max_active_time` per il WS privato.
- Lunghezza massima argomenti di sottoscrizione non specificata come vincolo stringente nella ricerca — verificare se necessario per il numero di canali che useremo (contenuto, analogo a OKX).

---

## 9. Fee — dettaglio e confronto con OKX

| Mercato | Maker (non-VIP) | Taker (non-VIP) | Note |
|---|---|---|---|
| Spot (standard) | 0.10% | 0.10% | Nessun rebate a questo tier, a differenza di OKX Demo (-0.2%/-0.35%) |
| Spot USDC-denominato (VIP Supreme, dal 23/03/2026) | fino a 0.0225% | fino a 0.0225% | Solo per tier VIP alti, non applicabile a un account nuovo |
| Sconto con token nativo BIT | fino al 25% aggiuntivo | fino al 25% aggiuntivo | Da valutare se conveniente detenere BIT solo per lo sconto fee |

**Endpoint per leggere il fee tier reale dell'account:** `GET /v5/account/fee-rate?category=spot&symbol=BTCUSDT` — equivalente diretto di `GET /api/v5/account/trade-fee` su OKX, già usato per certificare `fee_tier_certified` nel nostro flusso. Va chiamato all'avvio sessione, esattamente come `get_trade_fee()` esistente, e il risultato deve **sempre** essere usato al posto di assunzioni hardcoded.

**Conclusione fee (aggiornabile solo dopo lo spike):** allo stato attuale della ricerca, il fee spot standard di Bybit (0.10%/0.10%, round-trip 0.20%) **non risolve automaticamente** il problema economico che ha spinto Andrea a lasciare OKX, a meno che: (a) l'account abbia già/possa ottenere uno sconto VIP o via referral; (b) l'obiettivo reale non sia "fee più basse in assoluto" ma "fee **prevedibili e non-rebate**" (il rebate OKX, pur numericamente favorevole sulla carta, potrebbe comportarsi in modo diverso a seconda del tipo di ordine reale eseguito — market vs limit — cosa che nella sessione OKX live potrebbe non aver funzionato come nello spike Demo). **Il primo output pratico dello spike Bybit deve essere una tabella comparativa reale (fee OKX effettivamente pagate sull'ultimo trade live vs fee Bybit sul primo trade demo) prima di continuare con il resto della migrazione.**

---

## 10. Rate limit REST

- Header standard `X-RateLimit-*` e `Retry-After` per il throttling.
- Bybit applica un limite giornaliero aggregato sul numero di ordini per utente (main + subaccount), con warning/restrizioni oltre soglia — non documentato con un numero fisso nella ricerca, verificare nel pannello account.
- Placement ordini via API SDK ufficiali gode di rate limit più alti (400 req/sec dichiarati per l'SDK Node.js ufficiale) — non rilevante se si chiama REST direttamente senza SDK, da tenere a mente se si valutasse di adottare un SDK ufficiale (`pybit` per Python) invece di chiamate HTTP dirette.
- Per lo scalping a 1 minuto con poche chiamate per ciclo, questo limite non dovrebbe mai essere un problema — stesso principio già applicato per OKX.

---

## 11. Mappatura concettuale OKX -> Bybit (per il refactor)

| OKX (attuale) | Bybit (da usare) | Note |
|---|---|---|
| `https://eea.okx.com` + header `x-simulated-trading` | `https://api.bybit.eu` (**da verificare se accessibile per trading custom**) o `https://api.bybit.com`/`api-testnet.bybit.com` per test | Punto critico #1 di questo documento |
| Header auth: `OK-ACCESS-KEY/SIGN/TIMESTAMP/PASSPHRASE` | Header auth: `X-BAPI-API-KEY/SIGN/TIMESTAMP/RECV-WINDOW` | Bybit non richiede passphrase |
| `instId` con trattino (`BTC-EUR`) | `symbol` concatenato (`BTCUSDT`) | Simbolo Bybit più vicino al formato Binance già noto |
| `tdMode=cash` (spot puro) | `category=spot` nell'endpoint unificato | |
| `side: buy/sell` (lowercase) | `side: Buy/Sell` (PascalCase) | Attenzione nel mapping enum |
| `order-algo` con `tpTriggerPx`/`slTriggerPx` | `stopOrderType=OcoOrder` sullo stesso `order/create` (da confermare) | Possibile semplificazione: un solo endpoint invece di due |
| WS business per fill algo (`/ws/v5/business`) | Stesso topic `order` privato per ordini normali e OCO (da confermare) | Possibile eliminazione di un'intera classe di bug simbolo/canale |
| WS trades pubblico, campo lato taker da verificare | `publicTrade`, campo `S`, da verificare | Stessa cautela |
| Fee rebate -0.2%/-0.35% (Demo) | Fee 0.10%/0.10% standard (da verificare tier reale account) | Vedi §9 — punto centrale della migrazione |
| `GET /api/v5/account/trade-fee` | `GET /v5/account/fee-rate` | Stesso ruolo, stesso obbligo di certificazione (`fee_tier_certified`) |
| WS private EU bloccato (60032), workaround REST polling | **Accesso API custom EU potenzialmente bloccato del tutto** | Rischio strutturalmente più alto, va chiuso PRIMA di scrivere adapter |

---

## 12. Cose da NON dare per assodate — verificare empiricamente prima di scrivere codice definitivo

1. **[BLOCCANTE]** Se un account Bybit EU (`bybit.eu`, dominio MiCA) può generare una API key HMAC utilizzabile da un client custom per trading Spot automatizzato, oppure se l'accesso è ristretto solo ad app whitelistate ("Connect to Third-Party Applications").
2. Se, in assenza del punto 1, esiste un percorso legale alternativo (es. entità non-EU con onboarding per residenti italiani, o un cambio di framework normativo nel frattempo) — da NON assumere, da verificare con la UI Bybit reale.
3. Il fee tier realmente applicato al nuovo account (non VIP di default) e se è competitivo rispetto al problema economico di partenza.
4. La forma esatta dei parametri per l'OCO Spot su `POST /v5/order/create` (nome esatto del parametro, se serve un `orderFilter` dedicato, se il TP/SL è attached o standalone).
5. Se il topic WS `order` privato riceve davvero sia ordini normali sia OCO/TP-SL senza bisogno di un canale separato (da confermare con un OCO reale in demo/testnet).
6. Il campo esatto che identifica il lato taker in `publicTrade` (per il calcolo CVD).
7. Se `marketUnit=quoteCoin` sui market order Spot funziona in modo equivalente a `tgtCcy=quote_ccy` di OKX per comprare "a budget" invece che "a quantità".
8. Se il testnet Bybit (`api-testnet.bybit.com`) espone davvero le stesse coppie/comportamenti del mainnet EU, o se — come già visto su OKX Demo — alcuni simboli/comportamenti differiscono tra ambiente di test e produzione (es. OKB-EUR non disponibile in Demo ma live su OKX).
9. Se esistono coppie **EUR** dirette con liquidità sufficiente su Bybit spot, o se conviene operare su una coppia USDT/USDC gestendo la conversione EUR solo lato dashboard (come già fatto concettualmente per OKX in `okx-migration-architecture.md` §9).

**Suggerimento pratico (stesso principio già seguito per OKX):** prima ancora di toccare `router.py`, scrivere uno script isolato (`scripts/test_bybit_demo.py`, fuori da SynthTrade) che: crea/usa API key Bybit EU (o testnet, se EU risultasse bloccato), fa un ordine market minimo con TP/SL, ascolta il fill sul canale giusto, e soprattutto **verifica il fee tier reale e il punto critico #1 di questo documento prima di qualunque altra cosa**. Solo dopo aver confermato tutti i punti sopra con osservazione diretta, portare quel comportamento confermato dentro l'architettura vera — stesso principio già seguito per lo spike OKX (`docs/analysis/okx-demo-spike-results.md`).

---

## 13. Prossimi passi quando si riprende il codice

1. Verificare il punto critico #1 (accesso API custom su Bybit EU) — se bloccante, l'intera migrazione si ferma qui e va rivalutata l'opzione exchange.
2. Se sbloccato: creare API key (EU o testnet), verificare i 9 punti della sezione 12 con uno script isolato.
3. Confrontare il fee tier reale Bybit con l'ultimo dato Fee OKX osservato in produzione, per confermare che il cambio risolva davvero il problema economico di partenza.
4. Decidere se serve ancora un "WalletOrchestrator"-equivalente (probabilmente no, dato che Bybit UTA è un conto unificato come OKX, non un modello multi-wallet come Binance) — coerente con la nota già presente in `okx-migration-architecture.md` §6 sullo short/margin.
5. Riscrivere/estendere `ExchangeAdapterProtocol` (già astratto e provider-neutral da TASK-1102) con un nuovo `BybitExchangeAdapter`, seguendo la stessa disciplina già applicata per `OkxExchangeAdapter` — nessun porting 1:1, semantica Bybit propria.
6. Aggiornare i task esistenti — vedi `bybit-migration-implementation-plan.md` per il breakdown operativo.

---

Fonti: documentazione ufficiale Bybit (`bybit-exchange.github.io/docs/v5`), changelog v5, help center Bybit, SDK ufficiali (`pybit`, `bybit-api` Node.js), documentazione di integrazione di terze parti (3Commas) usata come prova indiretta del comportamento reale dell'account EU. Trattare come punto di partenza solido ma non infallibile — verificare sempre la versione più recente su `bybit-exchange.github.io/docs/v5` prima dell'implementazione finale, e non fidarsi di articoli di terze parti per i punti bloccanti (solo la doc ufficiale + un test empirico diretto contano per la decisione finale sul punto critico #1).
