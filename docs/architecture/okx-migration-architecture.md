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

---

## 5. OKX Trading Model

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

OKX non richiede il modello Binance "wallet separati -> transfer -> borrow -> repay" come percorso primario. Per OKX il piano e':

```text
Segnale SELL approvato e short_enabled=true
  -> place_market_order(tdMode=cross|isolated, side=sell, auto-borrow se confermato)
  -> place_exit_bracket(side=buy, TP sotto entry, SL sopra entry)
  -> auto-repay alla chiusura se supportato e validato
```

Implicazioni:

- `WalletOrchestrator` Binance non va implementato ora.
- La futura epica short riparte da OKX margin mode e account mode.
- Il DB deve comunque prevedere `position_side`, `margin_mode`, `borrow_asset`, `borrow_amount`, `margin_interest`, `repay_status`, ma questi campi si popolano secondo la semantica OKX.

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

---

## 10. Spike Obbligatorio Prima dell'Implementazione

Prima di toccare il flusso live:

1. creare API key OKX Demo Trading;
2. verificare REST auth con passphrase e header demo;
3. verificare `ccxt.okx` con `set_sandbox_mode(True)` e, se serve, header manuale;
4. leggere strumenti e regole per `BNB/USDC` o coppia alternativa disponibile;
5. piazzare market order minimo;
6. piazzare exit bracket TP/SL;
7. ascoltare fill su WS corretto;
8. confermare payload trade pubblico per CVD;
9. documentare payload reali in `docs/analysis/okx-demo-spike-results.md`.

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

