# SynthTrade — Architettura e Piano di Migrazione OKX -> Bybit EU

> Data: 11 luglio 2026
> Stato: bozza per pianificazione, da validare con spike Bybit EU/Demo prima di qualunque codice live
> Riferimento tecnico: `bybit-api-reference-analysis.md` (leggere PRIMA di questo documento)
> Scope: sostituire OKX come exchange operativo per lo scalping live, mantenendo l'architettura provider-neutral già introdotta con la migrazione Binance -> OKX (`docs/architecture/okx-migration-architecture.md`)

---

## 0. Perché questa migrazione e cosa NON rifare da zero

Il motivo della migrazione è **economico, non normativo**: su OKX lo Stop Loss configurato allo 0.3% viene eroso dalle fee al punto da rendere lo scalping non sostenibile.

### 0.1 Dato empirico reale (11/07/2026, screenshot pannelli fee ufficiali) — sostituisce ogni stima precedente

**OKX — pannello "Il mio livello di commissioni", tier "Utente regolare":**

| | Maker | Taker |
|---|---|---|
| Spot | 0,20% | 0,35% |

Questo è il dato **reale** applicato all'account, e smentisce lo scenario di rebate (-0,20%/-0,35%) osservato nello spike Demo Trading (`okx-demo-spike-results.md`) — quel rebate era evidentemente un artefatto dell'ambiente Demo, mai applicato al conto live. Confermato anche via query Supabase su `scalping_sessions`/`scalping_trades`: **63 trade reali su 69** hanno registrato `fee_tier_maker/taker = 0.001/0.001` (fallback hardcoded, non certificato correttamente), solo 1 trade ha visto il rebate demo. La certificazione del fee tier (`fee_tier_certified`) andrebbe comunque rivista per OKX, ma il dato di riferimento per il confronto economico è quello dello screenshot: **0,20% maker / 0,35% taker**.

**Bybit EU — pannello "I miei tassi di commissione" (`bybit.eu/it-EU/my-fee-rate`), tier "Utente regolare":**

| | Maker | Taker |
|---|---|---|
| Spot (crypto/crypto) | 0,10% | 0,25% |
| Coppie Fiat (es. EUR) | 0,15% | 0,25% |

### 0.2 Calcolo R (round-trip fee) — flusso attuale (entry market + exit market al trigger)

Il flusso SynthTrade oggi apre sempre a **market** (taker) e chiude il TP/SL **a market al trigger** (taker), sia per OKX sia per il porting Bybit pianificato (per evitare il rischio, documentato da Bybit stesso, che una gamba TP/SL Limit venga cancellata prima di essere riempita). Quindi il costo di round-trip realistico è **doppia fee taker**:

| Exchange | Fee taker | R round-trip (taker+taker) |
|---|---|---|
| OKX (reale, screenshot) | 0,35% | **0,70%** |
| Bybit EU (reale, screenshot, spot crypto/crypto) | 0,25% | **0,50%** |

**Miglioramento reale passando a Bybit: -29% sul costo fisso di round-trip** (da 0,70% a 0,50%). Non è la riduzione drastica che una fee generica da 0,10%/0,10% avrebbe suggerito, ma è un miglioramento concreto, misurabile e sufficiente a giustificare la migrazione — con l'avvertenza che **non elimina la tensione strutturale tra scalping stretto e fee**, la attenua soltanto. Vedi §0.3 per un'ottimizzazione aggiuntiva non ancora implementata che potrebbe ridurre ulteriormente R.

### 0.3 Leva aggiuntiva non ancora sfruttata: entry a maker invece che a market

Su entrambi gli exchange il differenziale maker/taker è ampio (OKX: 0,20% vs 0,35%, rapporto 1,75x; Bybit: 0,10% vs 0,25%, rapporto 2,5x). Il flusso attuale usa sempre un market buy per l'apertura. Se l'ordine di apertura venisse piazzato come **limit/post-only** (accettando il rischio di non-fill se il prezzo si muove prima del riempimento), il costo scenderebbe a:

- OKX: R = 0,20% (entry maker) + 0,35% (exit taker) = **0,55%**
- Bybit: R = 0,10% (entry maker) + 0,25% (exit taker) = **0,35%**

