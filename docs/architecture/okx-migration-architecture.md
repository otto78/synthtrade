# SynthTrade — Architettura Definitiva Migrazione Binance -> OKX

> Data: 2026-07-02  
> Stato: definitivo per pianificazione, da validare con spike Demo Trading prima del codice live  
> Scope: sostituire Binance come exchange operativo per live trading in Italia, mantenendo la pipeline scalping esistente e rendendo l'integrazione exchange pluggable.

---

## 1. Decisione Architetturale

Binance non e' piu' utilizzabile come exchange operativo per l'Italia. SynthTrade deve migrare a OKX senza trasformare il codice in un porting fragile 1:1.

La decisione e':

1. introdurre un layer exchange pluggable stabile;
2. mantenere Binance solo come adapter legacy/test fino a rimozione esplicita;
3. implementare OKX come adapter primario;
4. spostare la logica specifica Binance fuori da router, websocket, balance e frontend;
5. trattare short/margin con semantica OKX, non con WalletOrchestrator Binance.

Questa migrazione ha priorita' superiore all'epica short selling Binance: TASK-1000 resta utile come riferimento concettuale, ma non deve essere implementato prima di OKX.

---

## 2. Vincoli del Progetto

SynthTrade oggi dipende da Binance in questi punti:

| Area | Stato attuale | Decisione OKX |
|---|---|---|
| Config | `BINANCE_*`, `binance_base_url`, `binance_ws_base_url` in `config.py` | aggiungere `EXCHANGE_PROVIDER=okx`, credenziali OKX demo/live, computed field generici |
| Factory | `core/exchange_factory.py` crea `ccxt.binance` sync | rifare come factory provider-aware; per scalping usare adapter async |
| Adapter | `BinanceExchangeAdapter` in `execution/exchange.py` | estrarre protocollo e creare `OkxExchangeAdapter` |
| Market data | `core/market_data.py`, backtest e generator basati su `ccxt.binance` | usare factory generica; simboli in formato normalizzato |
| Scalping WS | `BinanceWSClient` parse kline/trade Binance | introdurre `MarketDataWSProtocol` e `OkxWSClient` |
| User stream | `UserDataStreamManager` Binance UDS | introdurre `OrderEventStreamProtocol`; OKX usa WS private/business |
| OCO/TP-SL | Binance OCO nativo | OKX algo order / attached TP-SL, da validare in Demo |
| Frontend | `BinanceSymbolsService`, label "Saldo Binance" | rinominare in exchange-neutral |
| Docs/tasks | riferimenti `docs/architecture/okx-api-reference.md` mancanti | rendere questo file la fonte architetturale primaria |

---

## 3. Provider Model

### 3.1 Configurazione

Nuove variabili:

```env
EXCHANGE_PROVIDER=okx
TRADING_MODE=test

OKX_API_KEY=...
OKX_SECRET_KEY=...
OKX_PASSPHRASE=...

OKX_API_KEY_LIVE=...
OKX_SECRET_KEY_LIVE=...
OKX_PASSPHRASE_LIVE=...

OKX_DEMO_TRADING=true
ALLOW_LIVE_MODE=false
```

Regole:

- `TRADING_MODE=test` usa OKX Demo Trading e deve inviare `x-simulated-trading: 1`.
- `TRADING_MODE=live` usa credenziali live e richiede `ALLOW_LIVE_MODE=true`.
- La passphrase OKX e' una credenziale obbligatoria, distinta da key/secret.
- Le computed property Binance rimangono temporaneamente per compatibilita', ma ogni nuovo codice usa nomi generici: `exchange_api_key`, `exchange_secret_key`, `exchange_passphrase`, `exchange_provider`.

### 3.2 Interfacce

Il protocollo exchange deve rappresentare le esigenze di SynthTrade, non i nomi Binance:

