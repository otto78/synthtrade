# SynthTrade — Piano di Implementazione Consolidato: Collector Intelligence

> **Versione:** 1.0 — 13 luglio 2026
> **Sostituisce/consolida:** `docs/plans/collector-abbondanza-piano-okx.md` (TASK-1120→1124) + `docs/TASKS.md` sezione "EPICA COLLECTOR IMPROVEMENT" (TASK-COLLECTOR-001→005) + `docs/TASKS.md` TASK-1116.C
> **Analisi di riferimento:** `docs/analysis/collector-intelligence-analysis.md`
> **Recap decisionale:** `docs/recap/2026-07-13_collector-strategy-pivot-recap.md`
> **Contesto vincolante:** OKX unico exchange operativo (Bybit chiuso), simbolo operativo attuale OKB-EUR (spot, nessun perpetual), SL/TP ricalibrati (TASK-OKX-RECAL) → profilo "micro swing" 10-30 trade/giorno invece di scalping ad alta frequenza.

---

## Principio guida di questo piano

Con meno trade al giorno e SL/TP più larghi, ogni decisione del Supervisor comporta un rischio per-trade maggiore rispetto a prima. L'obiettivo di questo piano **non è aggiungere collector per il gusto di avere più dati**, ma colmare il vuoto strutturale lasciato da funding_rate/open_interest/long_short_ratio (assenti per design su OKB-EUR) con segnali che funzionano davvero sul simbolo realmente in uso, prima di lasciare che il sistema apra trade con size significative sotto il nuovo profilo di rischio.

Regola esplicita ripresa dal resto del progetto: **"one change at a time"** — ogni fase sotto va completata e verificata con dati reali (log, non assunzioni) prima di passare alla successiva. Nessuna fase modifica logica di trading esistente (regime detector, strategy selector, SL/TP) — quello è un lavoro successivo esplicitamente fuori scope qui.

---

## Sequenza delle fasi

```
Fase 0 (fatta, TASK-1125) → Fase 1 (TASK-1150) → Fase 2 (TASK-1151, 1152)
    → Fase 3 (TASK-1153) → Fase 4 (TASK-1154, 1155, 1156) → Fase 5 (TASK-1157, 1158)
    → Fase 6 (TASK-1159, ricalibrazione pesi)
```

Le Fasi 2 e 4 sono internamente parallelizzabili (task indipendenti tra loro). La Fase 6 non può iniziare finché le precedenti non hanno prodotto almeno 2-3 sessioni reali di log da cui leggere i numeri.

---

## Fase 0 — Prerequisito (già soddisfatto)

**TASK-1119/1125 — Diagnostica coverage reale per simbolo — ✅ Done**

Fornisce il log `[COVERAGE_REAL]` in `signal_score_engine.py` con `real_coverage`, `structurally_unavailable`, `no_response_transient`, confrontato con `old_coverage_field`. Ogni fase successiva di questo piano va verificata leggendo questo log su una sessione reale, non assumendo il risultato.

---

## Fase 1 — Quick win a zero rischio

### TASK-1150 — Abilitare whale collector + verificare sentiment su OKX

**Status:** ✅ Done (14/07/2026)
**Priorità:** 🔴 Alta — zero rischio, zero codice nuovo
**Stima:** 30 minuti
**Dipendenze:** nessuna

**Obiettivo:** Il collector `whale` (Whale Alert RSS + Blockchair, TASK-804) è già implementato e indipendente dall'exchange, ma disabilitato di default. Il collector `sentiment` (CryptoCompare + NewsAPI, TASK-804) è anch'esso indipendente dall'exchange ma non è mai stato riverificato con OKX attivo — nei log notturni del 29-30/06 risultava intermittente per un problema DNS locale, non dell'endpoint.

**Modifiche:**
1. In `synthtrade/backend/.env`: `SCALPING_WHALE_ENABLED=true`
2. Verificare in log se la sola fonte Blockchair (senza `WHALE_ALERT_API_KEY`) produce dati utilizzabili, o se serve la key
3. Avviare una sessione paper/demo e osservare per 30-60 minuti se `sentiment` risponde regolarmente o se il problema DNS del 29-30/06 persiste

