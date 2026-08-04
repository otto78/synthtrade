# SynthTrade — Piano di Implementazione: Consolidamento a 3 Strategie Runtime

> **Data:** 29 luglio 2026
> **Contesto:** fee reali confermate account (taker 0,10%, round-trip 0,20% — non più 0,70% come nello spike OKX demo di luglio). SL/TP netti attuali (0,50%/0,80%) restano sostenibili, nessuna ricalibrazione urgente richiesta da questo piano.
> **Riferimento:** `docs/analysis/scalping-strategies-analysis.md` (mappa completa strategie, regime, config)
> **Principio guida:** "one change at a time" — ogni fase va verificata con dati reali prima della successiva. Nessuna cancellazione di codice in questo piano: `momentum_base` e `stoch_rsi_bb_squeeze` restano nel registry come dead code innocuo, non vengono toccati.

---

## 0. Obiettivo e razionale (per chi implementa)

Oggi il sistema ha 5 strategie runtime mappate su 5 regimi, ma 2 di esse sono strutturalmente sprecate in un motore long-only:

- `vwap_reversion` è **orfana**: registrata in `registry.py` ma mai assegnata da nessun regime in `StrategySelector`/`config_loader.py`. Non gira mai.
- `ema_cross` su regime `trending_down` genera quasi solo segnali SELL, che vengono sistematicamente bloccati (long-only, short cancellato — vedi `docs/analysis/audit-short-selling-cancelled.md`). Cicli sprecati.
- `momentum_base` (fallback per `unknown`) ha un margine di trigger di 0,01% sopra/sotto EMA9 — dentro il rumore di una candela 1m, non un edge misurabile.

**Decisione presa con l'utente:** consolidare a 3 strategie realmente attive, riassegnando i regimi così:

```
ranging       → rsi_bollinger   (invariato)
trending_up   → ema_cross       (invariato)
trending_down → rsi_bollinger   (era ema_cross)
volatile      → vwap_reversion  (era stoch_rsi_bb_squeeze — regime mai osservato in produzione)
unknown       → vwap_reversion  (era momentum_base — regime visto solo come transiente iniziale)
```

Il meccanismo che rende sicuro `rsi_bollinger` su `trending_down` **esiste già** ed è la Falling Knife Protection (TASK-906, `signal_aggregator.py`): se il trend è in caduta verticale confermata (`trend_direction=="diverging"` + `trend_5m < -20.0`), il mean-reversion override viene bloccato. Nei bearish "normali" (non caduta-coltello), l'override tenta comunque il rimbalzo BUY. Non serve costruire nessuno stato "pausa" separato — è sufficiente il riassegnamento del mapping regime→strategia.

**Nessun deploy di codice backend richiesto per il mapping regime→strategia**: dopo TASK-904, questo mapping è interamente DB-driven via `scalping_runtime_config` (chiavi `REGIME_STRATEGY_*` e `REGIME_ALLOWED_*`), con reload a caldo. La parte di codice reale riguarda solo il **frontend** (dropdown selezione strategia) e il **default di avvio sessione**.

---

## FASE 1 — Config runtime: riassegnare regime → strategia (zero codice, solo config)

**Priorità:** 🔴 Alta — sblocca tutto il resto
**Rischio:** Bassissimo, reversibile in un secondo POST
**Dipendenze:** nessuna

### Task 1.1 — Aggiornare `scalping_runtime_config` via endpoint esistente

Usare l'endpoint già esistente (da TASK-838/B5) `POST /api/scalping/config/{key}` per aggiornare, uno alla volta e verificando il reload dopo ognuno:

```
POST /api/scalping/config/REGIME_STRATEGY_trending_down
  body: value=rsi_bollinger

POST /api/scalping/config/REGIME_STRATEGY_volatile
  body: value=vwap_reversion

POST /api/scalping/config/REGIME_STRATEGY_unknown
  body: value=vwap_reversion

POST /api/scalping/config/REGIME_ALLOWED_trending_down
  body: value=rsi_bollinger

POST /api/scalping/config/REGIME_ALLOWED_volatile
  body: value=vwap_reversion

POST /api/scalping/config/REGIME_ALLOWED_unknown
  body: value=vwap_reversion
```

**Non toccare:** `REGIME_STRATEGY_ranging`, `REGIME_STRATEGY_trending_up`, `REGIME_ALLOWED_ranging`, `REGIME_ALLOWED_trending_up` — restano `rsi_bollinger` ed `ema_cross` come oggi.

### Task 1.2 — Verifica applicazione

- `GET /api/scalping/config` deve mostrare i 6 valori aggiornati
- Log all'avvio del prossimo ciclo di scoring: verificare che `ScalpingConfigLoader` non segnali errori di parsing
- Nessun restart backend necessario (reload a caldo già implementato, TASK-838)

### Acceptance criteria Fase 1

