# SynthTrade — Recap Sessione: Bug critico mode="TEST" + fragilità ccxt su OKX (50119 falsi positivi)

**Data:** 9 luglio 2026
**Sessione analizzata:** `sess_bf1ff9d4` — OKB-EUR, mode=test (OKX Demo Trading)
**Sessione precedente di confronto:** `sess_370477c9` — OKB-EUR, mode=paper (riuscita)
**Tipo documento:** analisi diretta su log applicativi reali, bug nuovo non ancora documentato altrove

---

## 1. Sintesi Esecutiva

Sessione avviata in modalità `test` (OKX Demo Trading) e terminata dopo **~13 secondi**, senza mai completare correttamente l'inizializzazione. Due problemi distinti, di gravità diversa:

1. **🔴 Bloccante:** `mode="TEST"` viola il CHECK constraint `scalping_sessions_mode_check` sulla tabella `scalping_sessions` → l'INSERT fallisce → il Session Load Guard non completa mai il `db_phase` → sessione abortita.
2. **🟡 Da correggere ma non bloccante in questo caso:** `get_trade_fee()` fallisce con errore `50119 API key doesn't exist` — errore fuorviante, la chiave **esiste ed è valida** (lo dimostra il fatto che il balance viene letto correttamente pochi istanti dopo). È un problema di **routing interno di ccxt**, non di autenticazione reale. Vedi §4 per la spiegazione completa.

**Impatto pratico in questo caso:** nullo lato capitale — nessun ordine è stato eseguito, il guard ha bloccato correttamente il tentativo di trade. Ma il bug #1 rende **completamente inutilizzabile la modalità `test`/OKX Demo Trading** finché non viene corretto lo schema DB.

---

## 2. Cronologia dettagliata

| Orario | Evento |
|---|---|
| 11:19:07 | `ExchangeAdapter: OKX \| demo=True \| base_url=https://eea.okx.com` |
| 11:19:08 | `CCXT fetch_balance failed (50119 API key doesn't exist)` → fallback a REST diretto **riuscito** |
| 11:19:09 | Balance letto correttamente: 9137.94 EUR [OKX DEMO] — **prova che la chiave è valida** |
| 11:19:09 | `get_trade_fee` fallisce con lo stesso `50119` — **nessun fallback REST per questa chiamata** → fee tier non certificato, fallback hardcoded maker=0.001/taker=0.001 |
| 11:19:09 | Sessione avviata: `mode=test` |
| 11:19:17 | Warmup completato, primo segnale generato: `FORCED FIRST PIPELINE ... BUY@0.35` (decisione approvata, non ancora eseguita) |
| 11:19:17 | WS OkxWSClient avviato |
| 11:19:17,348 | **`Failed to insert session in DB`** — `scalping_sessions_mode_check` violato, valore rigettato: `mode='TEST'` |
| 11:19:18,702 | Primo tentativo di trade reale (`candle_processor`) — **bloccato dal Session Load Guard** (`db_insert_failed`, elapsed 11.1s) |
| 11:19:19 | WS candele (business) e trade (public) confermano connessione — nessun impatto da questo bug |
| 11:19:22 | Supervisor scheduler stoppato, sessione fermata, ExecutionLoop stoppato — shutdown completo a ~13s dall'avvio |

---

## 3. Problema #1 (🔴 Bloccante) — `mode="TEST"` viola `scalping_sessions_mode_check`

**Evidenza dal log:**
new row for relation "scalping_sessions" violates check constraint "scalping_sessions_mode_check"
Failing row contains (..., TEST, OKB-EUR, 1m, running, ...)

**Causa probabile:** lo schema originale di `scalping_sessions.mode` (vedi `docs/plans/scalping-module-plan.md` §9, `docs/architecture/oco-flow-architecture.md` §6) definisce:
```sql
mode TEXT CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST'))
```

Con l'introduzione della modalità globale `TRADING_MODE=test` per OKX Demo Trading (vedi `docs/analysis/okx-live-runbook.md`), il router scalping ora può produrre un valore di sessione `"test"`/`"TEST"` mai aggiunto al CHECK constraint. La sessione precedente della stessa giornata (`sess_370477c9`, `mode=paper`) si era salvata correttamente — confermando che il problema è specifico al valore `test`.

**Nota:** nella riga fallita compare anche una colonna distinta `exchange_account_mode='test'` (minuscolo, da TASK-1108) che invece **non** è vincolata dallo stesso constraint. Il problema è isolato alla colonna legacy `mode`.

**Impatto:** qualunque sessione avviata con `mode=test` fallisce l'INSERT iniziale e va in stato critico entro pochi secondi. La modalità Demo Trading OKX (distinta da `paper`) risulta **non operativa**.