**Verifica di completamento (risultati live 14/07/2026):**
- `SCALPING_WHALE_ENABLED=true` applicato in `synthtrade/backend/.env` (verificato a runtime: `settings.scalping.SCALPING_WHALE_ENABLED == True`).
- Whale collector (Blockchair, no key): risponde con dati reali per BTC/LTC (`large_transfer_volume` popolato, es. BTC `volume≈992297`), ma per il simbolo operativo **OKB-EUR ritorna `None`** (OKB non è una chain supportata — BTC/LTC/ETH/BNB — e il fallback news CryptoCompare per categoria `okb` trova 0 headline con keyword "whale"). → La sola fonte Blockchair **non è sufficiente per OKB-EUR**: conferma la necessità di TASK-1154/1155 (Whale Alert API a pagamento) per coprire il simbolo reale.
- `[COVERAGE_REAL]` su OKB-EUR: `configurable_total` passa da **0.40 → 0.50** (whale ora nel denominatore). `responded_weight` non sale su OKB-EUR perché whale=None → whale resta in `no_response_transient` finché non risponde.
- Sentiment: risponde regolarmente (score=0.0, `news_count=10`, source=`cryptocompare+newsapi+rss`). Il problema DNS del 29-30/06 **non si ripresenta** → nessuna nota separata di robustezza richiesta per questo task.
- Nessun errore/eccezione propagata dallo ScoreEngine con whale abilitato.

**Nota per fase successiva:** il whale collector abilitato aumenta la coverage potenziale ma, su OKB-EUR, contribuisce 0 allo score reale fino a quando non viene aggiunta una fonte whale-aware per OKB (vedi TASK-1154/1155).

---

## Fase 2 — Collector nuovi, exchange-agnostici (priorità più alta per OKB-EUR)

Questi due collector funzionano su **qualunque** coppia spot OKX, incluso il simbolo attualmente in uso, perché non dipendono da un mercato futures. Sono il miglior rapporto sforzo/beneficio per colmare il vuoto lasciato da funding_rate/open_interest/long_short_ratio.

### TASK-1151 — OrderBookImbalanceCollector

**Status:** ✅ Done (14/07/2026)
**Priorità:** 🔴 Alta
**Stima:** 3-4 ore
**Dipendenze:** nessuna

**Note di completamento:**
- Collector implementato in `collectors/order_book_imbalance.py` (usa `/market/books`, pubblico, nessuna auth).
- Modello `OrderBookImbalance` (`models/intelligence.py:152`): `imbalance` clampato a [-1, +1].
- Wiring in `SignalScoreEngine`: peso provvisorio **0.15** in `DEFAULT_WEIGHTS`; `is_symbol_supported` sempre True (funziona su ogni spot OKX, incluso OKB-EUR).
- Log diagnostico `[COLLECTORS_DIAG_TEMP]` mostra `order_book_imbalance:on/OK` su OKB-EUR.
- Verifica live OKB-EUR: `imbalance ≈ -0.26` (più liquidità ask al momento del test) → coerente col segno.
- Test: `tests/scalping/test_order_book_imbalance.py` (16 test, tutti verdi) + fix `test_signal_score_engine.py::TestDefaultWeights` (pesi relativi, somma non vincolata a 1.0).
- Regressioni introdotte e risolte: `test_weights_sum_to_one`/`test_all_keys_present` aggiornati all'invariante "pesi relativi normalizzati". Suite scalping: **0 nuove regressioni** (48 fail pre-esistenti invariati, 184 pass).

**Endpoint:** `GET https://eea.okx.com/api/v5/market/books?instId={instId}&sz=20` — pubblico, nessuna autenticazione.

**Logica:**
```python
class OrderBookImbalanceCollector:
    """
    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
    imbalance > 0 → più liquidità bid → pressione rialzista
    imbalance < 0 → più liquidità ask → pressione ribassista
    Score: imbalance * 100, clampato a [-100, +100]
    """
    BASE_URL = "https://eea.okx.com"

    async def fetch(self, symbol: str, depth: int = 20) -> "OrderBookImbalanceSnapshot | None":
        ...  # somma quantità sui primi N livelli bid/ask, None se book vuoto o simbolo non trovato

    def is_symbol_supported(self, symbol: str) -> bool:
        return True  # funziona su ogni spot OKX per design
```

**Modello Pydantic:**
```python
class OrderBookImbalanceSnapshot(BaseModel):
    symbol: str
    bid_depth: Decimal
    ask_depth: Decimal
    imbalance: float  # -1.0 a +1.0
    timestamp: datetime
```