- [ ] I 6 valori sono aggiornati e verificati via `GET /api/scalping/config`
- [ ] Nessun errore nei log del config loader dopo il reload
- [ ] `REGIME_STRATEGY_ranging` e `REGIME_STRATEGY_trending_up` risultano invariati (controllo di non-regressione)

---

## FASE 2 — Backend: default strategia di avvio sessione

**Priorità:** 🔴 Alta
**Rischio:** Basso
**Dipendenze:** nessuna (indipendente da Fase 1, ma va fatta prima della Fase 3 frontend)

### Task 2.1 — Individuare il default hardcoded lato backend

Cercare tutte le occorrenze di `momentum_base` usato come **default** (non come riferimento generico) in:
- `synthtrade/backend/app/scalping/_state.py` — dizionario di default sessione (campo `strategy`)
- `synthtrade/backend/app/scalping/rest/session.py` — eventuale default nel body di `POST /session` se il client non specifica una strategia
- Qualunque altro punto trovato con:
  ```bash
  grep -rn "momentum_base" synthtrade/backend/app/scalping/ | grep -iv "registry\|strategies/momentum_base.py\|test_"
  ```

### Task 2.2 — Sostituire il default con `vwap_reversion`

In ogni punto trovato al Task 2.1 dove `momentum_base` è usato come valore di default (non come opzione tra tante), sostituire con `vwap_reversion`.

**Non toccare:** il file `strategies/momentum_base.py` stesso, né la sua registrazione in `registry.py` — resta disponibile come opzione, solo non più il default automatico.

### Task 2.3 — Verifica

- Avviare una sessione senza specificare esplicitamente `strategy` nel body di `POST /session` (o con il default di frontend, dopo Fase 3)
- Verificare in log/DB (`scalping_sessions.strategy`) che il valore salvato sia `vwap_reversion`, non `momentum_base`

### Acceptance criteria Fase 2

- [ ] Grep conferma zero occorrenze residue di `momentum_base` come default (solo come opzione nel registry)
- [ ] Una sessione avviata senza strategia esplicita salva `vwap_reversion` su DB

---

## FASE 3 — Frontend: dropdown selezione strategia limitato a 3 opzioni

**Priorità:** 🔴 Alta
**Rischio:** Basso — solo UI, nessun impatto su logica di trading
**Dipendenze:** Fase 2 (per coerenza del default mostrato)

### Task 3.1 — Individuare il dropdown e la lista opzioni

File coinvolto (da TASK-821, già toccato in passato per default/nomi):
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts`

Cercare l'array/oggetto che popola le opzioni dello strategy selector (probabilmente un array di label/value tipo quello già modificato in TASK-821: "RSI + Bollinger", "StochRSI BB Squeeze", ecc.)

```bash
grep -n "momentum_base\|stoch_rsi_bb_squeeze\|vwap_reversion\|ema_cross\|rsi_bollinger" synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts
```

### Task 3.2 — Ridurre le opzioni del dropdown a 3

Il dropdown deve mostrare **solo**:
- `rsi_bollinger` → label "RSI + Bollinger" (invariata)
- `ema_cross` → label esistente (invariata)
- `vwap_reversion` → label da definire (es. "VWAP Reversion"), oggi probabilmente assente dal dropdown essendo mai stata wired

Rimuovere dalle opzioni visibili: `momentum_base`, `stoch_rsi_bb_squeeze`.

**Nota per chi implementa:** non cancellare i model/tipi TypeScript che referenziano le 5 strategie se usati altrove (es. `trade-log.component.ts` che mostra lo storico — un vecchio trade con `strategy_type=momentum_base` deve continuare a renderizzare correttamente il nome nello storico). La rimozione riguarda **solo la lista di opzioni selezionabili per nuove sessioni**, non i tipi/enum usati per visualizzare dati storici.

### Task 3.3 — Aggiornare il default del dropdown

Il valore selezionato di default alla apertura del pannello (probabilmente uno `[value]` o binding iniziale nel component, o un default nel `SessionControl` model) deve essere `vwap_reversion` invece di `momentum_base`, coerente con la Fase 2.

Verificare anche `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/strategy-panel.component.ts` — da TASK-821 risulta avere un fallback `STRATEGY_DEFAULTS['momentum_base']` per quando la strategia attiva non è ancora nota. Se questo fallback esiste ancora, aggiornarlo a `STRATEGY_DEFAULTS['vwap_reversion']` per coerenza, **oppure** verificare se ha ancora senso mantenerlo su `momentum_base` come "ultima spiaggia" di visualizzazione (non è un default operativo, solo di rendering) — decisione a discrezione di chi implementa, da annotare nel commit.

### Task 3.4 — Verifica UI

- Aprire i controlli sessione: il dropdown mostra esattamente 3 opzioni (RSI+Bollinger, EMA Cross, VWAP Reversion)
- Il valore preselezionato all'apertura è VWAP Reversion
- Avviare una sessione con VWAP Reversion selezionata esplicitamente e verificare che il backend la accetti e la salvi correttamente

### Acceptance criteria Fase 3

- [ ] Dropdown mostra solo 3 strategie
- [ ] Default preselezionato è VWAP Reversion
- [ ] Trade storici con `strategy_type` nelle vecchie 5 strategie (inclusi `momentum_base`/`stoch_rsi_bb_squeeze`) continuano a visualizzarsi correttamente in Trade Log/Performance Panel (nessuna regressione sui dati storici)
- [ ] Una sessione live/demo avviata con VWAP Reversion funziona end-to-end (nessun crash, nessun errore console)

---

## FASE 4 — Osservazione post-cambio (nessun codice, solo monitoraggio)

**Priorità:** 🔴 Alta — è la parte che dà valore a tutto il resto
**Dipendenze:** Fasi 1-3 completate e in produzione da almeno 2-3 giorni

`vwap_reversion` non ha **mai girato in produzione** prima d'ora (era orfana). Questo consolidamento è anche il suo primo vero collaudo, non solo un redeploy di logica nota.

### Task 4.1 — Query di verifica dopo i primi trade

Dopo le prime sessioni con il nuovo mapping, eseguire una query analoga a quella già usata in TASK-1232/TASK-898 per verificare distribuzione e win rate per `strategy_type`:

```sql
SELECT
    t.strategy_type,
    sl.regime,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(AVG(t.pnl), 4) AS avg_pnl
