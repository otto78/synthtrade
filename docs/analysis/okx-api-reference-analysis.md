# OKX API v5 — Reference Tecnico per SynthTrade

> Scopo: documento di riferimento da consultare PRIMA di scrivere codice sull'integrazione OKX, per evitare di procedere a tentativi. Copre solo ciò che serve a SynthTrade (spot, margin, OCO/algo, WebSocket per CVD).
> Data compilazione: Luglio 2026. Verificare sempre https://www.okx.com/docs-v5/en/ per eventuali aggiornamenti prima di implementare.
> Non ancora verificato empiricamente — tutto ciò che segue va confermato con chiamate reali in Demo Trading prima di fidarsi al 100%.

---

## 1. Base URL e ambienti

| Ambiente | Base URL REST | Base URL WS |
|---|---|---|
| Produzione | https://www.okx.com | wss://ws.okx.com:8443/ws/v5/{public\|private\|business} |
| Demo Trading (= testnet Binance) | stesso host, header speciale | stesso host, header speciale |

Punto critico: OKX non ha un dominio separato per il testnet come testnet.binance.vision. La Demo Trading gira sugli stessi endpoint di produzione, ma:
- Ogni richiesta REST deve includere l'header x-simulated-trading: 1
- Le API key demo si generano da: OKX -> Trade -> Demo Trading -> Personal Center -> Demo Trading API
- Non tutte le funzioni sono supportate in demo (es. withdraw, deposit, purchase/redemption Earn)
- Le API key demo sono diverse dalle API key live, non riusabili tra i due ambienti

Per ccxt: exchange.set_sandbox_mode(True) dovrebbe iniettare l'header automaticamente, ma alcuni bug storici su ccxt segnalavano che serviva a volte anche l'header manuale ({"x-simulated-trading": "1"}). Da verificare empiricamente.

---

## 2. Autenticazione REST

Ogni richiesta privata richiede 4 header:

```
OK-ACCESS-KEY: <api_key>
OK-ACCESS-SIGN: <base64 HMAC-SHA256>
OK-ACCESS-TIMESTAMP: <ISO8601 con millisecondi, es. 2026-07-01T10:06:02.066Z>
OK-ACCESS-PASSPHRASE: <passphrase scelta alla creazione della key>
```

Differenza chiave rispetto a Binance: OKX richiede una terza credenziale, la passphrase, scelta manualmente in fase di creazione della API key (non generata dal sistema). Va salvata insieme a key/secret — se persa, la key non è più utilizzabile e va rigenerata.

Signing string: timestamp + method(UPPERCASE) + requestPath + body
- Per le GET, body si omette (ma i query param fanno parte di requestPath)
- sign = base64(HMAC_SHA256(prehash_string, secret_key))

Vincolo temporale: la richiesta viene rifiutata (errore 50102) se il timestamp differisce di oltre 30 secondi dall'orario server. Usare sempre UTC. Sincronizzare con GET /api/v5/public/time prima di piazzare ordini se ci sono dubbi sul clock del server (rilevante su Windows dove avete già avuto problemi di drift).

---

## 3. Account mode — passaggio obbligatorio prima di operare

OKX richiede di impostare esplicitamente una modalità account, una tantum, da Web/App (non via API), prima di poter usare margin/futures:
- Spot mode
- Futures mode
- Multi-currency margin mode
- Portfolio margin mode

Azione pratica: da fare manualmente nel setup dell'account, prima di qualunque test API. Per SynthTrade (spot + margin) serve probabilmente "Spot mode" o "Multi-currency margin mode". Verificare quale modalità serve leggendo GET /api/v5/account/config una volta loggati.

---

## 4. Piazzare ordini — Spot e Margin

Endpoint: POST /api/v5/trade/order