```python
class ExchangeAdapterProtocol(Protocol):
    provider: str
    trading_mode: str

    async def close(self) -> None: ...
    async def get_balance(self, asset: str) -> float: ...
    async def get_holdings(self) -> dict[str, float]: ...
    async def get_ticker_price(self, symbol: str) -> float: ...
    async def get_symbol_rules(self, symbol: str) -> SymbolRules: ...
    async def place_market_order(self, request: MarketOrderRequest) -> ExchangeOrder: ...
    async def close_position(self, request: ClosePositionRequest) -> ExchangeOrder: ...
    async def place_exit_bracket(self, request: ExitBracketRequest) -> ExitBracketOrder: ...
    async def get_open_exit_orders(self, symbol: str) -> list[ExchangeOrder]: ...
    async def cancel_open_exit_orders(self, symbol: str) -> None: ...
    async def get_trade_fee(self, symbol: str) -> FeeTier: ...
```

`place_exit_bracket()` sostituisce `place_oco_order()`. Per Binance puo' mappare a OCO, per OKX a algo TP/SL. Il resto dell'app non deve sapere quale meccanismo usa l'exchange.

---

## 4. Symbol Model

SynthTrade usa ancora simboli compatti Binance tipo `BNBUSDC`. OKX usa strumenti tipo `BNB-USDC`, mentre ccxt usa `BNB/USDC`.

Decisione:

- Il dominio interno usa `SymbolRef`.
- Le API frontend possono continuare a inviare `BNBUSDC` durante la transizione.
- Ogni adapter espone `normalize_symbol()` e `to_exchange_symbol()`.

```python
@dataclass(frozen=True)
class SymbolRef:
    base: str
    quote: str

    @property
    def compact(self) -> str: ...
    @property
    def ccxt(self) -> str: ...
```

Questo evita parsing ad hoc in router e WS.

### 4.1 Instrument Discovery e Default Operativo

L'app non deve assumere che una coppia esista solo perche' e' configurata. All'avvio sessione e all'apertura della dashboard scalping va caricata la lista strumenti spot realmente permessi dall'exchange:

```text
OKX GET /api/v5/public/instruments?instType=SPOT
```

Regole:

- filtrare `instType=SPOT` e `state=live`;
- esporre al frontend solo coppie live;
- usare `lotSz`, `minSz`, `tickSz`, `maxMktSz`, `maxMktAmt` per quantity/price rules;
- se il simbolo richiesto non esiste o non e' live, bloccare start sessione con errore esplicito;
- mantenere una cache breve in memoria, ma sempre refreshabile.

Default di transizione: `OKB-EUR`, perche' e' una coppia OKX/EUR adatta al nuovo contesto operativo. Verifica fatta il 2026-07-02 sull'endpoint pubblico OKX:

- `OKB-EUR`: `state=live`, `baseCcy=OKB`, `quoteCcy=EUR`, `lotSz=0.00001`, `minSz=0.01`, `tickSz=0.01`.
- `BNB-USDC`: l'endpoint pubblico OKX lo indica `state=live` al 2026-07-02, ma non va comunque usato come default per la migrazione perche' il nuovo test iniziale sara' su `OKB-EUR` e la disponibilita' effettiva va sempre validata runtime.
- Primo run Demo Trading 2026-07-02: con header demo, `OKB-EUR` e `BNB-USDC` ritornano `51001` non disponibili; la discovery Demo espone invece coppie EUR come `SOL-EUR`, `BTC-EUR`, `ETH-EUR`, `USDC-EUR`, `USDT-EUR`. Quindi il default deve essere environment-aware: live candidato `OKB-EUR`, demo fallback da lista EUR live.

TASK-1100 deve confermare anche la disponibilita' in Demo Trading, non solo sulla lista pubblica live.

---

## 5. OKX Trading Model

### 5.0 Fee Tier, Net Pricing e PnL

