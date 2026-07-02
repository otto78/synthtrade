# SynthTrade — Piano Implementazione Migrazione OKX

> Data: 2026-07-02  
> Fonte architetturale: `docs/architecture/okx-migration-architecture.md`  
> Stato: piano operativo per task loom TASK-1100 -> TASK-1116
> Breakdown operativo: `docs/plans/okx-migration-task-breakdown.md`

---

## Strategia

La migrazione va fatta in due binari:

1. spike OKX Demo Trading per eliminare incertezza su auth, algo order e WS;
2. refactor incrementale dell'app per rendere exchange, market data e order stream pluggable.

Non si implementa short/margin nella prima release OKX. Prima si ripristina il flusso long live protetto da TP/SL server-side; lo short viene ripianificato dopo la validazione OKX.

---

## Fase 0 — Spike Demo Trading

**Obiettivo:** provare OKX fuori dal router live.

Deliverable:

- `scripts/test_okx_demo.py` o script equivalente non integrato nel runtime;
- `docs/analysis/okx-demo-spike-results.md` con payload reali e decisioni finali;
- conferma su `x-simulated-trading`, passphrase, symbol rules, fee tier, market order, exit bracket, WS fill.
- verifica `OKB-EUR` in Demo Trading come default operativo iniziale.

Blocco: senza questa fase non si procede con TASK-1102+.

---

## Fase 1 — Config e Provider Factory

**Obiettivo:** introdurre provider OKX senza rompere Binance legacy.

Modifiche:

- `config.py`: `EXCHANGE_PROVIDER`, credenziali OKX demo/live, computed field generici;
- `.env.example`: documentare OKX;
- `exchange_factory.py`: provider-aware;
- test config/factory.

Output: l'app puo' dichiarare provider OKX ma il runtime scalping puo' ancora restare su Binance fino ai task successivi.

---

## Fase 2 — Protocollo Exchange e Adapter OKX

**Obiettivo:** separare dominio SynthTrade da dettagli Binance.

Modifiche:

- estrarre modelli `MarketOrderRequest`, `ExitBracketRequest`, `SymbolRules`, `ExchangeOrder`, `FeeTier`;
- rinominare semanticamente `place_oco_order` -> `place_exit_bracket`;
- implementare `OkxExchangeAdapter`;
- mantenere `BinanceExchangeAdapter` come legacy adapter dietro lo stesso protocollo.
- mantenere parita' funzionale per `get_trade_fee()` e `fee_tier_certified`.

Test:

- symbol mapping `BNBUSDC` <-> `BNB/USDC` <-> `BNB-USDC`;
- default `OKB-EUR` e discovery strumenti live;
- rounding OKX da market metadata;
- failure bracket -> errore specifico;
- commission extraction.
- `_net_to_gross_pct()` usa maker/taker OKX e quote currency corretta.

---

## Fase 3 — WebSocket Market Data OKX

**Obiettivo:** sostituire `BinanceWSClient` nel path scalping.

Modifiche:

- creare `MarketDataWSProtocol`;
- creare `OkxWSClient`;
- spostare `CandleEvent`, `TradeEvent`, `ConnectionStatusEvent` in modulo shared;
- aggiornare `_start_ws_broadcast()` per costruire client via factory.

Test:

- parser candle OKX;
- parser trade OKX con lato taker validato;
- reconnect/backoff;
- compatibilita' con CVDCalculator.

---

## Fase 4 — Order Event Stream OKX

**Obiettivo:** ricevere fill di TP/SL server-side da OKX.

Modifiche:

- creare `OrderEventStreamProtocol`;
- creare `OkxOrderEventStream`;
- normalizzare payload fill per `_on_order_update`;
- preservare `on_reconnect_sync`.

Test:

- fill TP;
- fill SL;
- evento duplicato/expired ignorato;
- reconnect sync con posizione gia' chiusa.

---

## Fase 5 — Router Scalping Provider-Neutral

**Obiettivo:** rimuovere assunzioni Binance dal ciclo sessione.

Modifiche:

- `_build_exchange_adapter`;
- `_build_market_ws`;
- `_build_order_event_stream`;
- `_handle_exit_bracket_failed`;
- route strumenti generica `/api/scalping/exchange/instruments`;
- aggiornare restore session con `exchange_provider`.

Test:

- start live demo OKX con fake adapter;
- bracket failure chiude market e non salva posizione aperta;
- stop session cancella bracket e chiude market;
- restore con bracket aperto;
- restore con bracket gia' fillato.

---

## Fase 6 — DB e Persistenza

**Obiettivo:** tracciare provider, ordini OKX e compatibilita' storica.

Modifiche:

- migration nuove colonne su `scalping_sessions` e `scalping_trades`;
- persistenza `exchange_provider`, order id, bracket id, raw payload;
- persistenza `fee_tier_certified`, fee raw e commission asset entry/exit;
- query storiche backward-compatible.

Test:

- sessione Binance storica ancora leggibile;
- sessione OKX nuova salva provider e ids;
- performance/trade log non filtrano erroneamente.

---

## Fase 7 — Frontend Exchange-Neutral

**Obiettivo:** rimuovere hardcoding Binance dalla UI.

Modifiche:

- `BinanceSymbolsService` -> `ExchangeSymbolsService`;
- route strumenti generica;
- default UI `OKB-EUR` se disponibile, altrimenti primo strumento EUR live configurato;
- label provider nel topbar/dashboard;
- badge DEMO/LIVE + provider;
- testi "Saldo Binance" -> "Saldo OKX" quando provider OKX.

Test:

- service Angular;
- dashboard render provider;
- session controls caricano strumenti OKX.

---

## Fase 8 — Cutover e Hardening

**Obiettivo:** passare OKX a provider primario.

Checklist:

- `EXCHANGE_PROVIDER=okx` default in `.env.example`;
- Binance resta legacy ma non e' il default;
- dashboard balance provider-neutral sostituisce `binance_balance.py`;
- collector Binance/Futures auditati: sostituiti, disabilitati o marcati come fonte esterna;
- documentazione setup OKX completata;
- smoke test Demo Trading;
- trade minimo live solo dopo conferma manuale;
- changelog/story/handoff aggiornati.

---

## Ordine Task

1. TASK-1100 — Spike OKX Demo Trading
2. TASK-1101 — Config provider OKX
3. TASK-1102 — Exchange protocol v2
4. TASK-1103 — OkxExchangeAdapter REST
5. TASK-1104 — Exit bracket OKX
6. TASK-1105 — Market data WS OKX
7. TASK-1106 — Order event stream OKX
8. TASK-1107 — Router scalping provider-neutral
9. TASK-1108 — DB migration provider/order ids
10. TASK-1109 — Frontend exchange-neutral
11. TASK-1110 — Market data/backtest factory cleanup
12. TASK-1111 — Tests e fake exchange integration
13. TASK-1112 — Demo end-to-end validation
14. TASK-1113 — Cutover OKX live readiness
15. TASK-1114 — Fee/net pricing parity OKX
16. TASK-1115 — Dashboard balance provider-neutral
17. TASK-1116 — Intelligence collectors OKX audit

Per dettagli esecutivi, ownership, subtasks, test e acceptance criteria usare `docs/plans/okx-migration-task-breakdown.md` come riferimento obbligatorio prima di iniziare ogni task.