Questo è un cambio architetturale non banale (oggi `place_market_order` assume sempre esecuzione immediata) e va trattato come task separato successivo al primo porting Bybit, non incluso nella Fase 0-1. Va menzionato qui perché rappresenta la leva più efficace per riavvicinare il sistema a un vero scalping, più della sola scelta dell'exchange.

### 0.4 SL/TP ricalcolati con R reale (flusso attuale, nessun cambio architetturale)

Con R_bybit = 0,50% (scenario base, entry+exit taker):

| Opzione | SL netto | TP netto | Distanza lorda SL | Distanza lorda TP | R:R netto |
|---|---|---|---|---|---|
| A — minimo fattibile | 0,60% | 0,70% | 0,10% | 1,20% | 1,17:1 |
| **B — consigliata per il primo test** | 0,75% | 1,10% | 0,25% | 1,60% | 1,47:1 |
| C — più margine di sicurezza | 0,90% | 1,40% | 0,40% | 1,90% | 1,56:1 |

Per confronto, con R_okx = 0,70% reale (verificato, non lo scenario ipotetico precedente), gli stessi livelli di sicurezza avrebbero richiesto SL netto ≥1,0% e TP netto ≥1,3-1,5% — molto più lontano dal concetto di scalping di quanto richiesto su Bybit.

Se in futuro si implementasse l'entry a maker (§0.3, R_bybit=0,35%), l'opzione B diventerebbe SL lordo 0,40% / TP lordo 1,45% — leggermente meno estrema, a parità di target netti.

**Conclusione onesta:** il passaggio a Bybit aiuta concretamente (-29% di costo fisso per trade rispetto a OKX) ma non è una soluzione magica — attenua la tensione tra fee e scalping stretto, non la elimina. Va comunque accompagnato da un aggiustamento di SL/TP rispetto ai valori originali (0,3%/0,5%) e, in una fase successiva, dalla valutazione dell'entry a maker (§0.3) e/o del trailing stop loss già in backlog (`docs/recap/2026-06-26_trailing-stop-loss.md`) come alternativa strutturale al TP fisso lontano.

**Buona notizia architetturale:** la migrazione Binance -> OKX (TASK-1100 -> TASK-1116, completata) ha già introdotto un intero layer **exchange pluggable**:

- `ExchangeAdapterProtocol` in `exchange_models.py` — interfaccia astratta (`place_market_order`, `place_exit_bracket`, `get_symbol_rules`, `get_trade_fee`, `close_position`, `get_open_exit_orders`, `cancel_open_exit_orders`, ecc.)
- Modelli di dominio provider-neutral: `SymbolRef`, `SymbolRules`, `MarketOrderRequest`, `ExitBracketRequest`, `ExchangeOrder`, `ExitBracketOrder`, `FeeTier`
- `MarketDataWSProtocol` e `OrderEventStreamProtocol` come interfacce per WS market data e WS fill/ordini
- `exchange_factory.py` con dispatch provider-aware (`get_adapter()`, `get_market_ws_client()`, `get_order_event_stream()`)
- Router scalping (`router.py`) già reso **completamente provider-neutral** in TASK-1107 (100%) — nessuna assunzione Binance/OKX-specifica residua nel ciclo sessione
- DB già esteso con colonne generiche (`exchange_provider`, `exchange_order_id`, `exchange_bracket_id`, `exchange_tp/sl_order_id`, `exchange_raw`, `fee_tier_certified`) in TASK-1108
- Frontend già parzialmente exchange-neutral (TASK-1109, TASK-1115)

**Conseguenza pratica per Bybit:** questa migrazione **non ripete il lavoro architetturale** già fatto per OKX. Il grosso del lavoro si riduce a:

1. Uno spike Bybit EU/Demo (equivalente a TASK-1100), con un focus aggiuntivo critico sul punto di accesso API EU (vedi `bybit-api-reference-analysis.md` §1) e sulla verifica del fee tier reale.
2. Un nuovo `BybitExchangeAdapter` che implementa lo stesso `ExchangeAdapterProtocol` già esistente.
3. Un nuovo `BybitWSClient` (market data) e `BybitOrderEventStream` (fill TP/SL), sullo stesso modello di `OkxWSClient`/`OkxOrderEventStream`.
4. Aggiornamento della factory e della config per aggiungere `EXCHANGE_PROVIDER=bybit` accanto a `okx` (Binance e OKX restano leggibili come legacy, non vanno rimossi).
5. Audit dei collector di Signal Intelligence (stesso lavoro già fatto in TASK-1116 per OKX) per verificare cosa Bybit espone nativamente (funding rate derivati, se rilevante) e cosa va disabilitato/gestito come graceful skip.
6. DB: aggiungere `bybit` come nuovo valore possibile di `exchange_provider` (nessuna nuova colonna strutturale necessaria, sono già generiche).