#### Red — Test
- [x] `test_fetch_success_balanced_book` — bid_depth ≈ ask_depth → imbalance ≈ 0
- [x] `test_fetch_success_bid_heavy` — bid_depth >> ask_depth → imbalance vicino a +1
- [x] `test_fetch_success_ask_heavy` — ask_depth >> bid_depth → imbalance vicino a -1
- [x] `test_fetch_empty_book` — book vuoto → `None` con log
- [x] `test_fetch_http_error` — 4xx/5xx → `None` con log, nessuna eccezione propagata
- [x] `test_imbalance_to_score_clamped` — 5 casi ai limiti (-1, -0.5, 0, 0.5, 1) → score in [-100, 100]
- [x] `test_is_symbol_supported_always_true`

#### Green — Implementazione
- [x] File `synthtrade/backend/app/scalping/intelligence/collectors/order_book_imbalance.py`
- [x] Wiring in `SignalScoreEngine.WEIGHTS` con peso provvisorio (0.15) — da ricalibrare in Fase 6
- [x] Nessuna dipendenza da futures o da altri collector

**Verifica di completamento:** in sessione su OKB-EUR, il collector risponde con dati reali (non `None`); l'`imbalance` calcolato confrontato a mano con lo stato dell'order book visibile su OKX UI nello stesso istante è coerente in segno.

---

### TASK-1152 — SpreadCollector

**Status:** ✅ Done (collector + modello; wiring INTENZIONALMENTE DISATTIVATO) (14/07/2026)
**Priorità:** 🟡 Media
**Stima:** 2 ore
**Dipendenze:** nessuna

**Decisione di design (confermata con Andrea):** implementato SOLO il collector + modello.
Nessun wiring nel weighted score (`SignalScoreEngine.DEFAULT_WEIGHTS` non contiene
`spread`): lo spread è non-direzionale (flag di cautela), non un bias bullish/bearish.
Il collector calcola, logga (`[COLLECTORS_DIAG_TEMP] spread ...`) e ritorna `SpreadSnapshot`,
ma non influenza le decisioni finché non si decide gate-vs-peso in `signal_aggregator.py`.
Injectabile via config in futuro senza refactor del collector.

**Endpoint:** `GET https://eea.okx.com/api/v5/market/ticker?instId={instId}` — già usato altrove nell'adapter (`get_ticker_price`), nessuna nuova connessione.

**Logica:**
```python
class SpreadCollector:
    """
    spread_pct = (ask - bid) / mid_price * 100
    Mantiene una media mobile (es. ultimi 20 campioni) per normalizzare:
    uno spread 3x la media recente è anomalo, non un valore assoluto arbitrario.

    NON è direzionale (non bullish/bearish) — è un flag di affidabilità/cautela.
    """
```

**Decisione di design da prendere prima di implementare (non assumere):** integrare nel weighted score come gli altri collector, oppure come moltiplicatore separato sul gate `tradeable` in `signal_aggregator.py`. Discutere con Andrea prima di scrivere il wiring finale — l'implementazione del collector stesso (calcolo spread + media mobile) è indipendente da questa decisione.

#### Red — Test
- [x] `test_fetch_success_normal_spread`
- [x] `test_fetch_success_anomalous_spread_vs_rolling_avg`
- [x] `test_fetch_http_error`
- [x] `test_rolling_average_window_size` — verifica che la finestra sia effettivamente 20 campioni, non cresca illimitatamente

#### Green — Implementazione
- [x] File `synthtrade/backend/app/scalping/intelligence/collectors/spread.py`
- [x] Modello `SpreadSnapshot` in `models/intelligence.py`
- [x] Wiring **provvisoriamente disattivato** dal weighted score (come deciso sopra) — il collector calcola e logga, non influenza ancora le decisioni

**Verifica di completamento:** spread calcolato confrontato con quello visibile su OKX UI; durante una finestra di bassa liquidità nota (notte, poco volume) lo spread relativo sale effettivamente.

---

## Fase 3 — Provider-aware refactor (funding/OI/long-short)

### TASK-1153 — CollectorAdapter provider-aware per funding_rate / open_interest / long_short_ratio

**Status:** Pending — *supersede TASK-1116.C e TASK-COLLECTOR-001*
**Priorità:** 🟡 Media (impatto nullo su OKB-EUR, alto se in futuro si opera su BTC-EUR/ETH-EUR)
**Stima:** 4-5 ore
**Dipendenze:** TASK-1116.B (già fatto — `FUTURES_SYMBOL_MAP` con `OKBEUR: None`)