Il comportamento attuale su Binance recupera il fee tier a inizio sessione (`get_trade_fee()`), salva `_execution_state["fee_tier"]` e usa `_net_to_gross_pct()` per trasformare target netti desiderati in prezzi TP/SL lordi. Questa logica e' obbligatoria anche su OKX.

Requisiti:

- `OkxExchangeAdapter.get_trade_fee(symbol)` deve recuperare fee maker/taker specifiche account/simbolo o fallire in modo certificabile.
- `_execution_state["fee_tier_certified"]` deve rimanere anche con OKX.
- Se il fee tier non e' certificato, UI/log devono segnalarlo e i calcoli usano fallback esplicito, non silenzioso.
- Il market entry usa fee taker attesa.
- L'exit bracket usa fee **taker** per entrambe le gamme — OKX OCO esegue `tpOrdPx="-1"` e `slOrdPx="-1"` (market orders). Confermato da ordini reali (2026-07-16): "TP Market" e "SL Market". Fee round-trip = taker + taker.
- I log `[NET_PRICING]`, position update, trade log, PnL realtime, close manuale e restore devono usare lo stesso fee model provider-neutral.
- Le commissioni reali da fill OKX vanno normalizzate in `commission` e `commission_asset` come oggi per Binance.
- La conversione commissioni deve diventare quote-aware: oggi esistono helper BNB->USDC; con `OKB-EUR` la quote e' EUR, quindi non bisogna lasciare conversioni hardcoded USDC/BNB.

Definition of done specifica: su una sessione Demo OKX, i target configurati (es. TP netto +0.5%, SL netto -0.3%) devono produrre log, prezzi bracket, PnL e trade history coerenti con fee reali o fee tier certificato.

### 5.1 Spot Long

Flusso equivalente all'attuale:

```text
Segnale BUY approvato
  -> place_market_order(tdMode=cash, side=buy)
  -> place_exit_bracket(side=sell, tp sopra entry, sl sotto entry)
  -> salva posizione solo dopo bracket confermato
  -> ascolta evento fill bracket
  -> chiudi posizione in memoria + DB + broadcast UI
```

`place_market_order` deve supportare market buy con dimensionamento coerente. OKX distingue il significato di `sz` con `tgtCcy`; lo spike deve decidere se usare:

- `tgtCcy=quote_ccy` per comprare a budget quote, preferibile se supportato via ccxt/nativo;
- oppure quantita' base calcolata da `QuantityCalculator` come oggi.

### 5.2 Exit Bracket / OCO Equivalent

Principio invariato: nessuna posizione live deve restare aperta senza protezione server-side.

Opzioni OKX:

1. `attachAlgoOrds` dentro l'ordine di apertura;
2. `order-algo` separato con TP/SL;
3. fallback di emergenza: se bracket fallisce dopo entry, chiusura market immediata.

Decisione provvisoria per architettura: usare `place_exit_bracket()` separato, per restare compatibili con il flusso attuale dove l'app apre market e poi registra il bracket. La scelta finale dei parametri OKX e' bloccata dallo spike Demo Trading.

Regola non negoziabile: se `place_exit_bracket()` fallisce, l'adapter chiude subito la posizione con market order e solleva errore esplicito `ExitProtectionError`.

### 5.3 Short/Margin

OKX non richiede il modello Binance "wallet separati -> transfer -> borrow -> repay". Il conto e' unificato e il borrow avviene a livello di ordine:

**Meccanica reale (verificata su documentazione ufficiale OKX):**

1. **Prerequisito:** account mode deve avere `enableSpotBorrow=true` (verificabile via `GET /api/v5/account/config`)
2. **Apertura short:** stesso endpoint del long (`POST /api/v5/trade/order`), cambia solo `tdMode` da `cash` a `cross`/`isolated` e `side=sell`. Il borrow scatta automaticamente al fill se l'account ha enableSpotBorrow e c'e' collaterale/limite sufficiente.
3. **Riconoscimento short a posteriori:** `GET /api/v5/account/positions` — campo `posCcy`: quote currency (EUR) = short, base currency (BTC) = long.
4. **Chiusura short:** `place_exit_bracket(side=buy, TP sotto entry, SL sopra entry)` — stessa logica bracket gia' in uso per il long.
5. **Repay:** automatico se l'account ha `enableSpotBorrow` + modalita' auto-repay; altrimenti esplicito via `POST /api/v5/account/quick-margin-borrow-repay`.