| Campo | Valori | Note |
|---|---|---|
| instId | es. BTC-USDT | Formato con trattino, non slash — ccxt lo traduce automaticamente da BTC/USDT |
| tdMode | cash (spot puro) / cross / isolated (margin) | Questo campo decide se l'ordine è spot o margin — non serve un endpoint separato |
| side | buy / sell | |
| ordType | market / limit / post_only / fok / ioc | |
| sz | quantita | Per market buy, occhio a tgtCcy |
| px | prezzo (solo per limit) | |

Nota tgtCcy per market order: per gli ordini market, tgtCcy decide se sz è espresso in base currency o quote currency. Va gestito con attenzione nel QuantityCalculator — comportamento diverso da Binance.

---

## 5. TP/SL e OCO — differenza strutturale rispetto a Binance

### 5.1 TP/SL attaccato all'ordine (attachAlgoOrds)
Si passa un array attachAlgoOrds dentro alla stessa chiamata POST /api/v5/trade/order che apre la posizione. L'algo TP/SL diventa attivo solo dopo che l'ordine parent è stato eseguito — se il parent viene cancellato prima del fill, l'algo TP/SL non viene mai generato.

### 5.2 Algo order indipendente (POST /api/v5/trade/order-algo)
Per TP/SL non legati a un ordine parent specifico (probabile scelta per SynthTrade, dato che oggi piazzate il market buy e poi l'OCO separatamente). Si specificano tpTriggerPx/tpOrdPx e slTriggerPx/slOrdPx nello stesso algo order.

Regole di prezzo trigger:
- In vendita (per chiudere long): tpTriggerPx > ultimo prezzo, slTriggerPx < ultimo prezzo
- In acquisto (per chiudere short): tpTriggerPx < ultimo prezzo, slTriggerPx > ultimo prezzo

IMPORTANTE: gli aggiornamenti di stato degli algo order (incluso l'OCO-equivalente) NON arrivano sulla WebSocket "orders" normale — serve sottoscrivere il canale orders-algo sul WS business (/ws/v5/business), non public né private. Punto facile da sbagliare: se il codice ascolta solo "orders" sul WS private, non vedrà mai il fill del TP/SL.

Da verificare empiricamente prima di scrivere order_executor.py: confermare se attachAlgoOrds o order-algo standalone è la scelta giusta per il flusso SynthTrade.

---

## 6. Margin trading — DIFFERENZA ARCHITETTURALE IMPORTANTE vs Binance

Il modello Binance progettato in WalletOrchestrator/MarginBorrowManager presuppone: fondi sparsi su wallet separati (Spot/Funding/Margin/Earn) -> trasferimento esplicito verso Margin -> borrow esplicito -> trade -> repay esplicito -> eventuale trasferimento indietro.

OKX con "Quick Margin" funziona diversamente: nel Trading Account unificato, il margin trading avviene borrowando e ripagando automaticamente come parte del piazzamento/chiusura dell'ordine stesso, con 3 modalità:

| Modalità | Comportamento |
|---|---|
| Manual | Borrow/repay controllati manualmente via endpoint dedicato |
| Auto borrow | Il borrow avviene automaticamente quando l'ordine di apertura viene eseguito |
| Auto repay | Il repay avviene automaticamente quando l'ordine di chiusura viene eseguito |

Con tdMode: cross o isolated sull'ordine stesso, non serve orchestrare trasferimenti tra wallet separati come su Binance — il Trading Account di OKX è unificato, il collaterale è già lì.

Implicazione concreta per il refactor: la Fase 1 di WalletOrchestrator già scritta per Binance (resolve() puro, TransferStep con priorità Margin->Spot->Funding->Earn) probabilmente non serve affatto su OKX, almeno non nella stessa forma. Il flusso short si riduce concettualmente a:

```
Segnale SELL approvato
  -> place order con tdMode=cross/isolated, side=sell (Auto Borrow Mode)
  -> OKX borrowa automaticamente l'asset base e vende
  -> place order-algo per TP/SL di chiusura (side=buy, Auto Repay Mode)
  -> alla chiusura, OKX ripaga automaticamente il prestito
```

Questo elimina gran parte della complessità di wallet_orchestrator.py e margin_borrow_manager.py come progettati — da rivalutare interamente prima di riscrivere TASK-909 per il nuovo exchange. Probabilmente il modulo si riduce a poche righe di configurazione invece di un intero componente con 4 metodi e gestione multi-wallet.

Esiste comunque un endpoint di borrow/repay manuale esplicito (POST /api/v5/account/borrow-repay, con storico VIP loan separato) come opzione B se l'auto mode si rivela insufficiente.

Interesse: matura ogni ora, registrato "sull'ora" (se borrowate alle 22:55 UTC, l'interesse non viene registrato prima delle 23:00). Per trade di scalping <30 minuti l'interesse è trascurabile ma va comunque loggato — stesso principio già applicato nel campo margin_interest dello schema Binance.

---

## 7. WebSocket — canali rilevanti per SynthTrade

Tre endpoint distinti, non intercambiabili:

| Endpoint | Uso | Autenticazione |
|---|---|---|
| /ws/v5/public | Market data: trades, tickers, books, candle | Nessuna |
| /ws/v5/private | Account, orders (ordini normali), positions, balance | Login richiesto |
| /ws/v5/business | orders-algo (TP/SL/OCO), grid trading, altri prodotti "business" | Login richiesto |

### 7.1 Canale trades (per CVD)
Canale pubblico su /ws/v5/public. Da verificare se il payload espone un campo equivalente a is_buyer_maker di Binance (necessario al CVDCalculator per distinguere taker buy da taker sell) — non confermato nella ricerca, va controllato sul messaggio reale ricevuto in demo prima di scrivere cvd_calculator.py. Probabile che il campo si chiami "side" riferito al lato del taker, ma da validare.

### 7.2 Canale orders-algo (per il fill dell'OCO)
Sta sul WS business, non private. Un porting "ingenuo" del codice Binance andrebbe a cercare l'evento sul canale sbagliato.

### 7.3 Rate limit WebSocket
Lunghezza totale dei parametri di sottoscrizione non può superare 64 KB per connessione — irrilevante per il volume di canali che userete.

---

## 8. Rate limit REST

- Errore specifico: 50011 (Rate limit reached)
- Default sub-account: 1000 richieste di ordine/amend ogni 2 secondi (più permissivo del limite storico Binance in weight/min — verificare comunque il limite specifico per endpoint non-trading, tipicamente più basso)
- I livelli VIP alzano ulteriormente il limite in base al fill ratio

Per SynthTrade, che opera su timeframe 1 minuto con poche chiamate per ciclo, questo limite non dovrebbe mai essere un problema — vale comunque la pena un throttle lato client, stesso approccio già usato con enableRateLimit di ccxt.

---

## 9. ccxt + OKX — note pratiche

```python
import ccxt

exchange = ccxt.okx({
    "apiKey": "...",
    "secret": "...",
    "password": "...",       # qui va la PASSPHRASE OKX, non una password account
    "enableRateLimit": True,
})

# Per demo trading:
exchange.set_sandbox_mode(True)
# Se non basta (bug storico riportato su ccxt issue #17295 / #11923):
exchange.headers = {"x-simulated-trading": "1"}
```

Punti da verificare empiricamente appena create le API key demo:
- Confermare che set_sandbox_mode(True) da solo basti nella versione ccxt che userete
- Il parametro password in ccxt corrisponde alla OK-ACCESS-PASSPHRASE — nome poco intuitivo, facile fonte di errori se non documentato nel codice
- Formato simbolo: ccxt usa BTC/USDT e lo traduce automaticamente in BTC-USDT — non serve gestirlo manualmente

Per il market order margin, il parametro chiave da passare in params è tdMode:
```python
order = exchange.create_order(
    "BNB/USDT", "market", "sell", qty,
    params={"tdMode": "cross"}   # o "isolated"
)
```

Per gli algo order (TP/SL/OCO), ccxt instrada verso privatePostTradeOrderAlgo quando il type richiesto è oco/conditional/trigger — da testare con una chiamata reale in demo per vedere esattamente quali parametri ccxt si aspetta nella sua forma unificata, dato che la mappatura tra l'API unificata ccxt e i parametri nativi OKX non è banale.

---

## 10. Mappatura concettuale Binance -> OKX (per il refactor)

| Binance (oggi) | OKX (da usare) | Note |
|---|---|---|
| api.binance.com (spot) | www.okx.com con tdMode=cash | |
| Margin API separata (/sapi/v1/margin/*) | Stesso endpoint ordini, tdMode=cross/isolated | Niente endpoint margin separato per il trading in sé |
| OCO nativo (place_oco) | order-algo con tpTriggerPx+slTriggerPx | Concettualmente equivalente, sintassi diversa |
| WalletOrchestrator (trasferimenti multi-wallet) | Probabilmente non necessario | Trading Account unificato, collaterale già disponibile |
| MarginBorrowManager.borrow()/repay() | Auto Borrow/Auto Repay via tdMode sull'ordine | Drastica semplificazione, da confermare in pratica |
| WS bnbusdc@trade per CVD | WS trades su /ws/v5/public | Verificare campo lato taker |
| WS UserDataStream per OCO fill | WS orders-algo su /ws/v5/business | Endpoint diverso da quello ordini normali |
| Testnet (testnet.binance.vision) | Demo Trading (stesso host, header x-simulated-trading) | API key demo separate da quelle live |
| Token LD-prefissati da escludere dal balance | Nessun equivalente noto — da verificare | Se OKX Earn non mescola i saldi nello stesso modo, il problema potrebbe sparire del tutto |

---

## 11. Cose da NON dare per assodate — verificare empiricamente prima di scrivere codice definitivo

1. Il campo esatto nel payload WS trades che indica il lato del taker (per CVD)
2. Se set_sandbox_mode(True) di ccxt basta da solo o serve l'header manuale aggiuntivo
3. La forma esatta dei parametri ccxt unificati per gli algo order OCO-equivalenti (fare un test isolato)
4. Quale account mode (Spot mode vs Multi-currency margin mode) è effettivamente richiesta per il flusso SynthTrade — da impostare manualmente da UI prima di ogni test
5. Se esiste un equivalente della quirk LD-prefix di Binance per gli asset in Earn/Simple Earn su OKX
6. Se il rate limit per gli endpoint di market data (non-trading) usati per il polling è altrettanto permissivo del limite ordini (1000/2s) — probabile che sia diverso e più basso

Suggerimento pratico: prima ancora di toccare order_executor.py, vale la pena scrivere uno script isolato (test_okx_demo.py, fuori da SynthTrade) che: crea API key demo, fa login WS, piazza un market order minimo con TP/SL, ascolta il fill sul canale giusto. Confermare tutti i punti sopra con osservazione diretta, poi portare quel comportamento confermato dentro l'architettura vera. Stesso principio già seguito per la nota Binance testnet in coda al progetto (test_binance.py).

---

## 12. Prossimi passi quando riprendiamo il codice

1. Creare API key demo OKX, verificare i 6 punti della sezione 11 con uno script isolato
2. Decidere se serve ancora un WalletOrchestrator-equivalente o se il modello auto-borrow/auto-repay è sufficiente
3. Riscrivere ExchangeProtocol (già previsto in Fase 2.B) con i metodi che riflettono la semantica OKX, non un porting 1:1 di quella Binance
4. Aggiornare i task esistenti — il TASK equivalente a "WalletOrchestrator Fase 1" va probabilmente ridimensionato o riscritto alla luce del punto 6

---

Fonti: documentazione ufficiale OKX (okx.com/docs-v5), repository ccxt, issue tracker ccxt, guide tecniche di terze parti verificate incrociando più fonti. Trattare come punto di partenza solido ma non infallibile — la doc OKX si aggiorna con changelog frequenti, verificare sempre la versione più recente su docs-v5 prima dell'implementazione finale.
