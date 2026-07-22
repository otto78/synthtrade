# SynthTrade — Recap Sessione: Analisi Short Selling su OKX (meccanica API + costi + architettura)

> **Data:** 21 luglio 2026
> **Contesto:** analisi documentale (nessun codice toccato in questa sessione) — verifica della documentazione OKX ufficiale su Spot Margin/short selling, analisi costi (fee + interesse borrow) alla luce del pivot micro-swing, e definizione di una nuova feature di controllo pre-sessione.
> **Stato:** short selling resta a **zero implementazione** — questa sessione produce solo pianificazione, nessun task è stato avviato.

---

## 1. Istruzioni per l'aggiornamento della documentazione

### 1.1 — Da marcare esplicitamente `Superseded` (non cancellare, ma segnalare in testa al file)

| File | Motivo |
|---|---|
| `docs/architecture/short-selling-architecture.md` | Interamente basato sul modello Binance (`WalletOrchestrator`, `MarginBorrowManager`, trasferimenti multi-wallet Spot→Margin). Su OKX questo layer **non esiste**: conto unificato, nessun trasferimento tra wallet separati, borrow/repay gestito a livello di singolo ordine (`tdMode`) o di account mode. |
| `docs/analysis/short-selling-analysis.md` | Stessa origine Binance, riferisce ancora `TASK-1000`/`WalletOrchestrator` come piano attivo. Il §4 "Dettagli tecnici raccolti" (userMinBorrow, Margin Level 1.1, Isolated Margin) è specifico di Binance e non direttamente applicabile a OKX senza riverifica. |

**Azione concreta:** aggiungere in testa a entrambi i file un blocco tipo:

```markdown
> ⚠️ **SUPERSEDED — 21 luglio 2026**
> Questo documento descrive l'architettura Binance (WalletOrchestrator/MarginBorrowManager),
> non applicabile a OKX. Riferimento attuale: `docs/architecture/okx-short-selling-architecture.md`.
> Non avviare task da questo file.
```

Stesso pattern già usato con successo per `docs/plans/collector-abbondanza-piano-okx.md` quando è stato consolidato.

### 1.2 — Da riscrivere

| File | Cosa cambia |
|---|---|
| `docs/architecture/okx-migration-architecture.md` §5.3 | Lo pseudocodice attuale (`place_market_order(tdMode=cross\|isolated, side=sell, auto-borrow se confermato)`) va sostituito con la meccanica reale verificata in questa sessione (vedi §2). In particolare: **l'auto-borrow non è un parametro d'ordine**, è un'impostazione di conto (`enableSpotBorrow` + account mode); manca il riferimento a `posCcy` per riconoscere lo short a posteriori; manca qualunque menzione del costo di interesse. |

### 1.3 — Da creare

**Nuovo file: `docs/architecture/okx-short-selling-architecture.md`** — sostituisce concettualmente i due file superseded del §1.1, e diventa la fonte di verità per l'implementazione OKX. Deve contenere:
- La meccanica API reale (§2 di questo recap)
- Il modello di costo fee+interesse (§3)
- La nuova feature di verifica disponibilità short per simbolo (§4)
- Il concetto di time-stop, esplicitamente marcato come **aperto/da approfondire** (§5)
- Lista task da aprire (§6)

### 1.4 — Da aggiornare (riferimenti/indici)

| File | Modifica |
|---|---|
| `docs/BACKLOG.md` | Sezione "Short Selling" — sostituire i link ai due file superseded con link a `okx-short-selling-architecture.md`; aggiornare nota di stato da "sospeso fino al cutover OKX" a "cutover OKX completato, pianificazione costi in corso, zero codice" |
| `docs/TASKS.md` | Non esiste oggi nessuna EPICA short-selling per OKX. Da aprire una nuova sezione (numerazione da definire, es. `TASK-1220+` per evitare collisioni con le numerazioni già usate) — solo dopo che il tema time-stop (§5) sarà chiuso in sessione dedicata |

---

## 2. Meccanica reale OKX Spot Margin (verificata su documentazione ufficiale)

Punto di partenza rassicurante: **OKX Spot Margin è disponibile specificamente per utenti EEA** (dominio `eea.okx.com`, coerente col vostro setup attuale) — non è un prodotto ristretto per voi.

Meccanica: non un derivato, è un vero trade spot con margine (collaterale → borrow asset base → sell reale sul book pubblico → buy-back + repay alla chiusura).

### 2.1 — Cosa cambia rispetto all'ordine long attuale

```
POST /api/v5/trade/order
{
  "instId": "BTC-EUR",
  "tdMode": "cross",     // oggi usate "cash" (spot puro, niente borrow)
  "side": "sell",
  "ordType": "market",
  "sz": "..."
}
```

Stesso identico endpoint già in uso. Cambia solo `tdMode`. **Non esiste un parametro "auto-borrow" nell'ordine** — il borrow scatta automaticamente al fill se l'account ha `enableSpotBorrow=true` (verificabile via `GET /api/v5/account/config`) e se c'è collaterale/limite sufficiente.

### 2.2 — Come si riconosce uno short a posteriori