**Costi:**
- Fee: 0.70% round-trip (già noto)
- Interesse: `Liability x (APR / 365 / 24)`, accrual orario. Trascurabile per scalping breve, rilevante per posizioni lunghe (>2h)
- Endpoint pubblico per tasso: `GET /api/v5/public/interest-rate-loan-quota` (nessuna autenticazione)

**Check pre-sessione (feature da implementare):**
- `GET /api/v5/account/max-loan?instId=<symbol>&mgnMode=cross` — se ritorna 0, short non disponibile per quel simbolo
- `GET /api/v5/public/interest-rate-loan-quota?ccy=<asset>` — tasso interesse reale

**Implicazioni:**
- `WalletOrchestrator` Binance non serve (conto unificato OKX).
- La futura epica short riparte da OKX margin mode e account mode.
- Il DB deve comunque prevedere `position_side`, `margin_mode`, `borrow_asset`, `borrow_amount`, `margin_interest`, `repay_status`, ma questi campi si popolano secondo la semantica OKX.
- **Nessuno di questi endpoint e' mai stato chiamato empiricamente sul vostro account reale.** Prima di scrivere adapter, serve uno spike read-only (stesso principio per OKX Demo e Bybit).

> Rif.: `docs/recap/2026-07-21_okx-short-selling-analysis-recap.md` per dettagli completi.

---

## 6. WebSocket Architecture

### 6.1 Market Data

Sostituire `BinanceWSClient` con una interfaccia:

```python
class MarketDataWSProtocol(Protocol):
    candle_queue: asyncio.Queue[CandleEvent]
    trade_queue: asyncio.Queue[TradeEvent]
    status_queue: asyncio.Queue[ConnectionStatusEvent]
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

`CandleEvent` e `TradeEvent` restano modelli di dominio. I parser Binance/OKX vivono nei client specifici.

Per OKX:

- canale pubblico candle 1m;
- canale pubblico trades per CVD;
- validare nello spike se il payload trade espone il lato taker necessario a `CVDCalculator`.

---

## 6b. Intelligence Collectors e Fonti Binance

La migrazione non riguarda solo gli ordini. Alcuni collector che alimentano i segnali usano Binance o semantiche Binance Futures:

| Componente | Stato attuale | Azione OKX |
|---|---|---|
| `FundingRateCollector` | Binance Futures `/fapi/v1/fundingRate` | verificare OKX funding rate oppure disabilitare per spot-only |
| `OpenInterestCollector` | Binance Futures open interest | sostituire con OKX derivatives endpoint solo se simbolo/perp disponibile |
| `LongShortRatioCollector` | Binance Futures long/short ratio | trovare equivalente OKX o segnare collector unavailable |
| `CVDCalculator` | dipende dal trade stream Binance e `is_buyer_maker` | validare lato taker nel payload trades OKX |
| `BinanceRSSPoller` | annunci Binance per opportunity | sostituire con OKX announcements o rinominare come source separata non-execution |
| `market_data.py` / generator / backtest | `ccxt.binance` e data_source `binance_*` | usare provider factory e `exchange_provider` nei metadati |

Regola: nessun collector deve continuare a chiamare Binance in una sessione OKX senza essere marcato come fonte esterna esplicita. Se una fonte non ha equivalente OKX, il collector deve degradare a `unavailable` e il `SignalScoreEngine` deve ricalcolare i pesi senza falsare il punteggio.

### 6.2 Order Event Stream

Sostituire `UserDataStreamManager` con:

```python
class OrderEventStreamProtocol(Protocol):
    async def start(self, on_order_update: Callable, on_reconnect_sync: Callable | None = None) -> None: ...
    async def stop(self) -> None: ...