**Fix suggerito:**
```sql
ALTER TABLE scalping_sessions DROP CONSTRAINT scalping_sessions_mode_check;
ALTER TABLE scalping_sessions ADD CONSTRAINT scalping_sessions_mode_check
  CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST', 'TEST'));
```
In alternativa, se concettualmente `test` deve restare distinto solo a livello di `exchange_account_mode`/`exchange_demo` (già presenti), normalizzare il valore scritto in `mode` lato router (es. mappare `test` → `PAPER` per questa colonna legacy) — da decidere in base all'intenzione architetturale originale.

---

## 4. Problema #2 (🟡 Da correggere) — `get_trade_fee()` fallisce con 50119, nessun fallback

**Evidenza:**
OKX get_trade_fee failed for OKB/EUR: okx {"msg":"API key doesn't exist","code":"50119"} — using fallback
Fee tier [okx]: maker=0.001, taker=0.001 certified=False

A differenza di `fetch_balance()` — che ha un fallback REST diretto (confermato in `HANDOFF.md`: *"confermata presenza del CCXT→REST fallback: `_direct_fetch_balance` → `/api/v5/account/balance`"*) — `get_trade_fee()` non ha lo stesso meccanismo. Il risultato è un fee tier hardcoded (0.001/0.001) invece del fee tier reale OKX Demo, che secondo lo spike (`okx-demo-spike-results.md`) è un **rebate negativo** (maker=-0.2%, taker=-0.35%).

**Impatto:** se una sessione `test` fosse arrivata a eseguire trade con questo fee tier non certificato, i calcoli di `_net_to_gross_pct` per TP/SL avrebbero usato valori sbagliati (positivi invece che rebate negativi). In questa sessione non ha avuto conseguenze pratiche perché nessun trade è arrivato all'esecuzione.

**Fix suggerito:** applicare a `get_trade_fee()` lo stesso pattern di fallback REST diretto già usato per `fetch_balance()`.

**Vedi §5 per la spiegazione del perché questo errore è fuorviante.**

---

## 5. Perché l'errore "50119 API key doesn't exist" è fuorviante — la chiave esiste

Il messaggio `50119 API key doesn't exist` sembra indicare un problema di autenticazione, ma **la chiave è valida e funzionante**. Prova diretta dal log stesso: pochi istanti dopo l'errore su `fetch_balance` (via ccxt), la chiamata di fallback via REST diretto **riesce e restituisce il balance corretto** (9137.94 EUR). Se la chiave non esistesse davvero, anche la chiamata REST diretta con la stessa chiave avrebbe fallito.

**Causa reale:** è un problema di **routing interno di ccxt**, non di credenziali. Questo pattern è già documentato più volte nel progetto come fonte ricorrente di problemi:

- `docs/analysis/okx-api-reference-analysis.md` §11 segnalava esplicitamente come punto da verificare empiricamente: *"Se `set_sandbox_mode(True)` di ccxt basta da solo o serve l'header manuale aggiuntivo"* — cioè si sapeva già che ccxt su OKX EU/demo aveva comportamento non garantito.
- `HANDOFF.md` (sessione 3/7) documenta un fix analogo: *"NoneType crash in `_load_from_okx`"* — l'override manuale degli URL ccxt (`exchange.urls["api"][...]`) produceva valori `None` per alcuni endpoint, causando crash.
- Lo stesso `HANDOFF.md` documenta la soluzione adottata altrove nel progetto: *"Rewrite `_load_from_okx` con httpx diretto — zero ccxt fragility"* — cioè per `historical_loader.py` è stato **abbandonato ccxt del tutto** in favore di chiamate REST dirette con `httpx`, proprio per evitare questa fragilità.

**Cosa succede in pratica:** l'adapter imposta correttamente `base_url=https://eea.okx.com` per l'account EU, ma ccxt — internamente — mantiene una propria mappa di URL per singolo endpoint/metodo (`urls["api"]["public"]`, `urls["api"]["private"]`, e sotto-percorsi specifici per `fetchBalance`, `fetchTradingFee`, ecc.). L'override del solo "base URL" non garantisce che **ogni** metodo ccxt rispetti quel dominio: alcuni continuano a puntare implicitamente al dominio globale `www.okx.com`, che per un account EU risponde `50119` perché quella chiave API è registrata solo su `eea.okx.com`.

In sintesi: **non è un errore di autenticazione, è un errore di endpoint sbagliato mascherato da un messaggio che sembra di autenticazione.** La chiave esiste, è valida, ma ccxt la sta usando contro l'host sbagliato per quella specifica chiamata.

**Perché `fetch_balance` se la cava e `get_trade_fee` no:** perché nel codice esiste già un fallback REST diretto per il primo (probabilmente aggiunto dopo aver scoperto lo stesso problema, come documentato in `HANDOFF.md` per il balance fetch del 7/9), ma non è stato ancora replicato per `get_trade_fee`. È lo stesso identico bug di fondo, corretto in un punto e non nell'altro.

