# Collector Intelligence — Piano Recupero Abbondanza su OKX

**Contesto:** segue `TASK-1119_collector-coverage-diagnostica.md`. Quel task misura
il problema; questi task lo risolvono aggiungendo collector reali, non ridistribuendo
pesi a intuito.

**Principio guida:** per token spot-only senza perpetual da nessuna parte (es. OKB),
funding_rate/open_interest/long_short_ratio NON possono essere recuperati — non è un
bug, è la natura dello strumento. L'abbondanza per questi simboli si ottiene con
collector nuovi che usano dati sempre disponibili su qualunque spot OKX (Binario A),
non forzando dati inesistenti. Per simboli con perpetual reale (BTC, ETH) si recupera
invece l'endpoint OKX nativo al posto di quello Binance morto (Binario B).

**Ordine consigliato:** 1120 (zero rischio) → 1121/1122 (Binario A, massimo impatto per
spot-only) → 1123 (Binario B, impatto solo su BTC/ETH-class) → 1124 (spike, esito incerto).

---

## TASK-1120 — Quick win: abilitare whale collector + verificare sentiment su OKX

**Priorità:** ALTA — zero rischio, zero codice nuovo
**Stima:** 30 min
**Dipendenze:** nessuna

### Obiettivo
Il collector `whale` (Whale Alert RSS + Blockchair, TASK-804) è già implementato e
indipendente dall'exchange, ma disabilitato di default. Abilitarlo aggiunge un
collector reale immediatamente, per qualunque simbolo.

### Modifiche
1. In `.env`: `SCALPING_WHALE_ENABLED=true`
2. Verificare che `WHALE_ALERT_API_KEY` sia valorizzata (se vuota, il collector
   userà solo Blockchair whale tx filter — verificare in log se questo basta o
   se serve la key)
3. **Verifica separata per `sentiment`** (CryptoCompare + NewsAPI, TASK-804):
   questo collector è già exchange-indipendente per design, ma nei log recenti
   OKX compare intermittenza (`getaddrinfo failed` — vedi
   `docs/recap/2026-06-29_errori-notturni.md` punto 6). Va verificato se in
   sessione OKX risponde regolarmente o se lo stesso problema DNS lo affligge.

### Verifica di completamento
- Avviare sessione paper/demo, controllare nei log che compaiano righe con
  `whale` popolato (non più sempre `None`)
- Confermare che il coverage calcolato in TASK-1119 salga di conseguenza
- Se `sentiment` risulta intermittente, aprire un task separato per la
  robustezza DNS/retry (non bloccante per questo task)

---

## TASK-1121 — OrderBookImbalanceCollector (OKX order book depth)

**Priorità:** ALTA — massimo impatto per simboli spot-only senza perpetual
**Stima:** 3-4 ore
**Dipendenze:** nessuna, funziona su qualunque simbolo spot OKX

### Perché questo e non "recuperare" funding rate per OKB
OKB non ha un mercato perpetual su nessun exchange — non esiste un funding rate o
open interest da recuperare per questo token, su OKX o altrove. Questo collector
invece usa un dato che OKX espone per OGNI pair spot, incluso OKB-EUR: la
profondità dell'order book.

### Endpoint
```
GET https://eea.okx.com/api/v5/market/books?instId={instId}&sz=20
```
Nessuna autenticazione richiesta (pubblico).

### Logica
```python
class OrderBookImbalanceCollector:
    """
    Calcola lo squilibrio tra domanda (bid) e offerta (ask) nell'order book.

    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

    imbalance > 0  → più liquidità sul lato buy → pressione rialzista
    imbalance < 0  → più liquidità sul lato sell → pressione ribassista

    Score: imbalance * 100, clampato a [-100, +100]
    """
    BASE_URL = "https://eea.okx.com"  # coerente con adapter esistente

    async def fetch(self, symbol: str, depth: int = 20) -> OrderBookImbalanceSnapshot | None:
        # GET /api/v5/market/books?instId={symbol}&sz={depth}
        # somma quantità sui primi N livelli bid e ask
        # ritorna None con log se book vuoto o simbolo non trovato
        ...

    @staticmethod
    def imbalance_to_score(imbalance: float) -> float:
        return max(-100.0, min(100.0, imbalance * 100))
```

### Modello Pydantic
```python
class OrderBookImbalanceSnapshot(BaseModel):
    symbol: str
    bid_depth: Decimal
    ask_depth: Decimal
    imbalance: float  # -1.0 a +1.0
    timestamp: datetime
```

### Test (TDD, come da pattern esistente in `tests/scalping/`)
- `test_order_book_imbalance.py`: fetch success, book vuoto, HTTP error,
  imbalance_to_score (5 casi: fortemente bid, fortemente ask, bilanciato, estremi)

### Wiring in SignalScoreEngine
- Aggiungere a `WEIGHTS` con peso iniziale provvisorio (es. 0.10) — il peso
  definitivo si assesta dopo aver rivisto la coverage reale con TASK-1119
- Nessuna dipendenza da futures o da altri collector

### Verifica
- Sessione OKB-EUR: il collector risponde con dati reali (non None)
- Confrontare `imbalance` calcolato con lo stato reale dell'order book
  visibile su OKX UI per lo stesso istante

---

## TASK-1122 — SpreadCollector (bid-ask spread come proxy liquidità/volatilità)