```

Per OKX servono due famiglie di eventi:

- ordini normali su WS private;
- algo/bracket su WS business, se confermato dallo spike.

Il router deve ricevere eventi normalizzati:

```python
{
    "provider": "okx",
    "symbol": "BNBUSDC",
    "side": "sell",
    "order_id": "...",
    "bracket_id": "...",
    "status": "filled",
    "fill_price": 123.45,
    "commission": 0.01,
    "commission_asset": "USDC",
    "leg": "take_profit" | "stop_loss" | "exit_bracket",
}
```

---

## 7. Router e Session Lifecycle

`scalping/router.py` oggi conosce troppi dettagli Binance. Il refactor deve introdurre funzioni provider-neutral:

- `_build_exchange_adapter(mode)`
- `_build_market_ws(symbols, mode)`
- `_build_order_event_stream(mode)`
- `_handle_exit_bracket_failed(exchange, symbol)`
- `_on_order_update(event)` basata su evento normalizzato

Restano invariati i principi dell'OCO flow:

1. salva DB solo dopo entry + bracket confermati;
2. se bracket fallisce, chiusura market immediata;
3. session load guard blocca trade durante restore/start;
4. su restore, verifica ordini aperti sull'exchange e riconcilia DB;
5. UDS/order stream si riattiva quando esiste una posizione protetta.

---

## 8. Database

Migration consigliata:

```sql
ALTER TABLE scalping_sessions
ADD COLUMN IF NOT EXISTS exchange_provider TEXT DEFAULT 'binance',
ADD COLUMN IF NOT EXISTS exchange_account_mode TEXT,
ADD COLUMN IF NOT EXISTS exchange_demo BOOLEAN DEFAULT FALSE;

ALTER TABLE scalping_trades
ADD COLUMN IF NOT EXISTS exchange_provider TEXT DEFAULT 'binance',
ADD COLUMN IF NOT EXISTS exchange_order_id TEXT,
ADD COLUMN IF NOT EXISTS exchange_bracket_id TEXT,
ADD COLUMN IF NOT EXISTS exchange_sl_order_id TEXT,
ADD COLUMN IF NOT EXISTS exchange_tp_order_id TEXT,
ADD COLUMN IF NOT EXISTS position_side TEXT CHECK (position_side IN ('LONG', 'SHORT')) DEFAULT 'LONG',
ADD COLUMN IF NOT EXISTS margin_mode TEXT,
ADD COLUMN IF NOT EXISTS borrow_asset TEXT,
ADD COLUMN IF NOT EXISTS borrow_amount NUMERIC(16, 8),
ADD COLUMN IF NOT EXISTS margin_interest NUMERIC(16, 8),
ADD COLUMN IF NOT EXISTS repay_status TEXT,
ADD COLUMN IF NOT EXISTS exchange_raw JSONB;
```

Non rinominare subito le vecchie colonne Binance se esistono dati live storici. Aggiungere campi generici e mantenere compatibilita' in lettura.

Per fee e pricing aggiungere, se non gia' presenti nello schema effettivo:

```sql
ALTER TABLE scalping_sessions
ADD COLUMN IF NOT EXISTS fee_tier_certified BOOLEAN,
ADD COLUMN IF NOT EXISTS fee_tier_raw JSONB;