**Obiettivo:** oggi i 3 collector chiamano direttamente `fapi.binance.com`, ignorando `settings.EXCHANGE_PROVIDER`. Per un simbolo con perpetual reale (es. BTC-EUR), questo significa che il dato non arriva mai, anche se OKX espone un endpoint nativo equivalente.

**Punto critico da tenere a mente:** il perpetual OKX è quotato in USDT (`BTC-USDT-SWAP`), non in EUR. Il funding rate/OI riflettono il sentiment sull'asset base (BTC), non sulla coppia EUR specifica — proxy valido ma va **documentato esplicitamente come tale**, non presentato come dato "per BTC-EUR" letterale.

**File coinvolti:**
- `synthtrade/backend/app/scalping/intelligence/collectors/open_interest.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/funding_rate.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`
- `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py` (wiring)
- `synthtrade/backend/app/execution/okx_exchange.py` (nuovi metodi read-only)

#### Red — Test
- [ ] `test_collector_adapter_interface_okx_btc_perpetual` — con `OKX_PERPETUAL_MAP["BTC"] = "BTC-USDT-SWAP"`, il collector chiama l'endpoint OKX nativo, non Binance
- [ ] `test_collector_adapter_okb_eur_returns_none_no_network_call` — per OKB-EUR, `is_symbol_supported()` ritorna `False` e **nessuna chiamata di rete viene tentata** (né Binance né OKX)
- [ ] `test_provider_switch_binance_legacy_unchanged` — con `EXCHANGE_PROVIDER=binance`, comportamento legacy invariato (nessuna regressione)
- [ ] `test_fake_adapter_get_open_interest_mocked` — fake adapter con `get_open_interest()` mockato, nessun 400 verso Binance
- [ ] `test_score_reweighted_when_collector_unavailable` — score ricalcolato correttamente quando il collector è strutturalmente assente

#### Green — Implementazione
1. **Interfaccia read-only** in `okx_exchange.py`:
   ```python
   OKX_PERPETUAL_MAP: dict[str, str | None] = {
       "BTC": "BTC-USDT-SWAP",
       "ETH": "ETH-USDT-SWAP",
       "OKB": None,  # nessun perpetual OKB su nessun exchange
   }

   async def get_open_interest(self, base_asset: str) -> float | None: ...
   async def get_funding_rate(self, base_asset: str) -> float | None: ...
   ```
2. **Refactor dei 3 collector**: accettano `adapter: ExchangeAdapterProtocol | None = None` nel costruttore
   - Se `adapter` fornito e `settings.EXCHANGE_PROVIDER == "okx"`: estrarre base asset dal symbol, guardare `OKX_PERPETUAL_MAP`, se non-`None` chiamare `adapter.get_open_interest(base_asset)`; se `None`, comportamento identico a oggi (unavailable, nessuna chiamata Binance)
   - Se `adapter=None`: fallback Binance legacy invariato
   - `Long/Short Ratio`: OKX non ha endpoint equivalente confermato — mantenere `is_symbol_supported() = False` sempre per provider OKX, in attesa di TASK-1158
3. **SignalScoreEngine wiring**: passare `adapter` ai collector in `get_or_create()`, leggendo `settings.EXCHANGE_PROVIDER`

**Acceptance criteria:**
- Sessione OKX su un simbolo con perpetual reale (BTC-EUR) non chiama mai Binance Futures per questi 3 collector
- Sessione OKX su OKB-EUR: comportamento invariato rispetto a oggi (unavailable, come da TASK-1116.B), zero chiamate di rete sprecate
- Log mostra esplicitamente `collector=okx_native` o `collector=structurally_unavailable`, mai un errore 400 silenzioso

---

## Fase 4 — Affidabilità dei collector esistenti ma fragili

### TASK-1154 — Sentiment collector: fallback affidabile

**Status:** Pending — *supersede TASK-COLLECTOR-002*
**Priorità:** 🟡 Media
**Dipendenze:** TASK-1150 (verifica preliminare già fatta)

**Problemi noti:** NewsAPI e CryptoCompare richiedono API key; RSS feed potrebbero essere bloccati o intermittenti (problema DNS già osservato).