**Priorità:** MEDIA — complementare a TASK-1121, stesso principio (funziona su ogni spot OKX)
**Stima:** 2 ore
**Dipendenze:** nessuna

### Obiettivo
Usare lo spread bid-ask relativo come segnale di liquidità/incertezza —
spread anomalmente largo rispetto alla media recente indica bassa liquidità
o alta incertezza, utile come filtro di cautela indipendente da funding/OI.

### Endpoint
```
GET https://eea.okx.com/api/v5/market/ticker?instId={instId}
```
Già usato altrove nell'adapter (`get_ticker_price`) — riusa la stessa chiamata,
non serve una nuova connessione.

### Logica
```python
class SpreadCollector:
    """
    spread_pct = (ask - bid) / mid_price * 100

    Mantiene una media mobile dello spread (es. ultimi 20 campioni) per
    normalizzare: uno spread 3x la media recente è anomalo, non un valore
    assoluto arbitrario per simbolo (simboli diversi hanno spread base diversi).

    Score: negativo (cautela) quando spread anomalo, vicino a 0 quando normale.
    Non è direzionale (non dice bullish/bearish) — è un moltiplicatore di
    cautela sul tradeable gate, non un contributo al bias.
    """
```

**Nota di design:** a differenza degli altri collector, questo non produce un
bias bullish/bearish — produce un flag di affidabilità. Va deciso se integrarlo
nel weighted score come gli altri, o come moltiplicatore separato sul
`tradeable` gate (discussione da fare prima di implementare, non assumere).

### Verifica
- Confrontare spread calcolato con quello visibile su OKX UI
- Verificare che durante un momento di bassa liquidità nota (es. notte,
  poco volume) lo spread relativo salga effettivamente

---

## TASK-1123 — Funding Rate / Open Interest via OKX nativo (solo simboli con perpetual reale)

**Priorità:** MEDIA — impatto solo su BTC-EUR/ETH-EUR e simili, non su OKB-EUR
**Stima:** 4-5 ore
**Dipendenze:** TASK-1116.C (collector adapter provider-aware, già pianificato)

### Obiettivo
Per simboli il cui asset base ha un perpetual reale su OKX (es. BTC, ETH),
recuperare funding rate e open interest dall'endpoint OKX nativo invece che
da Binance Futures (morto per definizione su simboli EUR).

### Punto critico da verificare PRIMA di scrivere codice
Il perpetual OKX è quotato in USDT (`BTC-USDT-SWAP`), non in EUR. Il funding
rate/OI riflettono il sentiment sull'asset base (BTC), non sulla coppia EUR
specifica — è un proxy valido (il funding rate BTC è lo stesso concetto
indipendentemente da quale quote currency si sta tradando), ma va documentato
esplicitamente come tale, non presentato come dato "per BTC-EUR" letterale.

### Endpoint OKX
```
GET https://eea.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP
GET https://eea.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP
```

### Modifiche
1. Nuova mappa `OKX_PERPETUAL_MAP: dict[str, str | None]` — base asset →
   instId perpetual OKX (es. `"BTC": "BTC-USDT-SWAP"`, `"OKB": None`)
2. `FundingRateCollector`/`OpenInterestCollector`: se `settings.EXCHANGE_PROVIDER == "okx"`,
   estrarre base asset dal symbol, guardare `OKX_PERPETUAL_MAP`, se non-None
   chiamare l'endpoint OKX; se None, comportamento identico a oggi (unavailable,
   nessuna chiamata Binance)
3. Nessuna chiamata a Binance quando provider è OKX — sostituzione, non aggiunta

### Verifica
- BTC-EUR: funding_rate/open_interest popolati con dati OKX reali
- OKB-EUR: comportamento invariato (unavailable, come da TASK-1116.B)
- Nessun errore 400 residuo verso `fapi.binance.com`

---

## TASK-1124 — Spike: esiste un equivalente OKX per Long/Short Ratio?

**Priorità:** BASSA — esito incerto, da verificare prima di promettere l'implementazione
**Stima:** 1 ora (solo ricerca/verifica empirica, no implementazione)
**Dipendenze:** nessuna

### Obiettivo
`docs/analysis/okx-api-reference-analysis.md` non conferma un equivalente OKX
per il long/short ratio. Prima di aprire un task di implementazione, verificare
empiricamente se esiste (es. famiglia endpoint `rubik/stat` di OKX, da
controllare su docs-v5 aggiornata) e con quale copertura di simboli.

### Output atteso
Un paragrafo in `docs/analysis/okx-api-reference-analysis.md` che conferma
o esclude la disponibilità, con endpoint reale se esiste. Se non esiste,
il collector `long_short_ratio` resta strutturalmente unavailable su OKX
per design — da documentare esplicitamente, non lasciare come "da fare"
indefinito.

---

## Nota su ridistribuzione pesi

Dopo aver completato 1120-1123, il numero di collector realmente attivi cambia
per simbolo (OKB-EUR: whale + sentiment + fear_greed + order_book_imbalance +
spread = 5, contro i 2-3 attuali). A quel punto va ripetuta la misurazione di
`TASK-1119` con i collector nuovi attivi, e SOLO allora decisa la
ridistribuzione finale dei pesi — con numeri letti dai log, non scelti ora.