**Fix strutturale consigliato (oltre al fallback puntuale):** applicare sistematicamente a `OkxExchangeAdapter` lo stesso pattern già usato in `historical_loader.py` — bypassare ccxt per le chiamate REST verso endpoint noti per essere sensibili al routing EU (`fetch_balance`, `get_trade_fee`, e potenzialmente altri) usando `httpx` diretto contro `eea.okx.com`, invece di continuare a "toppare" ccxt endpoint per endpoint ogni volta che se ne scopre uno rotto.

---

## 6. Comportamenti corretti osservati

### Session Load Guard ha prevenuto il trade
Nonostante `FORCED FIRST PIPELINE` avesse approvato un BUY (11:19:17,079), il tentativo di esecuzione reale al candle close (11:19:18,702) è stato **correttamente bloccato**:
[SESSION_LOCK] Trade attempt BLOCKED (candle_processor): elapsed_sec=11.109
Comportamento esattamente da manuale (`docs/architecture/oco-flow-architecture.md` §5) — nessun ordine orfano o non tracciato è stato piazzato nonostante il fallimento DB.

### WS candele/trade non impattati
Entrambi i canali WS pubblici si sono connessi regolarmente (business per `candle1m`, public per `trades`), confermando che la fix del poller REST e la separazione dei canali continuano a funzionare indipendentemente da questo problema di sessione.

### Rumore non bloccante
`openai/gpt-oss-120b:free` risponde 429 due volte — modello non usato dal supervisor (su Claude Haiku 4.5 come tier 1), nessun impatto.

---

## 7. Domanda aperta

Il log `Session stopped — open positions closed at market` alle 11:19:22 compare **senza prefisso `[sess_bf1ff9d4]`**, a differenza di tutte le righe precedenti della stessa sessione. Non è chiaro dai soli log se si tratti di:
- uno stop manuale intercorso nella finestra osservata, oppure
- una chiusura automatica innescata dal fallimento critico del guard.

Da verificare nel codice (`session_load_guard.py` / `router.py`) se esiste una logica di auto-shutdown su `db_insert_failed`, o se lo stop era un'azione utente.

---

## 8. Collegamento con task proposti

| Task | Cosa | Priorità |
|---|---|---|
| **TASK-NEW-1** | Aggiornare `scalping_sessions_mode_check` per accettare `mode='TEST'` (o normalizzare il valore scritto dal router verso un valore già ammesso) | 🔴 Alta — blocca completamente la modalità Demo Trading OKX |
| **TASK-NEW-2** | Aggiungere fallback REST diretto a `get_trade_fee()` in `okx_exchange.py`, analogo a quello già esistente per `fetch_balance()` | 🟡 Media |
| **TASK-NEW-3** | Audit sistematico di `OkxExchangeAdapter`: identificare tutti i metodi ccxt sensibili al routing EU (non solo balance/fee) e valutare migrazione a `httpx` diretto, seguendo il precedente di `historical_loader.py` | 🟡 Media — previene la stessa classe di bug in altri metodi non ancora scoperti |
| **TASK-NEW-4** | Verificare se `Session stopped` senza prefisso sessione è auto-shutdown o stop manuale in caso di `db_insert_failed` critico | 🟢 Bassa — chiarimento |

---

## 9. Modifiche implementate (2026-07-09)

**TASK-1116.D — DB migration:** Creato `20260709000000_task1116d_add_test_mode_check.sql` per aggiungere `TEST` al CHECK constraint.

**TASK-1116.E — Fallback REST fee:** Aggiunto `_direct_fetch_trade_fee()` in `okx_exchange.py` con fallback automatico quando ccxt fallisce con 50119.

**Router demo mode:** Modificato `control.get("mode") == "live"` → `in ("live", "test")` per costruire adapter anche in demo mode.

**Frontend:** Aggiornato `session-controls.component.ts` per mappare `globalMode='test'` → `mode='test'` (prima era mappato a 'paper').

**Commit:** `d5ef9c3` — push effettuato su origin/main.

---

*Recap generato da analisi diretta di log applicativi reali — 9 luglio 2026.*

Spiegazione rapida (fuori dal documento): perché "API key doesn't exist" se la chiave esiste
In breve: il messaggio è tecnicamente vero solo se letto come "questa chiave non esiste su questo host", ma il messaggio OKX non lo dice esplicitamente, e sembra un errore di autenticazione generico.
Le chiavi API OKX per account EU sono registrate e riconosciute solo dall'host eea.okx.com. Se una richiesta — anche con la chiave corretta — arriva all'host globale www.okx.com (o a un endpoint interno di ccxt che punta lì per sbaglio), OKX risponde 50119 perché su quell'host, per quella chiave, letteralmente non c'è nessuna registrazione.
Il tuo adapter imposta il base_url giusto (eea.okx.com), ma ccxt non garantisce che ogni singolo metodo rispetti quell'override — ha una mappa interna di URL per endpoint che a volte "vince" sulla configurazione globale. È un problema già noto e già aggirato altrove nel codice (il caricamento storico candele è stato riscritto per bypassare ccxt del tutto), ma non ancora applicato a get_trade_fee().