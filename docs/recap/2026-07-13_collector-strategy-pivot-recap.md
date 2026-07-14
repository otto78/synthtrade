# SynthTrade — Recap Sessione: Pivot Micro-Swing e Consolidamento Piano Collector

**Data:** 13 luglio 2026
**Contesto:** analisi documentale (nessun codice toccato in questa sessione) — riordino del tema "collector intelligence" alla luce delle decisioni pregresse (chiusura migrazione Bybit, ricalibrazione SL/TP OKX) e di una decisione di prodotto nuova (pivot di frequenza operativa).

---

## 1. Decisioni pregresse che inquadrano questo lavoro

| Decisione | Fonte | Stato |
|---|---|---|
| OKX confermato unico exchange operativo | `TASKS.md` "Migrazione Bybit — CHIUSA" | Definitivo — accesso API custom bloccato per account EU retail su Bybit, nessuna alternativa disponibile |
| SL/TP ricalibrati su fee OKX reali | `docs/plans/okx-sl-tp-recalibration-task.md` (TASK-OKX-RECAL) | In esecuzione — Opzione B: SL netto 1,05%, TP netto 1,55%, R:R 1,48:1, su round-trip fee reale 0,70% (taker 0,35% x2) |
| **Nuova in questa sessione:** pivot di frequenza operativa | Indicazione diretta di Andrea | Da questo momento è il quadro di riferimento per tutto il lavoro sui collector |

### 1.1 — Il pivot: da scalping puro a "micro swing"

Con SL/TP allargati di oltre 3x rispetto ai valori originali (0,3%/0,5% → 1,05%/1,55%), il sistema non può più operare come scalping ad alta frequenza. Il nuovo target dichiarato è **10-30 trade al giorno**, non più centinaia. Questo non è un dettaglio quantitativo: cambia la natura stessa di cosa deve fare bene il sistema.

**Perché i collector diventano più critici ora, non meno:**

- Nello scalping puro ad alta frequenza, un singolo segnale sbagliato costa poco: lo SL è stretto, i trade sono tanti, la legge dei grandi numeri smussa gli errori nel tempo.
- Nel micro swing, ogni trade porta un rischio per-trade circa 3,5x più grande (SL 1,05% vs 0,3%) e ci sono 10-20x meno trade al giorno per compensare un errore sistematico di lettura del mercato.
- Conseguenza diretta: **la qualità e l'abbondanza dell'informazione che arriva al Supervisor prima di ogni decisione conta di più**, non di meno. Non ci si può più permettere di prendere decisioni con 1 collector su 8 funzionante.

Questo NON è ancora una richiesta di modificare le strategie tecniche esistenti (regime detector, strategy selector, entry logic) — quello è dichiaratamente un passo successivo ("poi valuteremo aggiornamento e modifiche delle strategie da scegliere"). Lo scope di questa sessione è **solo** l'infrastruttura di intelligence che alimenta il Supervisor.

---

## 2. Stato reale dei collector (verificato da log/handoff, non da assunzioni)

Fonte: `docs/HANDOFF.md` (ultimo aggiornamento 2026-07-13), `docs/TASKS.md` TASK-1116.B/1125, `docs/analysis/collector-intelligence-analysis.md` (versione precedente).

| Collector | Stato reale per il simbolo attuale (OKB-EUR, spot senza perpetual) | Causa |
|---|---|---|
| Fear & Greed | 🟢 Funzionante | alternative.me, indipendente da exchange, con cache fallback |
| CVD | 🟡 Incerto | dipende dal trade stream OKX WS; soglia grace period 100 trade mai confermata osservata in produzione |
| Funding Rate | 🔴 Strutturalmente assente (corretto per design) | OKB non ha mercato perpetual — graceful skip da TASK-1116.B, non un bug |
| Open Interest | 🔴 Strutturalmente assente (corretto per design) | idem |
| Long/Short Ratio | 🔴 Strutturalmente assente | idem, e nessun equivalente OKX nativo è mai stato verificato (spike mai eseguito) |
| Sentiment | 🔴 Non funzionante | dipende da API key CryptoCompare/NewsAPI, mai riverificato con OKX attivo |
| Whale Alert | 🔴 Disabilitato di default | `SCALPING_WHALE_ENABLED=false`, mai attivato in produzione |
| On-Chain | 🔴 Non funzionante | dipende da Dune API key, peso 0 nello score attuale |

