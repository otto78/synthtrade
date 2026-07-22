# SynthTrade — Design Tecnico: Time-Stop Interesse-Based per Short OKX (v2, con formule)

> **Data:** 21 luglio 2026
> **Sostituisce/estende:** `2026-07-21_okx-short-selling-analysis-recap.md` (le sezioni su deprecazione doc e lista API restano valide e sono riportate qui aggiornate; le sezioni su time-stop e margine sono ora finalizzate)
> **Decisioni chiuse in questa sessione:** tasso di interesse **fisso** (bloccato all'apertura del trade, non rivalutato), margine **isolated** (non cross), meccanismo **B/D con buffer rolling 24h**.
> **Stato:** design completo, **zero codice scritto**. Pronto per spike di verifica empirica prima dell'implementazione.

---

## 0. Executive summary (leggi questo se hai poco tempo)

Il meccanismo funziona così: ogni ora (finché l'app gira), ricalcoli SL/TP del bracket OKX assumendo che l'interesse continuerà a maturare per altre 24h oltre a quelle già trascorse. Questo "spinge in avanti" il bracket in modo conservativo: se il PC si spegne subito dopo un refresh, il bracket piazzato resta comunque sicuro per le successive 24h di silenzio. Il risultato pratico: lo **SL si restringe nel tempo** (l'interesse consuma parte del budget di perdita accettato) e il **TP si allontana nel tempo** (l'interesse consuma parte del profitto netto) — ma il processo è **auto-limitante**: se il prezzo non aiuta, prima o poi lo SL effettivo tocca zero e il sistema chiude comunque, garantendo un tempo massimo di detenzione finito e calcolabile in anticipo.

---

## 1. Formule complete (layer per layer)

Il calcolo del prezzo di SL/TP per uno short passa attraverso **4 layer** che si applicano in cascata. Ognuno esiste già in parte nel vostro codice (per il long) tranne il layer 3-4, che è nuovo.

### Layer 1 — Target netti configurati (invariato, decisione presa: stessi valori del long)

```
SL_net_target = 1.05%     (da TASK-OKX-RECAL, salvo variazioni del Supervisor)
TP_net_target = 1.55%     (idem)
```

### Layer 2 — Aggiustamento fee (riuso esatto di `_net_to_gross_pct` già esistente)

Lo spot margin OKX usa **lo stesso fee schedule dello spot puro** (maker 0,20% / taker 0,35%, stesso account). Il round-trip per uno short (entry sell market + exit buy market al trigger) è identico ai 0,70% già noti per il long:

```
SL_gross_fee_only = |_net_to_gross_pct(SL_net_target, fee_taker, fee_taker)|
TP_gross_fee_only = |_net_to_gross_pct(TP_net_target, fee_taker, fee_taker)|
```

Con i valori attuali (fee taker 0,35% simmetrica), questo dà gli **stessi identici numeri già calcolati per il long in TASK-OKX-RECAL, Opzione B**:

```
SL_gross_fee_only ≈ 0,35%
TP_gross_fee_only ≈ 2,26%
```

Questi sono i valori "di partenza", **prima** di considerare l'interesse. Sono statici per tutta la vita del trade (la fee è nota e fissa a priori).

### Layer 3 — Interesse proiettato (nuovo, il cuore del meccanismo)

**Tasso orario, bloccato all'apertura** (decisione presa: no rivalutazione durante il trade):

```
rate_hourly = APR_al_open / 365 / 24
```

`APR_al_open` va letto una volta, all'apertura del trade, da `GET /api/v5/public/interest-rate-loan-quota?ccy={base_asset}` (endpoint pubblico, nessuna autenticazione).

**A ogni refresh orario** (finché l'app gira), calcoli l'interesse **proiettato** includendo il buffer di sicurezza:

```
elapsed_real_h(t) = ore trascorse dall'apertura del trade fino a questo refresh
BUFFER_HOURS = 24   (parametro configurabile, default 24 — copre una notte di PC spento)

interest_projected_pct(t) = rate_hourly × (elapsed_real_h(t) + BUFFER_HOURS)
```

**Nota importante:** il **primo bracket**, piazzato a t=0 (apertura trade), usa già `elapsed_real_h(0) = 0`, quindi `interest_projected_pct(0) = rate_hourly × BUFFER_HOURS` — **non parte "nudo"**, è già scontato per le prime 24h da subito. Questo chiude il buco di sicurezza della primissima ora che avevamo identificato come rischio nella sessione precedente.

### Layer 4 — Soglie effettive (il meccanismo D — SL si restringe, TP si allontana)

```
SL_effective_gross(t) = SL_gross_fee_only − interest_projected_pct(t)
TP_effective_gross(t) = TP_gross_fee_only + interest_projected_pct(t)
```

### Layer 5 — Prezzi del bracket (direzione invertita rispetto al long, come per ogni short)

```
SL_price(t) = entry_price × (1 + SL_effective_gross(t) / 100)     [SL sopra entry]
TP_price(t) = entry_price × (1 − TP_effective_gross(t) / 100)     [TP sotto entry]
```

`entry_price` resta **sempre il prezzo di apertura originale**, mai il prezzo corrente — il calcolo è sempre "quanto ho guadagnato/perso rispetto a dove sono entrato", coerente con la semantica P&L esistente in tutto il resto del sistema.

### Layer 6 — Floor guard (caso limite, protezione obbligatoria)

Se `SL_effective_gross(t) ≤ 0` (l'interesse proiettato ha già superato l'intero budget di perdita), **il bracket diventerebbe invalido** (SL dalla parte sbagliata dell'entry — stesso tipo di bug già preso una volta con sCode 51280 sul long, da non ripetere). In questo caso:

```
if SL_effective_gross(t) <= FLOOR_MIN_PCT:   # FLOOR_MIN_PCT es. 0.02%, piccolo margine di sicurezza
    → chiudi immediatamente a mercato
    → exit_reason = "stop_loss_interest"
```

### Gate pre-apertura (validazione obbligatoria PRIMA di aprire lo short)

Se il solo buffer di 24h consuma già più del budget SL disponibile, il meccanismo non è compatibile col tasso di interesse corrente — **non aprire lo short**:

```
if (rate_hourly × BUFFER_HOURS) >= SL_gross_fee_only:
    → BLOCCA apertura short
    → motivo: "buffer di sicurezza (24h) incompatibile col tasso di interesse attuale per questo asset"
```

---

## 2. Esempio numerico completo (illustrativo — tasso reale da verificare empiricamente)

Assumo APR = 15% (ordine di grandezza plausibile per un major in condizioni normali, **non un dato OKX reale verificato** — va sostituito con quanto letto da `interest-rate-loan-quota` al primo spike).

```
rate_hourly = 15 / 365 / 24 = 0,0017123 %/ora
SL_gross_fee_only = 0,35%
TP_gross_fee_only = 2,26%
BUFFER_HOURS = 24
```

**Gate pre-apertura:** `24 × 0,0017123% = 0,0411%` < `0,35%` → ✅ OK, si può aprire.

| Ore reali trascorse | interest_projected (con buffer +24h) | SL_effective | TP_effective | Nota |
|---|---|---|---|---|
| 0 (apertura) | 0,0411% | 0,3089% | 2,3011% | primo bracket, già scontato |
| 24h | 0,0822% | 0,2678% | 2,3422% | refresh dopo 1 giorno |
| 100h (~4,2gg) | 0,2123% | 0,1377% | 2,4723% | |
| **180h (~7,5gg)** | **0,3493%** | **0,0007%** | **2,6093%** | **SL effettivo ≈ 0 → floor guard, chiusura forzata** |

**Tempo massimo di detenzione in questo scenario: ~180 ore, circa 7,5 giorni.** Questo è il worst case "prezzo perfettamente fermo" — se il prezzo si muove anche solo un po' a vostro favore, il TP arriva prima; se si muove contro, lo SL "vero" (da prezzo) arriva prima ancora.

**Formula generale per il tempo massimo di detenzione** (utile per stimare l'ordine di grandezza prima di aprire):

```
elapsed_max_h = SL_gross_fee_only / rate_hourly − BUFFER_HOURS
```

Con SL_gross_fee_only=0,35% e rate_hourly=0,0017123%: `0,35/0,0017123 − 24 ≈ 204,4 − 24 = 180,4 ore` ✓ coerente con la tabella.

**Cosa succede a tassi più alti (stress):** con APR=50%, `rate_hourly=0,0057%`, `elapsed_max_h = 0,35/0,0057 − 24 ≈ 61,4 − 24 = 37,4 ore` (~1,5 giorni) — il meccanismo si autoregola, tempi più brevi quando i tassi sono più alti, esattamente il comportamento desiderato.

---

## 3. Margine isolated — implicazioni pratiche e collaterale necessario

### 3.1 — Perché isolated è la scelta giusta (confermato da doc ufficiale)

Con isolated, il rischio di ogni posizione è **segregato**: se una posizione short va in liquidazione, non intacca il resto del saldo. Con cross, tutto il saldo disponibile fa da garanzia condivisa per tutte le posizioni aperte — più rischioso in caso di errore o bug, esattamente il tipo di isolamento del danno che volete per un sistema ancora in fase di test.

### 3.2 — Le soglie di rischio reali OKX (confermate da documentazione ufficiale)

```
Margin ratio ≥ 300%  → sicuro, nessun alert
Margin ratio 100-300% → zona di allerta liquidazione ("liquidation alert")
Margin ratio ≤ 100%  → liquidazione forzata (parziale o totale)
```

Il margin ratio si abbassa sia per movimento avverso di prezzo, sia — rilevante per voi — per **erosione da interesse accumulato**, che riduce l'equity della posizione isolata nel tempo esattamente come farebbe un piccolo movimento di prezzo contrario.

### 3.3 — Quanto collaterale serve per un trade di prova da 20€

**Risposta onesta: non ho un numero OKX certificato da questa sessione** — la maintenance margin ratio esatta per BTC-EUR/OKB-EUR in isolated mode dipende dal "position tier" (più borrow = tier più alto = margine richiesto più alto), verificabile solo con l'endpoint dedicato (vedi §4, nuovo endpoint aggiunto). Quello che posso darvi è una metodologia conservativa:

1. **Leva bassa** — impostate la leva più bassa disponibile per l'asset via `set-leverage` (idealmente 1x-2x, non di più). Con leva bassa, il collaterale richiesto per coprire il notional cresce, ma il margin ratio di partenza resta molto più alto (più sicuro) a parità di notional.
2. **Collaterale ≥ 3× il notional del trade come regola pratica di partenza**: per un trade da 20€, tenere **almeno 60€** allocati sulla posizione isolated — non perché servano davvero 60€ per aprire (il minimo richiesto sarà probabilmente più basso), ma per restare comodamente sopra la soglia di warning 300% considerando che lo SL è già stretto (0,35% gross) quindi il rischio di liquidazione da prezzo puro è basso, ma va dato margine per eventuali slippage sul trigger del bracket.
3. **Verifica empirica obbligatoria al primo trade reale**: appena aperta la prima posizione di test, leggere subito `mgnRatio` da `GET /api/v5/account/positions` — se è già vicino a 300% con 60€ di collaterale su un trade da 20€, va aumentato il collaterale minimo di sicurezza per i trade successivi. Non fidatevi del numero teorico sopra finché non lo vedete confermato sul vostro conto reale.

---

## 4. Lista API aggiornata (include le nuove scoperte di questa sessione)

Riprendo la lista della sessione precedente, **aggiungendo 2 endpoint nuovi** emersi dall'approfondimento su leva e margin tier:

| # | Endpoint | Metodo | Uso |
|---|---|---|---|
| 1 | `/api/v5/account/config` | GET | `enableSpotBorrow`, account mode |
| 2 | `/api/v5/trade/order` | POST | stesso endpoint long, `tdMode=isolated`, `side=sell` |
| 3 | `/api/v5/account/max-loan` | GET | disponibilità borrow per simbolo (check pre-sessione) |
| 4 | `/api/v5/account/set-leverage` | POST | **leva impostata per singola valuta (`ccy`), non per coppia** — nuovo dettaglio confermato in questa sessione |
| 4b | `/api/v5/account/leverage-info` | GET | **NUOVO** — leggere la leva attualmente impostata prima di modificarla |
| 5 | `/api/v5/account/positions` | GET | `posCcy` per riconoscere short; **`mgnRatio` per monitorare rischio liquidazione (soglie 300%/100% confermate)** |
| 6 | `/api/v5/public/interest-rate-loan-quota` | GET | tasso reale per asset — pubblico, no auth |
| 7 | `/api/v5/account/quick-margin-borrow-repay-history` | GET | storico borrow/repay per popolare `borrow_amount`/`margin_interest` |
| 8 | `/api/v5/trade/order-algo` | POST/GET | bracket TP/SL, stesso endpoint, direzione invertita |
| 9 | `/api/v5/account/interest-limits` | GET | eventuale quota interest-free (da verificare se applicabile al vostro account mode) |
| 10 | **`position-tiers` (nome esatto endpoint da confermare in doc-v5)** | GET | **NUOVO** — maintenance margin ratio per tier di posizione/simbolo, necessario per calcolare il collaterale minimo reale (§3.3) — nome parametro non confermato con certezza in questa sessione, verificare su docs-v5 durante lo spike |

---

## 5. Valutazione complessiva del meccanismo

### 5.1 — Cosa funziona bene

- **Auto-limitante per costruzione**: non serve indovinare un timeout arbitrario, il sistema si ferma da solo quando l'interesse ha eroso il budget di rischio, con un tempo massimo calcolabile in anticipo (formula §2)
- **Coerente con l'architettura esistente**: riusa `_net_to_gross_pct` (Layer 2), lo stesso concetto di "target netto → prezzo lordo" già applicato per le fee, solo esteso con un termine che varia nel tempo
- **Compatibile col vincolo operativo reale** (PC spento la notte): il buffer rolling risolve esattamente questo, senza richiedere monitoraggio continuo dell'app

### 5.2 — Cosa resta delicato

- **Cancel + replace del bracket ogni ora** introduce una finestra di rischio operativo che non esiste per il long (dove il bracket si piazza una volta e resta). Va gestita con lo stesso pattern già usato per lo stop sessione (attendi conferma cancellazione prima di piazzare il nuovo) — ma è comunque **complessità nuova e non banale** da testare a fondo prima di fidarsene con capitale reale
- **Il tasso di interesse fisso** semplifica il conto ma è un'approssimazione: se il tasso reale sale molto durante la vita del trade (es. da 15% a 80% APR per uno spike di domanda), il vostro calcolo continuerà a usare il tasso vecchio, sottostimando l'interesse reale accumulato — rischio limitato dal fatto che il buffer di 24h dà comunque un margine di sicurezza, ma va documentato come limite noto, non nascosto
- **Il collaterale minimo reale è ancora ignoto** (§3.3) — non scrivere codice che apra short live finché non avete un numero reale confermato

### 5.3 — Raccomandazione: non implementare tutto insieme

Coerente col principio che già seguite in tutto il progetto ("one change at a time"), suggerisco di **non costruire il meccanismo completo (Layer 3-6) come primo passo**. Una sequenza più sicura:

1. **Fase 1 (MVP)**: short con SL/TP mirrorati identici al long, **nessun aggiustamento per interesse**, ma con un **time-stop fisso e conservativo** (es. 48h flat, nessuna formula) come unica rete di sicurezza — serve solo a validare che l'apertura/chiusura short funzioni tecnicamente su OKX (tdMode, posCcy, bracket)
2. **Fase 2**: dopo aver osservato qualche trade reale e il tasso di interesse reale sui vostri asset, introdurre il meccanismo completo Layer 3-6 con i numeri veri, non quelli illustrativi di questo documento

Questo evita di introdurre contemporaneamente: nuovo tipo di ordine (short), nuovo margin mode (isolated), nuovo meccanismo di rischio (interesse dinamico) e nuova logica di refresh bracket — tutto insieme, senza aver mai visto un solo short reale funzionare.

---

## 6. Prossimi passi concreti

1. Spike read-only (nessun trade): chiamare endpoint #1, #3, #6, #10 sul conto reale per avere i primi numeri veri (tasso interesse BTC/OKB, disponibilità borrow, tier di margine)
2. Decidere il simbolo di test in base al risultato (OKB potrebbe non essere borrowable, vedi analisi precedente)
3. Implementare la Fase 1 (MVP, time-stop fisso 48h, nessuna formula dinamica) come primo task isolato e testabile
4. Solo dopo, con dati reali osservati, formalizzare il Layer 3-6 di questo documento con i tassi reali al posto del 15% illustrativo

## 7. Collegamento con la documentazione da aggiornare

Le istruzioni su deprecazione/aggiornamento file (`short-selling-architecture.md`, `short-selling-analysis.md`, `okx-migration-architecture.md` §5.3) restano quelle già definite in `2026-07-21_okx-short-selling-analysis-recap.md` §1 — questo documento le estende ma non le sostituisce. Il nuovo file `docs/architecture/okx-short-selling-architecture.md` da creare deve incorporare **entrambi** i recap (meccanica base + questo design del time-stop) come sezioni distinte, con la Fase 1/Fase 2 di §5.3 come piano di implementazione ufficiale.