**Soluzione:**
- Ordine di priorità: CryptoCompare (con key) → NewsAPI (con key) → RSS (fallback finale)
- Fallback testuale minimo basato su keyword "bull"/"bear" se tutte le fonti con key falliscono
- Cache 5 minuti per evitare rate limit
- Log compatto in caso di fallimento DNS ripetuto (una riga di warning dopo il primo fallimento consecutivo, non uno stack trace completo ogni minuto — stesso principio già notato per il rumore DNS FearGreed nel recap del 29-30/06)

#### Red — Test
- [ ] `test_priority_order_cryptocompare_first`
- [ ] `test_fallback_to_newsapi_when_cryptocompare_fails`
- [ ] `test_fallback_to_rss_when_both_key_sources_fail`
- [ ] `test_keyword_fallback_when_all_sources_fail`
- [ ] `test_cache_prevents_repeated_calls_within_5min`
- [ ] `test_dns_failure_logs_compact_warning_not_full_traceback`

### TASK-1155 — Whale collector: fonti OKX-compatibili

**Status:** Pending — *supersede TASK-COLLECTOR-003, parzialmente coperto da TASK-1150*
**Priorità:** 🟢 Bassa
**Dipendenze:** TASK-1150

**Obiettivo:** se dopo TASK-1150 il solo Blockchair (no API key) risulta insufficiente, aggiungere Whale Alert API come opzione a pagamento, con fallback su CryptoCompare news filtrato per keyword "whale".

### TASK-1156 — On-chain collector: fallback Blockchair

**Status:** Pending — *supersede TASK-COLLECTOR-004*
**Priorità:** 🟢 Bassa
**Dipendenze:** nessuna

**Soluzione:** priorità Dune (con key) → Blockchair (gratuito, no key). Per simboli EUR non-BTC/ETH, usare dati BTC/ETH come proxy macro con la stessa cautela di documentazione già applicata in TASK-1153.

---

## Fase 5 — Verifiche mirate

### TASK-1157 — Verifica CVD grace period

**Status:** Pending — *supersede TASK-COLLECTOR-005*
**Priorità:** 🟡 Media
**Dipendenza:** nessuna, solo osservazione

**Azioni:**
- Monitorare log per `"CVD grace period"` su una sessione live/demo di durata sufficiente a superare 100 trade nel trade stream
- Verificare se dopo il warmup il CVD inizia effettivamente a contribuire allo score (non solo a essere calcolato in background)
- Se dopo 2-3 sessioni il grace period non viene mai superato (volume insufficiente su OKB-EUR), valutare se abbassare la soglia o aggiungere fallback su OKX public trades con una finestra temporale invece che un conteggio di trade

**Output atteso:** una nota in questo piano (o task successivo) con il numero reale di minuti/ore necessari a superare il grace period su OKB-EUR — non un'ipotesi.

### TASK-1158 — Spike: esiste un equivalente OKX per Long/Short Ratio?

**Status:** Pending — *stesso contenuto già presente come TASK-1124 nel piano precedente (ora TASK-1158), rinumerato per coerenza*
**Priorità:** 🟢 Bassa
**Stima:** 1 ora (solo verifica documentale/empirica, no implementazione)

**Obiettivo:** verificare su `docs-v5` OKX aggiornata se esiste una famiglia di endpoint tipo `rubik/stat` equivalente al long/short ratio Binance. Se esiste, aprire un task di implementazione dedicato (probabilmente dentro TASK-1153). Se non esiste, documentarlo esplicitamente come strutturalmente assente per design — non lasciarlo "da fare" a tempo indeterminato.

---

## Fase 6 — Ricalibrazione pesi (solo a valle di dati reali)

### TASK-1159 — Ricalibrazione pesi SignalScoreEngine + nota cadenza micro-swing

**Status:** Pending
**Priorità:** 🔴 Alta, ma **bloccata** finché le Fasi 1-5 non sono attive per almeno 2-3 sessioni reali
**Dipendenze:** TASK-1150, 1151, 1152, 1153, 1154, 1157 (tutte, anche solo parzialmente osservate)

**Perché aspettare:** i pesi provvisori assegnati nelle fasi precedenti (es. 0,15 per Order Book Imbalance) sono placeholder. Assegnare pesi definitivi "a intuito" prima di aver visto il comportamento reale ripete esattamente l'errore già commesso in passato con la soglia `signal_strength_threshold` (cambiata 5 volte in una sessione senza meccanismo di decadimento, vedi `supervisor-analysis.md`).