**Sintesi cruda: 1 collector su 8 solidamente funzionante (Fear & Greed) per il simbolo oggi in uso.** TASK-1125 (diagnostica coverage, log `[COVERAGE_REAL]`) è stato completato e dà finalmente visibilità oggettiva su questo — ma nessun fix comportamentale è stato ancora eseguito dopo la diagnosi.

---

## 3. Problema di roadmap trovato: due piani paralleli mai unificati

| Piano | File | Task | Stato |
|---|---|---|---|
| Piano A | `docs/plans/collector-abbondanza-piano-okx.md` | TASK-1120 → TASK-1124 | Tutti `Pending`, mai eseguiti |
| Piano B | `docs/TASKS.md` sezione "EPICA COLLECTOR IMPROVEMENT" | TASK-COLLECTOR-001 → 005 | Tutti `Pending`, mai eseguiti |

I due piani si sovrappongono parzialmente (entrambi trattano il refactor provider-aware di funding_rate/open_interest/long_short_ratio) ma non si citano a vicenda e usano numerazioni diverse — rischio concreto di duplicare lavoro o di implementare due volte la stessa interfaccia con forme diverse.

**Azione presa in questa sessione:** consolidato tutto in un unico piano — `docs/plans/collector-intelligence-implementation-plan.md` — con una numerazione unica (TASK-1120→1125 mantenuti come già noti e compatibili, nuovi task da TASK-1140 in poi per evitare collisione con TASK-1126-1129 già usati per altri fix OKX nel changelog). TASK-1116.C e TASK-COLLECTOR-001→005 vanno marcati come **superseded** dal nuovo piano.

---

## 4. Priorità rivista alla luce del pivot micro-swing

L'ordine di implementazione proposto nel piano consolidato tiene conto esplicitamente del nuovo contesto:

1. **Quick win zero-rischio** (whale enable + verifica sentiment) — 30 minuti, nessun codice nuovo
2. **Collector nuovi exchange-agnostici** (Order Book Imbalance, Spread) — il miglior rapporto sforzo/beneficio per un simbolo spot-only come OKB-EUR, e restano validi anche se in futuro si cambiasse coppia
3. **Refactor provider-aware** dei 3 collector Binance-Futures-bound — utile solo per simboli con perpetual reale (BTC-EUR, ETH-EUR); per OKB-EUR restano strutturalmente assenti per design, e va documentato come tale, non "da fare"
4. **Affidabilità sentiment/whale/onchain** — fix mirati, non un intero collector nuovo
5. **Verifica CVD grace period** — capire se dopo il warmup contribuisce davvero
6. **Ricalibrazione pesi finale** — solo dopo che 1-5 sono attivi per qualche sessione reale, con numeri osservati (log `[COVERAGE_REAL]`), non a intuito

### Nota specifica sul pivot (per la fase di ricalibrazione pesi, non azionabile ora)

Con 10-30 trade/giorno invece di centinaia, la cadenza naturale di alcuni collector è già ben allineata al micro-swing: Fear&Greed (1x/giorno), sentiment/onchain (a minuti) non hanno bisogno di modifiche di frequenza. Il CVD, pensato per catturare pressione istantanea tipica dello scalping puro, potrebbe invece perdere peso relativo a favore di segnali più strutturali come l'Order Book Imbalance calcolato su finestre più larghe. **Questa è una nota per la Fase 6 del piano consolidato (ricalibrazione pesi), non un'azione da prendere ora** — prima servono i dati reali dei nuovi collector.

---

## 5. Collegamento frontend (nota, fuori scope per questo giro)

Quando Order Book Imbalance e Spread saranno implementati, il componente Angular `MarketIntelPanel` andrà esteso per mostrarli (oggi mostra solo funding rate, OI, CVD, Fear&Greed, Long/Short ratio — vedi `docs/plans/scalping-module-plan.md` §3). Non incluso in questo giro di lavoro backend, ma segnalato per non perderlo di vista quando si passerà al lavoro frontend.

---

## 6. File prodotti in questa sessione

1. Questo recap
2. `docs/analysis/collector-intelligence-analysis.md` — versione aggiornata, sostituisce la precedente
3. `docs/plans/collector-intelligence-implementation-plan.md` — piano consolidato pronto per l'implementazione (TASK-1120→1145)

## 7. Prossimo passo immediato

Iniziare da TASK-1120 (quick win, zero rischio) nel piano consolidato — verificare in log che il coverage reale (TASK-1125, già attivo) salga dopo l'attivazione di whale, poi procedere in sequenza. Nessuna sessione live con size significative dovrebbe partire prima che almeno le Fasi 1-2 del piano consolidato siano attive, dato il rischio per-trade più alto introdotto dal pivot micro-swing.