`GET /api/v5/account/positions` (`instType=MARGIN`): il campo `posCcy` è discriminante — **`posCcy` = quote currency (EUR) → short**, **`posCcy` = base currency (BTC) → long**. Nessun flag booleano dedicato.

### 2.3 — Bracket TP/SL

Stesso endpoint `order-algo` già in uso per il long, solo con direzione invertita (TP sotto entry, SL sopra entry).

---

## 3. Lista completa delle nuove API OKX coinvolte

| # | Endpoint | Metodo | Uso | Note |
|---|---|---|---|---|
| 1 | `/api/v5/account/config` | GET | Verifica `enableSpotBorrow` e account mode prima di abilitare short a livello di sistema | Da chiamare una volta all'avvio, non per-trade |
| 2 | `/api/v5/trade/order` | POST | **Stesso endpoint già usato per il long** — cambia solo `tdMode` (`cross`/`isolated` invece di `cash`) e `side=sell` per aprire | Nessun nuovo metodo adapter, solo nuovo parametro |
| 3 | `/api/v5/account/max-loan` | GET | **Bloccante** — verifica se il simbolo/asset è borrowable e quale sia il limite disponibile prima di aprire lo short | Parametri: `instId`, `mgnMode`. Vedi §4, uso esteso come check pre-sessione |
| 4 | `/api/v5/account/set-leverage` | POST | Imposta la leva per la valuta/coppia in margin mode | Necessario solo se si vuole leva diversa da 1x/default |
| 5 | `/api/v5/account/positions` | GET | Riconoscere long/short via `posCcy`; monitorare `mgnRatio` (rischio liquidazione) | Già usato in altri contesti dell'adapter, da estendere per MARGIN |
| 6 | `/api/v5/public/interest-rate-loan-quota` | GET | **Pubblico, nessuna autenticazione** — tasso di interesse reale per asset | Usare per il check pre-sessione (§4) e per il calcolo costi (§5) |
| 7 | `/api/v5/account/quick-margin-borrow-repay-history` | GET | Storico borrow/repay — popola i campi già previsti nello schema DB (`borrow_amount`, `margin_interest`) mai valorizzati finora | |
| 8 | `/api/v5/trade/order-algo` | POST/GET | **Stesso endpoint già in uso per TP/SL long** — nessuna modifica, solo direzione invertita | |
| 9 | `/api/v5/account/interest-limits` | GET | Limite di interesse/quota interest-free se applicabile all'account mode in uso | Da verificare se rilevante per "Spot mode enabled borrow" (probabile assenza di quota interest-free in questa modalità, a differenza di Multi-currency margin — da confermare empiricamente) |

**Nota bloccante prima di tutto:** nessuno di questi endpoint è mai stato chiamato empiricamente sul vostro account reale. Prima di scrivere adapter, serve uno spike isolato (stesso principio già seguito per OKX Demo e per Bybit) che chiami almeno i punti 1, 3, 6 in modalità read-only.

---

## 4. Nuova feature architetturale: check disponibilità short al momento della selezione simbolo

**Decisione presa in questa sessione:** la verifica "questo simbolo supporta lo short" non va fatta al momento di aprire il trade, ma **subito quando l'utente seleziona il simbolo e vengono caricate le candele** — stesso punto del flusso dove oggi gira la instrument discovery (TASK-1116.G, già environment-aware demo/live).

### 4.1 — Cosa verificare

Per il simbolo selezionato (es. `BTC-EUR`), estrarre l'asset base (`BTC`) e chiamare:
1. `GET /api/v5/account/max-loan?instId=BTC-EUR&mgnMode=cross` — se il valore ritornato è 0 o l'endpoint erroa, **short non disponibile**
2. `GET /api/v5/public/interest-rate-loan-quota?ccy=BTC` — se l'asset non compare nella risposta, conferma aggiuntiva di non-disponibilità; se compare, il tasso va mostrato all'utente

### 4.2 — Cosa mostrare all'utente

Nel componente di selezione simbolo (`session-controls.component.ts` o `exchange-symbols.service.ts`, stesso punto già toccato in TASK-1116.G), aggiungere un badge/messaggio:

- ✅ **"Short disponibile — tasso attuale: X% APR"** se `max-loan > 0`
- ⚠️ **"Short non disponibile per questo simbolo"** se `max-loan = 0` o endpoint fallisce

Questo permette all'utente di decidere se aprire comunque la sessione (accettando solo long) o cambiare simbolo prima di partire — esattamente come richiesto.

### 4.3 — Implicazione per il simbolo di default attuale

**OKB è il candidato più a rischio di non essere borrowable**: è il token nativo dell'exchange, il mercato di prestito per un asset del genere è probabilmente più sottile di BTC/ETH. Questo check risolverà la domanda in modo definitivo la prima volta che verrà eseguito — non c'è bisogno di indovinare prima.

### 4.4 — Nota per il refactor già pianificato

