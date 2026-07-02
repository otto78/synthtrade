# SynthTrade — Recap Sessione: Bug Mean-Reversion contro Bias Bearish & Pianificazione Short Selling

**Data:** 25 giugno 2026
**Contesto:** analisi live, in parallelo all'operatività reale del sistema (sessione `cd7ca3bc-1476-4907-bbe1-ea32ac97b034`), con screenshot UI + log applicativi reali.

---

## 1. Punti toccati in questa sessione

| # | Argomento | Stato |
|---|---|---|
| 1 | Calcolo campo "Investito" (20 USDC → 19.44 mostrato) | 🟢 Spiegato, nessun bug |
| 2 | Matematica win/loss asimmetrica (vince 0.06, perde 0.12) | 🟢 Spiegato concettualmente |
| 3 | Pannello Performance non aggiornato con ultimo trade (Total Trades 2 vs 3 nel log) | 🟢 Confermato risolto tra uno screenshot e il successivo |
| 4 | Analisi grafica: supporto/resistenza ignorato dallo Stop Loss fisso | 🟡 Proposta concettuale, non implementata |
| 5 | Distinzione "rimbalzo su livello" vs "breakdown con volume" | 🟡 Proposta concettuale, non implementata |
| 6 | Trade in perdita aperto in pieno bias bearish (4° stop_loss consecutivo) | 🟢 Causa radice identificata via log reali |
| 7 | Disallineamento UI Strategy ("Momentum Base") vs strategia reale in log (`rsi_bollinger`) | 🔴 Bug confermato, non ancora fixato in questa sessione |
| 8 | Assenza di cooldown dopo consecutive losses | 🟡 Proposta, non implementata |
| 9 | Pianificazione architetturale Short Selling | 🟡 Solo analisi/proposta, zero codice scritto |

---

## 2. Punti risolti / spiegati

### 2.1 Campo "Investito" inferiore al valore configurato
**Domanda:** trade da 20 USDC, mostrato "Investito: 19.44 USDC" — dove va la differenza, è la fee?

**Risposta:** non è la fee (lo 0.1% di Binance spiegherebbe solo ~0.02 USDC di differenza, non 0.56). La causa è il **LOT_SIZE rounding**: la quantità BNB calcolata da 20 USDC / entry_price viene troncata (floor) al `stepSize` di Binance prima dell'invio dell'ordine. Verificato a posteriori anche nei log forniti più avanti nella sessione (`qty_raw=0.0344... → qty_precise=0.034, step_size=0.001`), confermando esattamente questo meccanismo.

**Suggerimento dato:** valutare `quoteOrderQty` sugli ordini market per lasciare a Binance il calcolo della qty a precisione massima, evitando il troncamento manuale lato client.

---

### 2.2 "Posso vincere perdendo di più di quanto vinco?"
**Domanda:** è sostenibile una strategia con avg win 0.06 e avg loss 0.12 (poi confermato 0.05/0.12 su trade diversi)?

**Risposta:** sì in teoria, se il win rate compensa (expectancy = winRate×avgWin − (1−winRate)×avgLoss). Ma applicando i numeri reali con tutti i trade visibili in quel momento (incluso quello che il pannello Performance non stava ancora contando), l'expectancy risultava negativa — il che ha portato a scoprire il punto successivo.

---

### 2.3 Pannello Performance disallineato dal Trade Log
**Osservazione:** Trade Log mostrava 3 trade, pannello Performance diceva "Total Trades: 2" — le statistiche (avg win/loss, profit factor, win rate) erano calcolate senza l'ultimo trade chiuso.

**Verificato nello screenshot successivo:** il pannello si è aggiornato correttamente (Total Trades: 3, Avg Loss 0.09 = media di 0.05 e 0.12, Profit Factor 0.35 = 0.06/0.17, Total PnL -0.11 = 0.06-0.05-0.12). **Bug risolto** tra le due osservazioni, nessuna azione necessaria in questa sessione — solo confermato che ora i numeri sono consistenti.

---

### 2.4 Causa radice del 4° stop_loss consecutivo (analisi da log reali)
**Osservazione iniziale (da screenshot):** trade BUY aperto a 583.50 mentre Market Intelligence mostrava Signal Score -16.7 (soglia 10), Bias BEARISH, CVD FALLING, Extreme Fear — apparentemente un'entry long contro un quadro fortemente ribassista.

**Chiarito dai log applicativi forniti dall'utente:**
```
PIPELINE: regime=ranging strategy=rsi_bollinger tech=BUY@0.35 intel=-16.7 (bearish) tradeable=True
⚡ MEAN-REVERSION BUY permesso (source=rsi_bollinger...) nonostante bias=bearish — chiusura range, non long direzionale
```

**Causa reale:** non un bug di gating che "non blocca" — è un comportamento **intenzionale** del codice. La strategia attiva era `rsi_bollinger` (mean-reversion), che per design compra contro il bias quando ritiene di essere in un range (ipotesi: "il prezzo è sceso troppo, rimbalzerà"). Il vero punto critico si sposta quindi su **quanto è affidabile la classificazione del regime come "ranging"** in quella finestra — coerente con il problema di misclassificazione regime già noto nel progetto (movimento con volume spike, probabilmente un trend in formazione, non un range).

**Collegamento con la nota di progetto pre-esistente sulla Falling Knife Protection:** questo episodio è un ulteriore caso concreto a supporto della necessità di una soglia/condizione di sicurezza per le eccezioni mean-reversion, idealmente basata su `trend_direction`/velocità più che su un valore soglia statico.

---

## 3. Bug confermato, non ancora risolto in questa sessione