FROM scalping_trades t
LEFT JOIN session_signal_log sl ON sl.id = t.signal_log_id
WHERE t.entry_time > '<data_del_deploy>'
GROUP BY t.strategy_type, sl.regime
ORDER BY n_trades DESC;
```

### Task 4.2 — Verificare in particolare

- `rsi_bollinger` su `trending_down`: la Falling Knife Protection sta effettivamente bloccando gli override nei crash veri? (cercare log `FALLING_KNIFE` o assenza di trade con `trend_5m` molto negativo)
- `vwap_reversion`: si comporta come atteso (BUY quando prezzo sotto VWAP di soglia, non genera errori)? Nessuna strategia mai usata prima può nascondere bug non coperti dai test esistenti in condizioni di mercato reali
- Cooldown cambio strategia (20 min): con `rsi_bollinger` che ora copre 2 regimi, verificare che il Supervisor non oscilli in modo anomalo tra ranging/trending_down sullo stesso simbolo

### Acceptance criteria Fase 4

- [ ] Almeno 15-20 trade osservati con il nuovo mapping prima di trarre conclusioni
- [ ] Nessun errore applicativo specifico di `vwap_reversion` nei log
- [ ] Query di verifica eseguita e risultati documentati in un nuovo recap (`docs/recap/`)

---

## Riepilogo task per tracking (`docs/TASKS.md`)

| Task | Fase | Tipo | Rischio | Bloccante per |
|------|------|------|---------|----------------|
| 1.1 — Update `scalping_runtime_config` (6 chiavi) | 1 | Config, no-code | Bassissimo | Fase 4 |
| 1.2 — Verifica reload config | 1 | Verifica | — | — |
| 2.1 — Grep default `momentum_base` backend | 2 | Audit | — | 2.2 |
| 2.2 — Sostituire default con `vwap_reversion` | 2 | Backend | Basso | Fase 3 |
| 2.3 — Verifica sessione senza strategy esplicita | 2 | Verifica | — | — |
| 3.1 — Individuare dropdown frontend | 3 | Audit | — | 3.2 |
| 3.2 — Ridurre dropdown a 3 opzioni | 3 | Frontend | Basso | 3.4 |
| 3.3 — Default dropdown = VWAP Reversion | 3 | Frontend | Basso | 3.4 |
| 3.4 — Verifica UI + non-regressione storico | 3 | Verifica | — | Fase 4 |
| 4.1 — Query distribuzione/win-rate post-deploy | 4 | Analisi | — | — |
| 4.2 — Verifica falling knife + vwap + cooldown | 4 | Analisi | — | Recap finale |

---

## Esplicitamente fuori scope per questo piano

- Nessuna modifica al codice delle strategie stesse (`ema_cross.py`, `rsi_bollinger.py`, `vwap_reversion.py`) — solo riassegnazione di mapping e default
- Nessuna rimozione di `momentum_base.py` o `stoch_rsi_bb_squeeze.py` dal registry — restano come opzioni tecnicamente disponibili ma non più default né nel dropdown
- Nessuna ricalibrazione di SL/TP — il fee reale (0,20% round-trip) rende gli attuali target netti (0,50%/0,80%) già sostenibili
- Nessuna decisione sulla cadenza trade/giorno (scalping più stretto vs attuale) — discussione separata, da riprendere solo dopo aver osservato l'effetto di questo consolidamento
- Nessuna modifica ai pesi del `SignalScoreEngine` (TASK-1159 resta bloccato in attesa di campione più ampio)