**Metodologia:**
1. Raccogliere 2-3 sessioni reali (paper o demo) dopo che almeno le Fasi 1-3 sono attive
2. Estrarre i log `[COVERAGE_REAL]` e `[ScoreEngine] breakdown raw` (già esistenti da TASK-841/1125)
3. Per ogni collector, misurare: frequenza di risposta reale, correlazione empirica (anche solo qualitativa in questa fase) tra il segnale del collector e l'esito dei trade dove `signal_log_id` è popolato (vedi `signal_outcome_by_strategy_regime`, già esistente da TASK-897)
4. Redistribuire i pesi in `SignalScoreEngine.WEIGHTS` sui numeri osservati, non sui placeholder

**Nota esplicita sul pivot micro-swing (da applicare in questa fase, non prima):**
Con 10-30 trade/giorno invece di centinaia, la cadenza naturale di alcuni collector è già allineata al nuovo profilo (Fear&Greed 1x/giorno, sentiment/onchain a minuti). Il CVD, pensato per catturare pressione istantanea tipica dello scalping ad alta frequenza, è il candidato più probabile a un **ridimensionamento di peso** in favore di segnali più strutturali come l'Order Book Imbalance calcolato su finestre più larghe (es. media mobile invece di snapshot istantaneo). Questa non è una decisione da prendere ora — è un'ipotesi da verificare con i dati raccolti al punto 3 sopra.

**Acceptance criteria:**
- Nuovi pesi in `SignalScoreEngine.WEIGHTS` derivati da un log reale citato esplicitamente nel commit/PR (data, sessione, numero di cicli osservati)
- Nessun peso cambiato "perché sembra giusto" senza riferimento a un dato osservato
- Documentata esplicitamente la decisione su CVD (ridotto, invariato, o rimosso) con la motivazione basata sui dati

---

## Riepilogo task per numerazione (per aggiornare TASKS.md)

| Task | Sostituisce | Fase | Priorità | Dipendenze |
|------|-------------|------|----------|------------|
| TASK-1119/1125 | — | 0 | ✅ Done | — |
| TASK-1150 | (invariato) | 1 | 🔴 Alta | nessuna |
| TASK-1151 | (invariato) | 2 | ✅ Done | nessuna |
| TASK-1152 | (invariato) | 2 | ✅ Done (collector; wiring OFF) | nessuna |
| TASK-1153 | TASK-1116.C, TASK-COLLECTOR-001 | 3 | 🟡 Media | TASK-1116.B (done) |
| TASK-1154 | TASK-COLLECTOR-002 | 4 | 🟡 Media | TASK-1150 |
| TASK-1155 | TASK-COLLECTOR-003 | 4 | 🟢 Bassa | TASK-1150 |
| TASK-1156 | TASK-COLLECTOR-004 | 4 | 🟢 Bassa | nessuna |
| TASK-1157 | TASK-COLLECTOR-005 | 5 | 🟡 Media | nessuna |
| TASK-1158 | TASK-1124 (piano precedente) | 5 | 🟢 Bassa | nessuna |
| TASK-1159 | — | 6 | 🔴 Alta (bloccata) | 1150, 1151, 1152, 1153, 1154, 1157 |

**Da marcare esplicitamente `Superseded` in `docs/TASKS.md`:** TASK-1116.C, TASK-COLLECTOR-001, TASK-COLLECTOR-002, TASK-COLLECTOR-003, TASK-COLLECTOR-004, TASK-COLLECTOR-005, e il vecchio TASK-1124 di `collector-abbondanza-piano-okx.md` (rinominato TASK-1158 qui per evitare confusione con la numerazione già usata altrove).

---

## Esplicitamente fuori scope per questo piano

- Nessuna modifica a `RegimeDetector`, `StrategySelector`, o alle strategie tecniche esistenti
- Nessuna modifica a SL/TP (già gestito da TASK-OKX-RECAL, separato)
- Nessuna decisione definitiva sul cambio di simbolo operativo (resta OKB-EUR finché non diversamente deciso)
- La ricalibrazione strategica più ampia (quali strategie usare nel nuovo profilo micro-swing) è dichiaratamente un passo successivo, da affrontare solo dopo che questo piano ha dato al Supervisor dati sufficienti per decidere bene
