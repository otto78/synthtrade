# Collector Intelligence — Stato e Piano

> **Versione:** 2.0 — 13 luglio 2026 (sostituisce la versione precedente)
> **Tema trasversale** che emerge da: `docs/recap/2026-06-27_strategie-scalping.md` (in MASTER_RECAP), `docs/recap/MASTER_RECAP.md` §3 (bug #19), `docs/recap/2026-07-10_collector-coverage-diagnostica.md` (TASK-1119/1125), `docs/HANDOFF.md` (stato 2026-07-13).
> **Piano di implementazione:** `docs/plans/collector-intelligence-implementation-plan.md` (nuovo, consolida i due piani precedenti — vedi §5).
> **Recap decisionale:** `docs/recap/2026-07-13_collector-strategy-pivot-recap.md`.

---

## 0. Quadro di riferimento aggiornato (leggere prima del resto)

Due decisioni pregresse cambiano completamente le priorità rispetto alla versione 1.0 di questa analisi:

1. **OKX è l'unico exchange operativo.** La migrazione a Bybit è stata chiusa (`TASKS.md`, "Migrazione Bybit — CHIUSA") perché l'accesso API custom è bloccato per account EU retail. Ogni riferimento residuo a "verificare equivalente Bybit" nei documenti più vecchi è storico, non più attuabile.
2. **Le fee reali OKX (0,20% maker / 0,35% taker) hanno imposto una ricalibrazione SL/TP** (`docs/plans/okx-sl-tp-recalibration-task.md`, TASK-OKX-RECAL): SL netto ~1,05%, TP netto ~1,55%, invece dei precedenti 0,3%/0,5%. Questo sposta il sistema da uno **scalping puro** (centinaia di trade/giorno, movimenti minimi) a un profilo **micro swing**: **10-30 trade/giorno**, movimenti più ampi necessari per superare il costo fisso di round-trip (0,70%).

**Implicazione diretta per i collector:** con SL/TP ~3,5x più larghi e 10-20x meno trade al giorno, ogni decisione del Supervisor comporta un rischio per-trade molto più alto e non viene più "mediata" da un grande numero di trade. La qualità e l'abbondanza dei dati di intelligence prima di ogni decisione contano **di più**, non di meno, rispetto a quando questa analisi è stata scritta la prima volta. Questo documento e il piano collegato sono stati riscritti tenendo conto di questo.

---

## 1. Stato reale attuale (verificato, non stimato)

Il sistema opera oggi su **OKB-EUR**, una coppia spot senza mercato perpetual/futures associato su nessun exchange. Questo è strutturalmente rilevante: 3 degli 8 collector dipendono da dati futures e per questo simbolo non risponderanno mai, indipendentemente da qualunque fix di codice.

| Collector | Stato reale per OKB-EUR | Score contribution nominale | Causa |
|-----------|-------------------------|------------------------------|-------|
| Fear & Greed Index | 🟢 Funzionante | 0,10-0,15 | alternative.me, indipendente da exchange, con cache fallback su errore DNS |
| CVD (Cumulative Volume Delta) | 🟡 Incerto — da verificare | 0,20-0,25 | dipende dal trade stream pubblico OKX WS; grace period 100 trade mai osservato confermato in una sessione live reale |
| Funding Rate | 🔴 Strutturalmente assente (**per design, non bug**) | 0,10-0,20 | OKB non ha perpetual su nessun exchange — graceful skip già corretto da TASK-1116.B |
| Open Interest | 🔴 Strutturalmente assente (**per design**) | 0,10-0,15 | idem |
| Long/Short Ratio | 🔴 Strutturalmente assente (**per design**, probabile) | 0,10-0,15 | idem; inoltre non è mai stato verificato se OKX espone un equivalente nativo (spike mai eseguito, vedi TASK-1124/1145.C) |
| Sentiment (news/social) | 🔴 Non funzionante | 0,05-0,10 | dipende da API key CryptoCompare/NewsAPI, mai riverificato con sessione OKX attiva |
| Whale Alert | 🔴 Disabilitato di default | 0,10 | `SCALPING_WHALE_ENABLED=false`, mai attivato in produzione nonostante il codice esista da TASK-804 |
| On-Chain Metrics | 🔴 Non funzionante | 0,00-0,10 | dipende da Dune API key; peso attuale 0 nello score |

**Totale reale per OKB-EUR: 1 collector solidamente funzionante su 8 (Fear & Greed).** Il CVD è un'incognita da chiarire con la prossima fase, non una funzionalità confermata.

Per un simbolo con perpetual reale (es. BTC-EUR, ETH-EUR), lo stato sarebbe diverso: funding_rate/open_interest potrebbero funzionare usando il perpetual USDT dello stesso asset base come proxy (vedi §3.3 del piano). Ma il simbolo operativo oggi resta OKB-EUR.

---

## 2. Impatto pratico (aggiornato per il contesto micro-swing)

- Il SignalScoreEngine lavora oggi, nella pratica, con 1-2 collector su 8 per il simbolo in uso
- Con SL/TP allargati e meno trade/giorno, un Supervisor che decide su 1-2 segnali deboli espone il capitale a un rischio per-trade significativo senza reale conferma multi-fonte
- Le decisioni di Intelligence sono quindi oggi strutturalmente sotto-informate rispetto a quanto richiesto dal nuovo profilo di rischio del sistema
- TASK-1125 (completato) fornisce finalmente la misura oggettiva di questo problema tramite il log `[COVERAGE_REAL]` — ma la misura da sola non risolve nulla, serve l'implementazione dei collector mancanti

---

## 3. Cosa è recuperabile e come — sintesi (dettaglio nel piano di implementazione)

### 3.1 Recuperabile senza nuovo codice (quick win)
- **Whale Alert**: codice esiste da TASK-804, mai attivato. Basta `SCALPING_WHALE_ENABLED=true` + verifica se la sola fonte Blockchair (senza API key) basta.
- **Sentiment**: codice esiste, va solo riverificato se risponde con OKX attivo (nessuna dipendenza nota da Binance).

### 3.2 Recuperabile con nuovi collector exchange-agnostici (massimo impatto per spot-only)
Questi funzionano su **qualunque** coppia spot OKX, incluso OKB-EUR, perché non dipendono da un mercato futures:
- **Order Book Imbalance**: squilibrio bid/ask dall'order book pubblico OKX (`GET /api/v5/market/books`), nessuna autenticazione richiesta
- **Spread relativo**: proxy di liquidità/incertezza dal ticker pubblico OKX, già usato altrove nell'adapter

Questi due collector sono la priorità più alta per il simbolo attualmente in uso, perché colmano il vuoto lasciato dai 3 collector strutturalmente assenti (funding/OI/long-short) con dati sempre disponibili.

### 3.3 Recuperabile solo per simboli con perpetual reale
- Funding Rate / Open Interest via endpoint OKX nativo (`/api/v5/public/funding-rate`, `/api/v5/public/open-interest`), usando il perpetual USDT dell'asset base come proxy — applicabile solo a BTC-EUR/ETH-EUR e simili, non a OKB-EUR

### 3.4 Da verificare, esito incerto
- Long/Short Ratio: nessun equivalente OKX confermato nella documentazione consultata finora — richiede uno spike di verifica prima di aprire un task di implementazione, per non promettere qualcosa che potrebbe non esistere

### 3.5 CVD — verifica, non nuovo sviluppo
Il codice esiste ed è wired al trade stream OKX pubblico. Manca solo la conferma empirica che, dopo il grace period di 100 trade, il collector contribuisca effettivamente allo score in una sessione reale.

---

## 4. Priorità di fix (aggiornata per il contesto micro-swing)

| # | Azione | Impatto | Rischio | Rif. task |
|---|--------|---------|---------|-----------|
| 1 | Whale enable + verifica sentiment | Medio, costo quasi zero | Nessuno | TASK-1120 |
| 2 | Order Book Imbalance Collector | Alto — copre il vuoto strutturale per spot-only | Basso | TASK-1121 |
| 3 | Spread Collector | Medio | Basso | TASK-1122 |
| 4 | CollectorAdapter provider-aware (funding/OI/long-short) | Alto per simboli con perpetual, nullo per OKB-EUR | Medio | TASK-1140 |
| 5 | Affidabilità sentiment/whale/onchain (fallback robusti) | Medio | Basso | TASK-1141/1142/1143 |
| 6 | Verifica CVD grace period | Medio — chiarisce un'incognita aperta da settimane | Nessuno (solo osservazione) | TASK-1144 |
| 7 | Spike long/short ratio OKX | Basso — solo per chiudere la domanda aperta | Nessuno | TASK-1145.C |
| 8 | Ricalibrazione pesi SignalScoreEngine | Alto — ma solo dopo dati reali da 1-7 | Medio se fatta a intuito, basso se fatta su log osservati | TASK-1145 |

---

## 5. Nota storica — due piani precedenti, ora consolidati

Fino a questa revisione esistevano due documenti di pianificazione paralleli e mai unificati:

- `docs/plans/collector-abbondanza-piano-okx.md` (TASK-1120 → TASK-1124)
- `docs/TASKS.md`, sezione "EPICA COLLECTOR IMPROVEMENT" (TASK-COLLECTOR-001 → 005)

Entrambi trattavano parzialmente lo stesso lavoro (refactor provider-aware dei collector futures-bound) con numerazioni diverse, senza incrociarsi. **Sono stati consolidati in un unico piano**: `docs/plans/collector-intelligence-implementation-plan.md`. I vecchi TASK-COLLECTOR-001→005 e TASK-1116.C vanno considerati `Superseded` — il lavoro descritto vive ora nei TASK-1140→1145 del piano consolidato.

---

## 6. Collegamento con task (aggiornato)

| Task | Cosa | Stato | Priorità |
|------|------|-------|----------|
| TASK-1119/1125 | Diagnostica coverage reale per simbolo | ✅ Done | — (prerequisito già soddisfatto) |
| TASK-1120 | Whale enable + verifica sentiment | Pending | 🔴 Alta — zero rischio |
| TASK-1121 | OrderBookImbalanceCollector | Pending | 🔴 Alta |
| TASK-1122 | SpreadCollector | Pending | 🟡 Media |
| TASK-1140 | CollectorAdapter provider-aware (funding/OI/long-short) — *supersede TASK-1116.C, TASK-COLLECTOR-001* | Pending | 🟡 Media (nulla per OKB-EUR, alta se si opera su BTC/ETH) |
| TASK-1141 | Sentiment reliability fallback — *supersede TASK-COLLECTOR-002* | Pending | 🟡 Media |
| TASK-1142 | Whale collector fonti OKX-compatibili — *supersede TASK-COLLECTOR-003* | Pending | 🟢 Bassa (parzialmente coperto da TASK-1120) |
| TASK-1143 | On-chain collector fallback Blockchair — *supersede TASK-COLLECTOR-004* | Pending | 🟢 Bassa |
| TASK-1144 | Verifica CVD grace period — *supersede TASK-COLLECTOR-005* | Pending | 🟡 Media |
| TASK-1145 | Ricalibrazione pesi + nota cadenza micro-swing | Pending | 🔴 Alta, ma solo a valle di 1120-1144 |

---

**Ultima modifica:** 2026-07-13 — consolidamento post pivot micro-swing e chiusura migrazione Bybit.