**Cosa NON toccare:** short selling (resta sospeso, come già deciso per OKX — Bybit UTA supporta margin trading in modo simile a OKX con margine unificato, ma resta fuori scope per la prima release, esattamente come deciso in `okx-migration-architecture.md` §5.3).

---

## 1. Decisione Architetturale

1. Bybit diventa il **secondo provider aggiuntivo** nel layer pluggable già esistente — non sostituisce OKX nel codice, lo affianca. `EXCHANGE_PROVIDER` può valere `binance` (legacy), `okx` (legacy operativo se il problema fee si rivelasse non risolvibile diversamente), `bybit` (nuovo target).
2. Nessun porting 1:1 da OKX: Bybit ha semantiche proprie (simboli senza trattino, OCO Spot nativo probabilmente più vicino a Binance, un solo canale WS privato per ordini normali e TP/SL invece di due separati come OKX).
3. Il gate economico (fee reali, verifica se lo SL 0.3% torna sostenibile) è **bloccante e va risolto per primo**, prima di investire tempo nel resto del porting — a differenza di OKX, dove il gate bloccante iniziale era tecnico (auth EU), qui il gate bloccante iniziale è sia tecnico (accesso API EU) **sia economico** (le fee davvero risolvono il problema?).
4. Se il punto critico #1 di `bybit-api-reference-analysis.md` (accesso API custom bloccato per account Bybit EU retail) si conferma vero e non aggirabile, questa migrazione si ferma alla Fase 0 e va rivalutata l'intera strategia (es. rinegoziare i parametri di rischio su OKX allargando SL/TP, invece di cambiare ancora exchange).

---

## 2. Vincoli e rischi specifici di Bybit (in aggiunta a quanto già gestito per OKX)

| Area | Rischio | Mitigazione |
|---|---|---|
| Accesso API EU | Bloccante potenziale totale (non solo WS come su OKX) | Spike Fase 0 obbligatorio prima di qualunque altro task |
| Fee reali | Potrebbero non risolvere il problema economico di partenza | Confronto numerico esplicito OKX vs Bybit prima di proseguire (Fase 0) |
| Nuovo account (48h lock) | Se l'account Bybit è nuovo, la generazione della API key è bloccata per le prime 48 ore | Pianificare il tempo di attesa, non è un bug del nostro codice |
| Simbolo EUR liquidità | Le coppie EUR dirette potrebbero avere poca liquidità su Bybit (come già visto: OKX Demo ha liquidità EUR limitata) | Verificare nello spike; fallback su coppia USDT/USDC con conversione EUR solo lato dashboard |
| OCO Spot ancora "giovane" nell'API (introdotto di recente nel changelog v5) | Possibili comportamenti non ancora ben documentati o bug lato Bybit | Test isolato con quantità minima prima di integrare nel router |
| IP whitelist non più modificabile via API (dal 10/02/2026) | Se si pensa di automatizzare rotazione chiavi, non è più possibile | Gestire whitelist manualmente da browser, documentarlo nel runbook |

---

## 3. Provider Model — estensione della configurazione esistente

### 3.1 Configurazione

Estendere `.env` / `config.py` con lo stesso pattern già usato per OKX:

```env
EXCHANGE_PROVIDER=bybit          # invece di okx, quando la migrazione è confermata
TRADING_MODE=test                # test = Bybit testnet/demo, live = mainnet reale

BYBIT_API_KEY=
BYBIT_SECRET_KEY=
BYBIT_BASE_URL=https://api.bybit.eu     # o https://api-testnet.bybit.com per test iniziali

BYBIT_API_KEY_LIVE=
BYBIT_SECRET_KEY_LIVE=

ALLOW_LIVE_MODE=false
```

