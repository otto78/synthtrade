# 2026-09-29 — SL/TP per-strategia in LIVE, deploy VPS, bonifica suite test

**Data:** 2026-09-29
**Sessione:** continuazione TASK-1256/1257 (SL/TP per-strategia) + bonifica suite di test
**Esito:** TASK-1256/1257 deployati e verificati in LIVE. Suite a **792 passed / 0 failed**.

---

## 1. Cosa si è trattato — capisaldi

### 1.1 TASK-1256/1257 — SL/TP e trailing per-strategia (completato e in LIVE)

Obiettivo: `rsi_bollinger` non doveva più condividere i valori globali di rischio.

| Strategia | SL (netto) | TP (netto) | Cap trailing |
|---|---|---|---|
| `rsi_bollinger` | **0.30** | **0.55** | 0.55 |
| `ema_cross` | 0.50 (globale) | 0.80 (globale) | 0.80 |
| `vwap_reversion` | 0.50 (globale) | 0.80 (globale) | 0.80 |

I valori per-strategia sono override in DB (`scalping_runtime_config`, chiavi
`STRATEGY_<NOME>_SL_PCT` / `_TP_PCT`) con **fallback automatico ai globali** in `_state.py`.
Nessuna strategia può restare senza copertura: se manca l'override si usa il globale.

File toccati: `config_loader.py`, `candle_processor.py`, `break_even.py`.

### 1.2 Due chiarimenti importanti sul meccanismo di rischio

**Il break-even è corretto e fee-aware.** Trigger a +0.15% netto, stop di sicurezza a +0.05% netto,
entrambi calcolati con le fee reali taker (0.10%/lato) via `_exit_price_ratio`. Non va modificato:
l'obiettivo dichiarato è "non perdere", non "guadagnare". Su un trade da 20 € uno stop a +0,05% vale
1 cent: corretto che ci sia.

**Gli step del trailing NON sono proporzionali al TP.** I valori sono **fissi** in `break_even.py`
(`step 0.15`, `buffer 0.10`, `safety 0.10`), identici per tutte le strategie, overridabili solo via DB.
A essere dinamico è solo **quanti step** stanno sotto il tetto `TP - safety`:
- `rsi_bollinger` TP 0.55 → tetto 0.45 → **1 step (0.30)**
- `ema_cross` TP 0.80 → tetto 0.70 → **3 step (0.30 / 0.45 / 0.60)**

Conseguenza: con TP 0.55 la scala fissa verrebbe troncata a un solo livello, quindi l'aumento
del TP da 0.45 a 0.55 oggi **non** produce più step. Questa è la lacuna di **TASK-1258**, che resta
aperta: serve rendere gli step proporzionali o riscalati in funzione del TP.

**Nota sul dimensionamento:** SL 0.30% netto ≈ **−0.10% di movimento prezzo**, perché le fee
(0.20% round-trip) consumano quasi due terzi dello stop. Su un trade da 20 € lo stop scatta a ~2 cent
di perdita. Va bene, ma è un numero da tenere presente quando si calibra.

### 1.3 Fix UI — le percentuali mostrate erano sbagliate

La scheda posizione, il ripristino sessione e l'update realtime mostravano le percentuali **globali
(0.50 / 0.80)** anche quando erano stati piazzati ordini con valori diversi. Ora derivano dai **prezzi
OCO realmente piazzati** (`pos.sl_price` / `pos.tp_price`) tramite `_expected_net_pct_at_exit`.

File: `rest/position.py`, `router.py` (2 punti), `trade_processor.py` (2 punti).

### 1.4 Scoperta in LIVE: il bot stava tradando `ema_cross`, non `rsi_bollinger`

```
TASK-1250 MACRO OVERRIDE: BTC 84603 > EMA20 4h 84341 → override rsi_bollinger → ema_cross
```

Non è un bug: è il filtro macro TASK-1250 che ha funzionato. Ma la conseguenza pratica è che i
valori dedicati della bollinger **non erano attivi** in quel momento, perché la strategia selezionata
era un'altra (che usa i globali 0.50/0.80). Da ricordare quando si legge un trade: **controllare
sempre la strategia in esecuzione prima di valutare se SL/TP per-strategia ha funzionato.**

### 1.5 Deploy VPS — procedura e due errori da non ripetere

Il deploy è stato fatto con: backup → verifica hash → copia file → **normalizzazione CRLF→LF** →
rebuild → verifica funzionale in container.

**Errore 1 — `sed` remoto non applicabile.** I file locali sono 100% CRLF. Copiati così, sul VPS il
diff mostrava il file intero come riscritto (mille righe di diff invece di 6). Risolto con uno script
bash dedicato che fa `tr -d '\r'`. Il `sed` inline remoto non ha funzionato (quoting di PowerShell
attraverso SSH).

**Errore 2 — `scp` nella directory sbagliata.** `position.py` sta in `scalping/rest/`, non in
`scalping/`. Copiandolo nella directory sbagliata il file è finito come file spazzatura in
`scalping/position.py` **mentre** `rest/position.py` restava la versione vecchia. Rilevato dal fatto
che `git diff --stat` non elencava il file. Corretto: file spazzatura rimosso, `rest/position.py`
aggiornato e verificato con `git hash-object`.

**Regola appresa:** dopo ogni `scp`, verificare sempre `git diff --stat` sul VPS. Se un file che hai
appena copiato non compare nel diff, è finito nel posto sbagliato.

**Procedura verificata (hash):** `git hash-object` locale e sul VPS devono coincidere, altrimenti il
file è stato clobberato o è finito altrove.

### 1.6 Audit e bonifica della suite di test