ALTER TABLE scalping_trades
ADD COLUMN IF NOT EXISTS entry_fee_rate NUMERIC(12, 10),
ADD COLUMN IF NOT EXISTS exit_fee_rate NUMERIC(12, 10),
ADD COLUMN IF NOT EXISTS entry_commission_asset TEXT,
ADD COLUMN IF NOT EXISTS exit_commission_asset TEXT;
```

---

## 9. Frontend

Rinominare progressivamente:

| Attuale | Nuovo |
|---|---|
| `BinanceSymbolsService` | `ExchangeSymbolsService` |
| `/api/scalping/binance/exchange-info` | `/api/scalping/exchange/instruments` |
| "Saldo Binance" | "Saldo Exchange" oppure "Saldo OKX" se provider noto |
| badge TESTNET/LIVE | badge DEMO/LIVE + provider |

La UI non deve contenere assunzioni Binance; deve visualizzare `exchange_provider`, `trading_mode`, `exchange_demo`.

La dashboard principale oggi chiama `get_total_balance_eur()` da `core/binance_balance.py`. Questo va sostituito con un servizio provider-neutral:

```text
ExchangeBalanceService.get_total_balance(target_ccy="EUR")
```

Requisiti:

- usare `exchange.fetch_balance()` dell'adapter/factory corrente;
- convertire ogni asset in EUR usando ticker OKX, preferendo coppie dirette `{ASSET}/EUR`, poi via stablecoin se necessario;
- non includere logiche Binance `LD*` nel provider OKX;
- esporre `exchange_provider` nel payload `/api/dashboard`;
- aggiornare label frontend da "Saldo Binance" a "Saldo OKX" o "Saldo Exchange".

---

## 10. Spike Obbligatorio Prima dell'Implementazione

Prima di toccare il flusso live:

1. creare API key OKX Demo Trading;
2. verificare REST auth con passphrase e header demo;
3. verificare `ccxt.okx` con `set_sandbox_mode(True)` e, se serve, header manuale;
4. leggere strumenti e regole per `BNB/USDC` o coppia alternativa disponibile;
5. confermare `OKB-EUR` in Demo Trading e fallback se non disponibile;
6. recuperare fee tier maker/taker e certificare il payload;
7. piazzare market order minimo;
8. piazzare exit bracket TP/SL con prezzi netti calcolati da fee tier;
9. ascoltare fill su WS corretto con commissione reale;
10. confermare payload trade pubblico per CVD;
11. documentare payload reali in `docs/analysis/okx-demo-spike-results.md`.

Se uno dei punti 5-7 fallisce, non si procede con il porting del router.

---

## 11. Rischi e Mitigazioni

| Rischio | Impatto | Mitigazione |
|---|---|---|
| OKX algo TP/SL non mappato bene da ccxt | Alto | spike nativo + adapter con chiamate private specifiche se necessario |
| Eventi bracket sul WS sbagliato | Alto | validare WS business/private nello spike |
| Market buy usa base/quote in modo inatteso | Alto | test esplicito su `tgtCcy` e ordine minimo |
| Short margin non auto-repay come atteso | Alto | short fuori dalla prima release OKX long-only |
| Simboli `BNBUSDC` non disponibili su OKX | Medio | instrument discovery e fallback quote USDT |
| Frontend resta hardcoded Binance | Medio | task dedicato UI exchange-neutral |
| Dati storici Binance e OKX mischiati | Alto | `exchange_provider` su sessioni/trade/cache |

---

## 12. Definition of Done

La migrazione e' completa quando:

- `EXCHANGE_PROVIDER=okx` avvia una sessione paper e live demo senza riferimenti Binance nel path operativo;
- market data OKX alimenta candle buffer, CVD e dashboard;
- ordine market + exit bracket server-side funzionano in Demo Trading;
- fill TP/SL viene ricevuto via WS e chiude DB/UI con PnL e fee;
- stop session cancella bracket e chiude market in modo sicuro;
- restore session riconcilia posizione aperta o chiusa;
- frontend mostra provider OKX e strumenti OKX;
- test unitari coprono adapter, parser WS, symbol mapping e failure bracket;
- test integrazione con fake adapter coprono start -> entry -> bracket -> fill -> close.