Questa feature si aggancia naturalmente al lavoro già fatto in **TASK-1116.G** (instrument discovery environment-aware demo/live) — stesso schema di estensione: l'endpoint `/api/scalping/exchange/instruments` può restituire anche un campo `short_available: bool` e `short_borrow_rate_apr: float | null` per strumento, calcolato una volta per ciclo di discovery (non ad ogni selezione).

---

## 5. Time-stop legato allo SL — concetto proposto, **da approfondire in sessione dedicata**

### 5.1 — L'idea come discussa in questa sessione

Invece di un time-stop a durata fissa (es. "chiudi dopo N ore" indipendentemente da tutto), l'idea è: **il trade resta aperto finché il costo cumulato dell'interesse non equivale al valore dello Stop Loss**. A quel punto la posizione viene chiusa comunque — non perché il prezzo ha toccato lo SL, ma perché l'interesse accumulato "ha eroso" un budget di rischio equivalente. In pratica: o il prezzo tocca lo SL, o il tempo (via interesse) produce lo stesso effetto — converge sempre verso un'uscita "SL-equivalente".

TP e SL restano identici a quelli già in uso per il long (nessuna modifica ai valori assoluti), salvo eventuali variazioni decise dal Supervisor come già avviene oggi.

### 5.2 — Perché questo punto NON è ancora chiuso (e va trattato in una sessione dedicata)

Ci sono almeno tre ambiguità che vanno risolte prima di poter formalizzare la logica in un task implementabile:

1. **Contro cosa si misura l'interesse accumulato?** Contro il valore assoluto/percentuale dello SL nominale (fisso, calcolato all'apertura), oppure contro il "budget di rischio residuo" che si aggiorna se il prezzo nel frattempo si è mosso a favore o contro? Es.: se il prezzo è già a metà strada verso il TP (quindi in profitto non realizzato) ma l'interesse sta erodendo quel margine, la soglia di chiusura deve ricalcolarsi sul P&L netto (prezzo + interesse) o restare ancorata solo al valore SL originario?

2. **L'interesse "consuma" lo SL o si somma al movimento di prezzo?** Se il prezzo si muove leggermente contro (ma non abbastanza da toccare lo SL da solo) e contemporaneamente l'interesse accumula, la condizione di chiusura deve scattare sulla somma dei due (movimento prezzo equivalente% + interesse%), non sull'interesse isolato — altrimenti si rischia di chiudere posizioni che in realtà sono ancora ampiamente dentro la banda di rischio accettata.

3. **Come si traduce "equivale allo SL" in una soglia calcolabile in tempo reale?** Serve decidere se il confronto avviene in termini di valore assoluto (EUR) o percentuale sul notional, e se il ricalcolo avviene ad ogni tick di interesse (ogni ora, quando OKX registra l'accrual) o con un polling più frequente stimato tra un accrual e l'altro.

**Decisione presa:** non si tenta di risolvere questi tre punti ora. Si apre una sessione dedicata specificamente a formalizzare la logica del time-stop, con dati reali di interesse (dal check §4) come input, prima di scrivere qualunque pseudocodice definitivo.

### 5.3 — Cosa portare già pronto alla sessione dedicata

- Tassi di interesse reali osservati per almeno BTC ed ETH (via `interest-rate-loan-quota`, punto 6 della tabella API)
- Conferma se OKB è borrowable o meno (punto 4.3)
- Il valore SL attualmente in uso per il long (1,05% netto, da `TASK-OKX-RECAL`) come riferimento per il primo caso di test numerico

---

## 6. Riepilogo cronologico della sessione (per chi riprende)

1. Verificata meccanica OKX Spot Margin su documentazione ufficiale (EEA Spot Margin FAQ + OKX API guide) — confermato `tdMode=cross/isolated`, `posCcy` per riconoscimento short, tre modalità di borrow (Manual/Auto borrow/Auto repay) come impostazione di conto, non parametro d'ordine
2. Verificata formula di interesse: `Interesse = Liability × (APR / 365 / 24)`, accrual orario
3. Analizzato il rapporto tra costo fee (0,70% round-trip, già noto) e costo interesse — l'interesse resta secondario rispetto alla fee nella maggior parte degli scenari normali, ma diventa rilevante nello scenario "stuck in laterale per ore/giorni" reso più probabile dal pivot micro-swing (SL/TP allargati = bande di prezzo più larghe = permanenza più lunga senza trigger)
4. Identificato che **nessun documento attuale** quantifica questo rischio in modo specifico per OKX (il vecchio doc Binance lo liquidava con "alert dopo 2h", insufficiente)
5. Decisa la nuova feature: check disponibilità short + tasso al momento della selezione simbolo, agganciata al flusso instrument discovery già esistente (TASK-1116.G)
6. Proposto (non chiuso) il concetto di time-stop legato al valore dello SL — rimandato a sessione dedicata per le tre ambiguità del §5.2

## 7. Prossimo passo immediato

Aprire la sessione dedicata al time-stop (§5) prima di scrivere `okx-short-selling-architecture.md` in forma definitiva — il documento nuovo può essere abbozzato con le sezioni §2/§3/§4 già stabili, ma la sezione sul time-stop resta esplicitamente "TBD" finché quella sessione non chiude i tre punti aperti.