Audit completo: **110 test fallenti**, di cui **85 obsoleti**, **11 scritti male**, **0 bug reali**,
**0 problemi d'infrastruttura**. L'88,5% era rumore.

I fallimenti venivano quasi tutti da tre decisioni architetturali che i test non avevano seguito:
1. rimozione dello short selling (commit `cd4ec96`, 1943 righe eliminate) → metodi come
   `get_margin_positions`, `close_short_position`, `short_timestop_job` non esistono più;
2. passaggio a **long-only** → `should_execute()` blocca tutti gli SELL;
3. soglie cambiate → TASK-1255 ha portato strong-bearish da −15 a **−8.0**, TASK-1159 ha cambiato i pesi.

**Correzione a un'affermazione precedente:** il commit `cd71aae` NON è quello che ha rimosso gli
ordini OCO — è "fix: add session load guard and document OCO flow". La rimozione di
`place_stop_loss_order` / `place_limit_order` è avvenuta in un altro punto della storia.

**Due rischi concreti trovati e gestiti:**

- **Test che facevano rete vera.** `test_fear_greed.py` patchava `httpx.AsyncClient.get`, ma il
  collector usa **`aiohttp`** con context manager asincrono: il patch non intercettava nulla e i test
  colpivano davvero il servizio esterno (valore reale `71`). Ora la fixture autouse sostituisce
  `aiohttp.ClientSession` con `side_effect=AssertionError("network access is not allowed")`: se un
  test tocca la rete, **fallisce**. È anche il motivo per cui quel file era lento e instabile.
- **Copertura del percorso ordine reale in pausa.** I 12 test che coprono entry → bracket → fill →
  close con `FakeOkxAdapter` stavano in `tests/integration/`, che `pytest.ini` esclude. Ma il
  `FakeOkxAdapter` è importato anche dalla suite attiva, quindi la struttura era incoerente:
  l'infrastruttura in una dir "in pausa" che serve la suite attiva, e i test che la esercitano non
  giravano. **Spostati in `tests/scalping/`**: la copertura del codice che piazza SL/TP reali ora gira
  di default. Suite 780 → **792**.

**Stato finale verificato:** `792 passed, 0 failed` in ~2:35, lanciando da `synthtrade/backend/`.

### 1.7 Il gotcha che ha falsato una diagnosi

Lanciando pytest **dalla root del progetto** ho misurato 110 fallimenti e li ho scambiati per regressioni.
Lanciando dalla directory giusta: 0 fallimenti.

Il motivo: `synthtrade/backend/pytest.ini` contiene `asyncio_mode = auto`. Ese file **non viene
applicato** se si lancia dalla root, e senza quella impostazione tutti i test asincroni si degradano.
Risultato: numeri completamente diversi a seconda della directory di lancio.

**Regola: lanciare sempre `python -m pytest` da `synthtrade/backend/`, mai dalla root.**

Nota: `AGENTS.md` documentava il comando `pytest synthtrade/backend/tests/` **dalla root**, che è
proprio la forma che produce risultati fuorvianti. Corretto in `AGENTS.md`.

### 1.8 Lint — nessuna regressione

`ruff` segnala 53 errori sui 6 file toccati, ma sono **tutti pre-esistenti**: verificato con un
worktree sul commit precedente ai cambiamenti, che dà **esattamente gli stessi 53** con identica
spezione (34 F401, 15 E402, 3 F541, 1 F841). Nessun errore nuovo introdotto. Per la regola di
`AGENTS.md` (non correggere warning pre-esistenti) sono stati lasciati.

Nota: l'F401 su `MarketOrderRequest`/`ExitBracketRequest`/`SymbolRef` in `candle_processor.py` è
legittimo ma pre-esistente: esiste un import a livello di modulo e uno **locale dentro la funzione**,
ed è quello locale ad essere usato.

---

## 2. Stato al momento della consegna

- **`main` allineato con `origin/main`** (0 ahead / 0 behind), working tree pulito.
- Sessione live `09219901-1cd0-4475-a836-0ca3820f6bec` attiva, `live`, BTC-EUR, `fee_tier_certified: true`.
- Deploy VPS completato e verificato: 0 errori nei log, codice presente in container.
- Suite: 792 passed / 0 failed.
- Nessun test che tocchi la rete.
- Copertura del percorso ordine reale (bracket, cancel, fill) nella suite attiva.

## 3. Cosa resta aperto

| Task | Stato | Blocco |
|---|---|---|
| **TASK-1258** trailing per-strategia | aperta | gli step sono **fissi**, non proporzionali al TP. Con TP 0.55 la scala si tronca a 1 step. |
| **TASK-1257** calibrazione valori | aperta | servono ≥30 trade post-deploy 1.7.0 (dal 2026-09-25) |
| **TASK-1252** Fase 2 (peso score) | aperta | serve correlazione score→PnL su dati nuovi |
| **TASK-1253** asimmetria SL/TP | aperta | serve win rate per combinazione regime/strategia |
| Integration/audit/e2e in pausa | in pausa | 22 fallimenti (dashboard, strategies API, Binance legacy). Esclusi via `pytest.ini`. |

## 4. Decisioni da non ribaltare

- **Il break-even non si tocca.** Obiettivo "non perdere", non guadagnare.
- **Gli step trailing restano 1 per la bollinger** finché TASK-1258 non li rende proporzionali.
- **Non correggere i warning ruff pre-esistenti** (regola `AGENTS.md`).
- **Non fare `git pull` sul VPS**: il repo del VPS è divergente da locale. Si copia file singoli.
- **Mai `--reload` su uvicorn in live**: uccide le WebSocket.