Note:
- **Nessuna passphrase** richiesta (a differenza di `OKX_PASSPHRASE`) — un campo di configurazione in meno.
- `BYBIT_BASE_URL` deve poter puntare sia a `api.bybit.eu` (mainnet EU, se sbloccato) sia a `api-testnet.bybit.com` (test), sia eventualmente a `api.bybit.com` (globale, se l'account EU risultasse bloccato e si scegliesse comunque — da NON fare senza verifica di conformità normativa, solo come nota tecnica).
- Computed fields generici già esistenti (`exchange_provider`, `exchange_api_key`, ecc. da TASK-1101) vanno solo estesi con un nuovo branch `if provider == "bybit"`, stesso pattern di `okx`.

### 3.2 Interfacce — nessuna nuova interfaccia, solo nuova implementazione

Il protocollo `ExchangeAdapterProtocol` (giа definito in TASK-1102) resta invariato. Serve solo `BybitExchangeAdapter` che lo implementi:

```python
class BybitExchangeAdapterProtocol:  # implementa ExchangeAdapterProtocol
    provider: str = "bybit"
    trading_mode: str

    async def get_balance(self, asset: str) -> float: ...
    async def get_holdings(self) -> dict[str, float]: ...
    async def get_ticker_price(self, symbol: str) -> float: ...
    async def get_symbol_rules(self, symbol: SymbolRef) -> SymbolRules: ...
    async def place_market_order(self, request: MarketOrderRequest) -> ExchangeOrder: ...
    async def close_position(self, request: ClosePositionRequest) -> ExchangeOrder: ...
    async def place_exit_bracket(self, request: ExitBracketRequest) -> ExitBracketOrder: ...
    async def get_open_exit_orders(self, symbol: SymbolRef) -> list[ExchangeOrder]: ...
    async def cancel_open_exit_orders(self, symbol: SymbolRef) -> None: ...
    async def get_trade_fee(self, symbol: SymbolRef) -> FeeTier: ...
```

`place_exit_bracket()` per Bybit mappa (in base allo spike) su `POST /v5/order/create` con `stopOrderType=OcoOrder` (se confermato "attached" nello stesso endpoint) oppure su un endpoint dedicato se lo spike rivela il contrario.

---

## 4. Symbol Model

Bybit usa simboli concatenati senza separatore (`BTCUSDT`), lo stesso formato compatto già usato internamente da SynthTrade (`SymbolRef.compact`). Questo **semplifica** rispetto a OKX, dove serviva un parser dedicato per il trattino (`BTC-EUR`).

```python
symbol = SymbolRef.from_any("BTCUSDT")
symbol.bybit    # -> "BTCUSDT" (nuovo metodo, identico a .compact per Bybit)
symbol.ccxt     # -> "BTC/USDT" (se si usa ccxt come libreria di supporto)
```

**Instrument discovery obbligatoria (stesso principio già applicato per OKX, TASK-1116.G):** non assumere che una coppia esista solo perché configurata. All'avvio sessione, interrogare:

```text
GET /v5/market/instruments-info?category=spot
```

Filtrare per `status=Trading`, usare `lotSizeFilter`/`priceFilter` per quantity/price rules, e — punto critico — **verificare se esistono coppie EUR dirette con liquidità sufficiente**, oppure se conviene restare su una coppia USDT (es. `BTCUSDT`) con conversione EUR solo lato dashboard/report (stesso pattern già usato per il balance provider-neutral OKX in `okx-migration-architecture.md` §9).

---

## 5. Bybit Trading Model

### 5.0 Fee Tier, Net Pricing e PnL — requisito bloccante numero 1

Esattamente come per OKX (`okx-migration-architecture.md` §5.0), il comportamento di recupero fee tier a inizio sessione e trasformazione target netti -> prezzi lordi (`_net_to_gross_pct`) è **obbligatorio** anche per Bybit, con un'aggiunta specifica per questa migrazione:

- `BybitExchangeAdapter.get_trade_fee(symbol)` deve chiamare `GET /v5/account/fee-rate?category=spot&symbol=...` e popolare `FeeTier(maker, taker, certified=True, raw=..., source="bybit")`.
- **Sia OKX sia Bybit hanno fee standard positive per l'account "Utente regolare"** (confermato via screenshot §0.1: OKX 0,20%/0,35%, Bybit 0,10%/0,25% spot crypto — nessun rebate reale su nessuno dei due). Il codice `abs()` introdotto per gestire l'ipotesi di rebate OKX in `_net_to_gross_pct` (TASK-1111 bug fix) resta comunque utile come guardia difensiva ma diventa un no-op nella pratica per entrambi gli exchange con questo tier. Va **testato esplicitamente** che il calcolo funzioni identico con segno positivo.
- **Prerequisito bloccante prima di aprire qualunque trade reale:** con R_bybit=0,50% (§0.2), lo SL originale a 0.3% netto **non è economicamente sostenibile** (distanza lorda negativa, stesso problema già riscontrato su OKX) — va aggiornato almeno alle soglie indicate in §0.4 (opzione B: SL netto 0,75% / TP netto 1,10%) prima di qualunque sessione live. Il fee tier reale va comunque ri-certificato (`fee_tier_certified=True`) via `GET /v5/account/fee-rate` all'avvio di ogni sessione — non fidarsi del solo screenshot statico, che può cambiare con il volume di trading (VIP tier) o con eventuali sconti futuri (BIT token).

### 5.1 Spot Long

Flusso equivalente all'attuale (OKX/Binance):

```text
Segnale BUY approvato
  -> place_market_order(category=spot, side=Buy)
  -> place_exit_bracket(side=Sell, tp sopra entry, sl sotto entry)
  -> salva posizione solo dopo bracket confermato
  -> ascolta evento fill bracket (WS privato, topic "order")
  -> chiudi posizione in memoria + DB + broadcast UI
```

`place_market_order` deve gestire l'equivalente di `tgtCcy=quote_ccy` (comprare "a budget" invece che "a quantità") — probabile candidato: parametro `marketUnit=quoteCoin` osservato nel changelog v5. Da confermare nello spike prima di assumerlo funzionante.

### 5.2 Exit Bracket / OCO Spot

Principio invariato (stesso di OKX/Binance): nessuna posizione live deve restare aperta senza protezione server-side.

Decisione provvisoria in attesa di spike: usare l'OCO Spot nativo Bybit (`stopOrderType=OcoOrder`), **con TP/SL configurati come ordini Market al trigger** (non Limit) — per evitare il rischio documentato da Bybit stesso di restare scoperti se la gamba opposta viene cancellata prima che il Limit venga riempito (vedi `bybit-api-reference-analysis.md` §7).

Regola non negoziabile (identica a OKX): se `place_exit_bracket()` fallisce, l'adapter chiude subito la posizione con un market order e solleva un errore esplicito `ExitProtectionError` (classe già esistente, riusata).

### 5.3 Short/Margin

Fuori scope per questa release, come per OKX. Bybit UTA supporta margin trading unificato (simile concettualmente a OKX, non al modello multi-wallet di Binance) — da rivalutare solo dopo che il flusso long è stabile e il problema fee è confermato risolto.

---

## 6. WebSocket Architecture

### 6.1 Market Data

Sostituire (in aggiunta, non al posto di) `OkxWSClient` con un nuovo `BybitWSClient` che implementa lo stesso `MarketDataWSProtocol` già esistente:

```python
class MarketDataWSProtocol(Protocol):
    candle_queue: asyncio.Queue[CandleEvent]
    trade_queue: asyncio.Queue[TradeEvent]
    status_queue: asyncio.Queue[ConnectionStatusEvent]
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

Per Bybit:
- Canale candele: `kline.{interval}.{symbol}` su `wss://stream.bybit.com/v5/public/spot`
- Canale trade (per CVD): `publicTrade.{symbol}`, stesso endpoint pubblico
- **Punto di attenzione diverso da OKX:** su Bybit, a quanto risulta dalla documentazione, **non esiste la separazione public/business** che ci ha causato un bug reale su OKX (candele spostate sul WS business in una revisione API, TASK-1100.G) — sia `kline` sia `publicTrade` sembrano restare sullo stesso endpoint pubblico `spot`. Da confermare comunque con un test diretto prima di escludere lo stesso tipo di problema.
- Verificare nello spike se il campo `S` (`Buy`/`Sell`) in `publicTrade` corrisponde al lato taker richiesto da `CVDCalculator`.

### 6.2 Order Event Stream

Sostituire (in aggiunta) `OkxOrderEventStream` con `BybitOrderEventStream`, implementando `OrderEventStreamProtocol`:

```python
class OrderEventStreamProtocol(Protocol):
    async def start(self, on_order_update: Callable, on_reconnect_sync: Callable | None = None) -> None: ...
    async def stop(self) -> None: ...
```

Per Bybit, **un solo canale WS privato** (`wss://stream.bybit.com/v5/private`, topic `order`) sembra sufficiente sia per ordini normali sia per OCO/TP-SL (differenziati dal campo `stopOrderType`/`ocoTriggerBy` nel payload), a differenza di OKX che ne richiedeva due (`orders` + `algo-orders` su WS business separato). Questo, se confermato, **semplifica** l'implementazione rispetto a OKX. Payload normalizzato per `_on_order_update` (già provider-neutral):

```python
{
    "provider": "bybit",
    "symbol": "BTCUSDT",
    "side": "sell",
    "order_id": "...",
    "bracket_id": "...",       # orderLinkId o l'equivalente per raggruppare la coppia OCO
    "status": "filled",
    "fill_price": 65000.0,
    "commission": 0.01,
    "commission_asset": "USDT",
    "leg": "take_profit" | "stop_loss" | "exit_bracket",   # da ocoTriggerBy
}
```

**Da verificare se il WS privato Bybit soffre della stessa restrizione EU** già vista su OKX (dove il WS privato era bloccato per account EEA e si è dovuto ripiegare su REST polling). Se anche Bybit blocca il WS privato per account `.eu`, prevedere fin da subito lo stesso pattern di fallback REST polling già implementato in `OkxOrderEventStream` (interrogazione periodica di `GET /v5/order/history` e `GET /v5/execution/list`).

---

## 7. Router e Session Lifecycle

Nessuna nuova astrazione necessaria — il router (`scalping/router.py`) è già provider-neutral al 100% dopo TASK-1107. Le funzioni builder esistenti vanno solo estese con un nuovo branch:

- `_build_exchange_adapter(mode)` -> ramo `if provider == "bybit": return BybitExchangeAdapter.from_settings()`
- `_build_market_ws(symbols, mode)` -> ramo Bybit
- `_build_order_event_stream(mode)` -> ramo Bybit

I principi del flusso OCO restano invariati (stessi di OKX/Binance):
1. Salva DB solo dopo entry + bracket confermati.
2. Se bracket fallisce, chiusura market immediata.
3. Session load guard blocca trade durante restore/start.
4. Su restore, verifica ordini aperti sull'exchange e riconcilia DB.
5. Order event stream si riattiva quando esiste una posizione protetta.

---

## 8. Database

Nessuna nuova colonna strutturale necessaria — lo schema è già generico da TASK-1108 (`exchange_provider`, `exchange_order_id`, `exchange_bracket_id`, `exchange_tp/sl_order_id`, `exchange_raw`, `fee_tier_certified`, `fee_tier_raw`). Basta che il valore di `exchange_provider` possa essere `"bybit"` oltre a `"binance"`/`"okx"`. Nessuna migration SQL nuova prevista, salvo eventuale `CHECK` constraint esplicito su `exchange_provider` che andrebbe verificato/esteso (stesso tipo di bug già trovato su OKX in TASK-1116.D per il campo `mode`).

**Azione di verifica preliminare consigliata:** controllare via Supabase MCP se esiste un `CHECK` constraint su `scalping_sessions.exchange_provider` o `scalping_trades.exchange_provider` che limiti esplicitamente i valori a `('binance', 'okx')` — se sì, va esteso con una migration minima prima di poter salvare sessioni `bybit`, esattamente come già successo con `mode='TEST'` per OKX.

---

## 9. Frontend

Il frontend è già parzialmente exchange-neutral (`ExchangeSymbolsService`, badge provider, endpoint generico `/api/scalping/exchange/instruments`). Le modifiche necessarie sono minime:

- Endpoint `/api/scalping/exchange/instruments` deve restituire anche gli strumenti Bybit quando `EXCHANGE_PROVIDER=bybit`.
- Label provider-aware già esistente (`balanceLabel()` in dashboard) va estesa con `"Saldo Bybit"`.
- Badge modalità: `BYBIT DEMO`/`BYBIT LIVE` accanto ai badge OKX/Binance già esistenti.
- Dropdown simboli: default symbol da rivalutare (probabile `BTCUSDT` invece di `OKB-EUR`/`BTC-EUR`, in base a cosa emerge dallo spike sulla liquidità EUR).

---

## 10. Spike Obbligatorio Prima dell'Implementazione (Fase 0)

Analogo a TASK-1100 per OKX, ma con un ordine di priorità diverso: qui il primo blocco da risolvere non è tecnico ma di **accesso** e di **economia delle fee**.

1. **Verificare l'accesso API su Bybit EU** (punto critico #1 di `bybit-api-reference-analysis.md`) — creare un account (se non esiste già) o usare quello esistente, attendere le 48h di lock se l'account è nuovo, tentare la creazione di una API key HMAC "System-generated" e verificare se è vincolata a "Connect to Third-Party Applications" oppure se supporta un uso custom libero.
2. Se il punto 1 è bloccato: valutare testnet Bybit (`api-testnet.bybit.com`) come ambiente di validazione tecnica separato dalla questione dell'accesso EU, ma **non scambiare "funziona su testnet" con "è utilizzabile in produzione da un account EU retail"** — sono due domande distinte.
3. Recuperare il fee tier reale (`GET /v5/account/fee-rate`) e confrontarlo numericamente con l'ultimo fee tier OKX osservato in produzione — decidere se la migrazione ha ancora senso economico.
4. Instrument discovery: verificare quali coppie EUR esistono e sono liquide, o se conviene una coppia USDT con conversione EUR solo per la dashboard.
5. Piazzare un market order minimo, verificare fill price, quantity, commission, commission asset.
6. Piazzare un OCO Spot (TP/SL Market al trigger) sulla posizione aperta, verificare `stopOrderType`/`ocoTriggerBy` nella risposta.
7. Ascoltare il fill dell'OCO sul canale WS privato `order` — confermare se serve un canale separato per algo/TP-SL o se lo stesso topic basta (a differenza di OKX).
8. Verificare il campo lato taker su `publicTrade` per il CVD.
9. Documentare tutto in `docs/analysis/bybit-demo-spike-results.md` (stesso formato di `okx-demo-spike-results.md`), incluso un JSON raw dei payload osservati.

Se uno dei punti 1-3 fallisce o dà esito negativo, **non si procede** con il porting del router — si torna a rivalutare la strategia (es. rinegoziare SL/TP su OKX, oppure valutare un terzo exchange).

---

## 11. Rischi e Mitigazioni

| Rischio | Impatto | Mitigazione |
|---|---|---|
| Accesso API bloccato per account EU retail | Bloccante totale, ferma la migrazione | Spike Fase 0, punto 1, prima di ogni altra cosa |
| Fee reali non risolvono il problema economico | Alto — la migrazione perderebbe la sua motivazione principale | Confronto numerico esplicito in Fase 0 prima di investire nel porting |
| OCO Spot Bybit ancora "giovane"/poco documentato | Medio — comportamenti inattesi in produzione | Test isolato con quantità minima, stesso principio già usato per OKX |
| Simboli EUR poco liquidi | Medio — slippage o mancata esecuzione | Fallback su coppia USDT/USDC + conversione EUR lato dashboard |
| WS privato bloccato per EU (come già visto su OKX) | Medio — fill TP/SL non in tempo reale | Prevedere da subito fallback REST polling, stesso pattern già implementato per OKX |
| Doppio round-trip fee se si finisce per operare su più coppie diverse per arbitraggio liquidità | Basso | Preferire una singola coppia liquida e stabile, coerente col principio "one change at a time" |
| Collector Intelligence (funding rate, OI, long/short) potrebbero non avere equivalente Bybit per spot-only | Basso-Medio | Stesso audit già fatto per OKX in TASK-1116, graceful skip se non disponibile |

---

## 12. Ordine di Task Proposto (numerazione provvisoria TASK-1200+)

1. **TASK-1200** — Spike Bybit EU/Demo: accesso API, fee tier, market order, OCO Spot, WS fill, WS trades (Fase 0 di questo documento). **Bloccante per tutto il resto.**
2. **TASK-1201** — Config provider Bybit (`EXCHANGE_PROVIDER=bybit`, credenziali, computed fields) — solo dopo TASK-1200 positivo.
3. **TASK-1202** — `BybitExchangeAdapter` REST (balance, holdings, ticker, symbol rules, fee tier, market order, close position).
4. **TASK-1203** — `place_exit_bracket()` Bybit (OCO Spot nativo, TP/SL Market al trigger, emergency close su fallimento).
5. **TASK-1204** — `BybitWSClient` market data (candele + trade pubblici).
6. **TASK-1205** — `BybitOrderEventStream` (fill OCO/TP-SL via WS privato o fallback REST polling se bloccato per EU).
7. **TASK-1206** — Estensione `exchange_factory.py` e builder provider-neutral nel router (nessun refactor strutturale, solo nuovo branch `bybit`).
8. **TASK-1207** — Verifica/estensione `CHECK` constraint DB su `exchange_provider` se necessario.
9. **TASK-1208** — Frontend: dropdown simboli, badge, label Bybit.
10. **TASK-1209** — Audit collector Signal Intelligence per Bybit (funding rate/OI/long-short — equivalente Bybit o graceful skip).
11. **TASK-1210** — Test integration con fake Bybit adapter (stesso pattern di `fake_okx_adapter.py` + `test_okx_integration.py`): happy path, bracket failure, stop session, restore open/closed, fee/net pricing.
12. **TASK-1211** — Validazione Demo/Testnet end-to-end: sessione scalping completa con trade minimo.
13. **TASK-1212** — Verifica economica finale: N sessioni con SL/TP a valori economicamente coerenti con il fee tier reale Bybit, confronto win rate/PnL netto vs baseline storica OKX (18 sessioni, 70 trade, 34.3% win rate, -3.05 USDC — vedi memoria di progetto) per capire se il cambio ha davvero migliorato la sostenibilità economica del sistema.
14. **TASK-1213** — Cutover: `EXCHANGE_PROVIDER=bybit` come default, runbook operativo (stesso formato di `okx-live-runbook.md`), safety gates (`ALLOW_LIVE_MODE=false` di default, conferma manuale per il primo trade live).

**Nota importante:** a differenza della migrazione OKX (dove il problema era "Binance non è più utilizzabile, serve un'alternativa qualunque essa sia"), qui la domanda di fondo è "questa alternativa risolve davvero il problema economico?". Se TASK-1200 (spike) rivela che le fee Bybit non cambiano sostanzialmente la sostenibilità dello scalping a SL 0.3%, la conclusione corretta potrebbe non essere "cambiare ancora exchange" ma **rivedere i parametri di rischio della strategia stessa** (SL/TP più larghi, frequenza di trade più bassa, filtri di ingresso più selettivi) — un'opzione che vale la pena tenere esplicitamente sul tavolo accanto alla migrazione, non come alternativa scartata a priori.

---

## 13. Definition of Done

La migrazione (o la sua rivalutazione, se il punto economico/di accesso fallisce) è completa quando:

- Il punto critico #1 (accesso API EU) ha una risposta empirica documentata, positiva o negativa.
- Se positiva: `EXCHANGE_PROVIDER=bybit` avvia una sessione paper e demo/testnet senza riferimenti Binance/OKX nel path operativo.
- Il fee tier reale è certificato (`fee_tier_certified=True`) e confrontato numericamente con OKX.
- SL/TP configurati sono stati ricalcolati (se necessario) per essere economicamente sostenibili rispetto alle fee reali Bybit.
- Market order + exit bracket OCO funzionano in demo/testnet con fill osservato sul canale corretto.
- Stop session cancella il bracket e chiude market in modo sicuro (nessuna posizione orfana).
- Restore session riconcilia posizione aperta/chiusa correttamente.
- Test automatici con fake adapter coprono almeno gli stessi scenari già coperti per OKX (happy path, bracket failure, stop, restore open/closed, fee pricing).
- Almeno una sessione demo/testnet completa è documentata in `docs/analysis/bybit-demo-spike-results.md` senza ordini orfani.
- Se il punto economico risulta negativo: la conclusione e le alternative (rivedere SL/TP su OKX, altro exchange) sono documentate esplicitamente, non lasciate implicite.