### 3.1 Disallineamento nome strategia: UI vs log reali
**Osservazione:** il pannello Strategy in UI mostrava costantemente "Momentum Base" (con parametri Ema Fast/Slow, TP/SL%), ma i log applicativi mostrano `strategy=rsi_bollinger` sia nella pipeline di hold che in quella di apertura nuovo trade.

**Nota:** questo è lo stesso sync bug `strategy_selected`/`strategy_executed` già noto e già flaggato in sessioni precedenti come prerequisito bloccante prima di alimentare il Supervisor con dati di sessione attendibili — qui osservato di nuovo "sul campo" con screenshot + log a confronto diretto.

**Suggerimento dato:** essendo un probabile bug di frontend (valore mostrato non aggiornato all'evento giusto, o "agganciato" a uno stato stantio), indicato come punto di indagine rapido vista la specializzazione Angular dell'utente.

---

## 4. Proposte di miglioramento emerse (non implementate)

### 4.1 Analisi struttura grafica (supporti/resistenze) per lo Stop Loss
**Motivazione:** un SL a percentuale fissa (0.35%) ignora la struttura del prezzo — osservato un caso dove lo SL è caduto esattamente dentro una zona di rimbalzo storico, causando uno stop poco prima di un'inversione.

**Proposta architetturale discussa:**
- Nuovo collector (`MarketStructureCollector`) che deriva supporti/resistenze da swing high/low su dati OHLCV già disponibili (Binance), clusterizzando livelli vicini e pesandoli per numero di "touch"
- Utilizzo: evitare entry contro una resistenza forte, oppure piazzare lo SL oltre il livello strutturale più vicino invece che a % fissa
- Distinto dal concetto di "muri" in senso di order book liquidity (endpoint `depth` di Binance) — fonte dati diversa, più rumorosa, da considerare come segnale separato nel `SignalScoreEngine`

### 4.2 Volume di conferma sulla rottura di un livello
**Osservazione (da due screenshot consecutivi dello stesso livello):** lo stesso livello ha prima "tenuto" (rimbalzo senza volume anomalo) e poi si è "rotto" (breakdown con barra di volume molto sopra la media).

**Proposta:** flag `volume_confirmation` nel futuro `MarketStructureCollector` — rottura con volume >1.5-2x media recente → trattare come breakout reale (non allargare lo SL aspettando un rimbalzo); avvicinamento senza volume anomalo → più probabile test/rimbalzo, lì lo SL strutturale ha senso.

**Raccomandazione metodologica:** trattare come esperimento isolato — backtestare il rilevamento livelli da solo prima di agganciarlo a decisioni live, coerente col principio "one change at a time".

### 4.3 Cooldown dopo consecutive losses
**Osservazione:** il 4° trade della sequenza si è aperto 42 secondi dopo la chiusura in stop_loss del precedente, senza alcun meccanismo di pausa nonostante 3 perdite consecutive e un quadro di mercato fortemente bearish/Extreme Fear.

**Proposta:** introdurre un meccanismo di cooldown specifico per consecutive losses (es. pausa entry dopo N stop_loss di fila, o richiesta di una conferma aggiuntiva come il volume di cui sopra prima di un nuovo mean-reversion entry) — distinto dal cooldown già esistente sui cambi di strategia (20 minuti).

---

## 5. Short Selling — stato della pianificazione

**Punto di partenza dichiarato dall'utente:** nessuna implementazione esistente, solo analisi pregresse.

**Motivazione rafforzata da questa sessione:** lo short risolverebbe direttamente il problema osservato al punto 2.4 — con bias bearish forte e regime correttamente classificato come trending-down (non ranging), il sistema potrebbe tradare la direzione reale del mercato invece di essere limitato a mean-reversion contro-trend o nessuna azione.

**Struttura a fasi proposta in questa sessione (coerente con roadmap già esistente nel progetto):**

1. **Borrow/repay isolato e testabile** (`margin_short.py`, solo testnet) — `open_short()` (borrow + sell) e `close_short()` (buy + repay), validabile senza toccare la logica di trading esistente
2. **Entry-side awareness nel `signal_aggregator`** — decisione di prodotto aperta: short solo come trend-following (consigliato per iniziare, coerente col bug osservato oggi) oppure anche short mean-reversion (più rischioso, da validare dopo)
3. **OCO mirrorato** — TP sotto l'entry, SL sopra, calcolo PnL invertito (entry − exit) ovunque oggi si assume long-only
4. **Risk Controls / StrategySelector simmetrici** — % SL/TP applicate per direzione invece che solo per long

**Stato a fine sessione:** 🔴 Nessun codice scritto. Prossimo passo concordato: partire dal blocco 1 (borrow/repay isolato), validarlo su testnet, fermarsi lì prima di proseguire — in attesa di conferma per procedere con l'implementazione.

---

## 6. Riepilogo aperti / prossimi passi

- [ ] Fix sync bug nome strategia mostrato in UI (Angular, frontend) vs strategia realmente eseguita
- [ ] Decidere se/come irrobustire la classificazione regime ranging vs trending (collegato a `MarketStructureCollector` e a `trend_direction`/`diverging`, già notato in sessioni precedenti)
- [ ] Implementare Falling Knife Protection con un caso reale aggiuntivo a supporto (questo episodio)
- [ ] Valutare introduzione cooldown su consecutive losses
- [ ] Avviare Fase 1 short selling: `margin_short.py` isolato su testnet
- [ ] (Da sessioni precedenti, ancora aperto) Verifica empirica end-to-end calcolo fee/PnL su un trade reale chiuso con i fix già applicati

---

## 7. File prodotti in questa sessione

1. Questo recap
