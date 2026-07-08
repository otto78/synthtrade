# SynthTrade — Recap Sessione: Fix WebSocket OKX per dati real-time (grafico + trade)

**Data:** 8 luglio 2026
**Contesto:** debug diretto su log applicativi + screenshot UI, sessione live di test su `OkxWSClient` (modulo scalping, provider OKX). Nessun accesso diretto al codice completo del router/frontend in questa sessione — analisi basata solo su `okx_ws_client.py` fornito e log/screenshot reali.

---

## 1. Punto di partenza

Sintomo riportato dall'utente: il grafico live e gli aggiornamenti trade non si muovevano in tempo reale — il sistema sembrava funzionare solo via polling a ~60s, mentre su Binance il comportamento real-time era garantito nativamente. Ipotesi iniziale dell'utente: OKX non permette WS pubblici con dati reali in Europa.

**Chiarito da subito:** vanno tenute separate due limitazioni diverse, già note al progetto:
- **WS privato/business per fill ordini** (TP/SL) — bloccato per gli account OKX EEA (`60032 API key doesn't exist`), limitazione confermata anche da altri progetti open source (nautilus_trader, hummingbot, freqtrade). Non e' bug nostro, e' gia' gestito con workaround REST polling (`OkxOrderEventStream`).
- **WS pubblico per market data** (candele/trade, senza autenticazione) — questo *non* dovrebbe avere restrizioni EU. Il problema qui era quindi presumibilmente un bug di configurazione, non una limitazione OKX.

---

## 2. Diagnosi #1 — DNS non risolvibile

Dal primo batch di log:

```
OKX WS disconnected ([Errno 11001] getaddrinfo failed) on wss://wsaws.okx.com:8443/ws/v5/public. Reconnect in 1.0s...
```

`getaddrinfo failed` = errore di **risoluzione DNS**, non un rifiuto di OKX (niente 403, niente 60032). L'host `wsaws.okx.com` semplicemente non risolve — coerente con quanto già annotato nella memoria di progetto ("wsaws.okx.com domain not resolving in public DNS").

**Causa probabile:** quando si è deciso di passare al "live network" per il market data (STORY.md v1.4.5, TASK-1100.G Chart fix v3 — motivato dalla bassa liquidità del demo network), è stato introdotto un endpoint `wsaws.okx.com` mai verificato empiricamente nello spike originale (TASK-1100.H aveva testato solo `wspap.okx.com` in demo).

**Fix applicato:** rimossa la logica EU-specifica per il WS pubblico (che non ne ha bisogno — quella limitazione riguarda solo REST autenticato `eea.okx.com` e WS privato). Sostituiti gli URL con gli endpoint standard globali:
- Demo: `wss://wspap.okx.com/ws/v5/public` (già verificato funzionante nello spike)
- Live: `wss://ws.okx.com:8443/ws/v5/public`

Verifica post-fix: connessione riuscita, niente più errori DNS a raffica.

---

## 3. Diagnosi #2 — Regressione: market data tornato su demo

Dopo il primo fix, il grafico restava comunque fermo. Dal log:

```
OKX WS connected: wss://wspap.okx.com/ws/v5/public (channel: trades)
OKX WS connected: wss://wspap.okx.com/ws/v5/public (channel: candle1m)
```

Il fix aveva reintrodotto una selezione `if demo: ... else: ...` per l'URL del WS pubblico, che per una sessione in `mode=paper` risolveva sul network **demo** — esattamente la scelta già scartata in precedenza (STORY.md v1.4.5: *"Demo network OKX ha bassa liquidità → usare sempre live network per dati di mercato. Demo mode deve essere solo per trading execution, non per market data"*).

**Fix applicato:** market data (candele/trade) sempre su endpoint **live**, indipendentemente dal flag `demo` della sessione — quel flag deve influenzare solo l'esecuzione ordini, non la sorgente dati di mercato.

Verifica post-fix:
```
OKX WS connected: wss://ws.okx.com:8443/ws/v5/public (channel: trades)
```
Connessione su live confermata, ma **nessun dato di candela arrivava comunque dal WS** — solo il poller REST continuava a produrre candele (`OKX REST candle: ...` ogni ~55s).

---

## 4. Diagnosi #3 — Canale candele spostato su WS business

Il WS pubblico si connetteva con successo e la sottoscrizione non generava errori visibili, ma il canale `candle1m` non consegnava mai dati. Ipotesi confermata: OKX ha spostato il canale delle candele (`candleX`) dal WS **public** al WS **business** in una revisione dell'API — cambiamento noto e documentato nel changelog OKX. Il canale `trades` resta invece sul `public`.

**Fix applicato:** separata la sottoscrizione nel metodo `start()` di `OkxWSClient`:
- `candle1m` → sottoscritto su `self._ws_business_url` (`wss://ws.okx.com:8443/ws/v5/business`)
- `trades` → resta su `self._ws_url` (public)

Verifica post-fix (log):
```
OKX WS connected: wss://ws.okx.com:8443/ws/v5/business (channel: candle1m)
OKX WS connected: wss://ws.okx.com:8443/ws/v5/public (channel: trades)
```

Confermato indirettamente che le candele ora arrivano dal WS: nel log compaiono righe `>>> PROCESSING closed candle` (11:07:00 e 11:08:00) **senza** la riga esplicita `OKX REST candle:` subito prima — quella riga la stampa solo il poller REST. Il poller gira ogni ~55s (partito alle 11:06:55), quindi quelle due candele non possono provenire da lì: sono arrivate dal canale WS business in tempo reale.

**Conclusione:** il backend ora riceve dati di mercato OKX realmente in tempo reale via WebSocket, sia per le candele (business) sia per i trade (public).

---

## 5. Fix minore — Pylance type warning

Segnalato un warning statico (non un errore runtime) su `websockets.connect(current_url, ...)`: `current_url` era tipizzato `str | None` per via di `self._ws_url_backup: Optional[str]`.

**Fix proposto (non ancora confermato applicato):** rimuovere del tutto la logica di fallback su URL di backup (non più necessaria dopo l'eliminazione di `wsaws.okx.com` — non esistono più URL "di riserva" da provare), semplificando `_run_connection()` per usare un singolo parametro `url: str` senza `Optional`. In alternativa, guard difensivo `if current_url is None: current_url = url`.

---

## 6. Diagnosi #4 (RISOLTA) — mismatch formato simbolo nel filtro frontend

Nonostante il backend ricevesse ormai dati OKX realtime via WS (confermato in log — candele "silenziose" senza riga REST corrispondente), **il grafico nel frontend Angular restava comunque fermo**. Dallo screenshot: il grafico si bloccava su un intervallo temporale precedente mentre in parallelo un trade veniva aperto/chiuso correttamente (BUY @ 54344.20 alle 11:08, poi stop_loss), a riprova che tutto il resto della pipeline (execution loop, position manager, supervisor, DB, backend→frontend broadcast) funzionava.

**Causa radice trovata** in `live-chart.component.ts`, nel subscriber del canale WS `candle$`:

```typescript
if (candle.symbol.toUpperCase() !== this.currentSymbol.toUpperCase()) return;
```

Il confronto normalizza solo il maiuscolo/minuscolo, non il trattino. Nello stato sessione (`_execution_state["session"]["symbol"]`) il simbolo è salvato in formato "compact" senza trattino (`BTCEUR`, vedi log: `Session started: ... symbol=BTCEUR`), mentre `OkxWSClient` usa l'`instId` nativo OKX con trattino (`BTC-EUR`, vedi log: `OkxWSClient started for 1 symbols: ['BTC-EUR']`) e lo stesso formato arriva nel campo `event.symbol` di ogni candela broadcastata dal backend.

Risultato: `"BTC-EUR" !== "BTCEUR"` è sempre vero → **ogni singolo evento candela in arrivo dal WS veniva scartato silenziosamente** dal componente grafico. Il caricamento iniziale via HTTP (`GET /candles/{symbol}`) funzionava perché quell'endpoint non applica questo filtro — da qui l'illusione che "il grafico si carica una volta e poi si blocca".

**Fix applicato:** introdotta una normalizzazione simmetrica prima del confronto, che rimuove sia il caso sia i separatori (`-`, `/`):

```typescript
private _normalizeSymbol(s: string): string {
  return s.toUpperCase().replace(/[-/]/g, '');
}
```

e nel subscriber:
```typescript
if (this._normalizeSymbol(candle.symbol) !== this._normalizeSymbol(this.currentSymbol)) return;
```

**Verificato:** dopo il fix il grafico si aggiorna in tempo reale — confermato dall'utente. L'intera catena WS OKX → backend → broadcast → frontend è ora funzionante end-to-end.

**Nota per il resto del codebase:** questo stesso tipo di mismatch (`BTCEUR` vs `BTC-EUR`) potrebbe presentarsi in altri punti del frontend che confrontano simboli provenienti da fonti diverse (stato sessione vs eventi WS provider-specific). Vale la pena un audit mirato sui confronti di stringa simbolo in tutti i componenti Angular che consumano il WS scalping (es. `trade-log`, `position-ticker`, `market-intel-panel`), applicando la stessa normalizzazione se necessario.

---

## 7. Bug non correlato individuato di passaggio

Nel log compare un errore non-blocking ma reale:

```
new row for relation "session_signal_log" violates check constraint "session_signal_log_decision_type_check"
```

Causato da `decision_type='rejected_short_unsupported'`, valore non incluso nel `CHECK` constraint della tabella (che ammette solo `execute`, `block_conflict`, `mean_reversion_override`, `hold_existing_position`, `rejected_other` — da `docs/recap/2026-06-29_logging-decisionale.md`). Coerente con il gap noto sullo short selling (nessuna implementazione ancora), ma comporta la perdita silenziosa di questi log specifici. Da aggiungere come nuovo valore ammesso al constraint, o da mappare su `rejected_other` finché lo short non è implementato.

---

## 8. Riepilogo modifiche applicate

**Backend — `okx_ws_client.py`:**

| # | Modifica | Motivo |
|---|----------|--------|
| 1 | Rimosso `wsaws.okx.com` (DNS non risolvibile) | Reconnect loop infinito, mai connesso |
| 2 | Market data sempre su endpoint live, non condizionato da `demo` | Demo network ha liquidità troppo bassa, candele piatte |
| 3 | Canale `candle1m` spostato su WS business, `trades` resta su WS public | OKX ha spostato candleX su business in una revisione API |
| 4 (proposto) | Rimossa logica URL di backup / `Optional[str]` | Non più necessaria, elimina warning di tipo |

**Frontend — `live-chart.component.ts`:**

| # | Modifica | Motivo |
|---|----------|--------|
| 5 | Aggiunta normalizzazione simbolo (`_normalizeSymbol`) prima del confronto nel subscriber `candle$` | Mismatch `BTCEUR` (stato sessione) vs `BTC-EUR` (instId OKX nei payload WS) scartava silenziosamente ogni update real-time |

---

## 9. Stato finale

✅ **Risolto end-to-end.** Confermato dall'utente che il grafico si aggiorna correttamente in tempo reale dopo il fix #5. L'intera catena è ora funzionante: OKX WS pubblico (business per candele, public per trade) → `OkxWSClient` → broadcast interno → WebSocket scalping frontend → `LiveChartComponent`.

## 10. Aperti / prossimi passi

- [ ] Applicare fix minore Pylance (rimozione backup URL logic in `_run_connection`, non bloccante)
- [ ] Aggiungere `rejected_short_unsupported` (o valore equivalente) al CHECK constraint di `session_signal_log`, oppure mappare esplicitamente su `rejected_other` nel writer — bug osservato di passaggio, non bloccante ma comporta perdita silenziosa di log
- [ ] Audit degli altri componenti Angular che consumano il WS scalping (`trade-log`, `position-ticker`, `market-intel-panel`, `supervisor-log`) per lo stesso tipo di mismatch simbolo compact vs OKX instId, applicando `_normalizeSymbol` dove serve
- [ ] Valutare se centralizzare la normalizzazione simbolo in un helper condiviso (es. `SymbolUtils.normalize()`) invece di reimplementarla in ogni componente, per evitare che il bug si ripresenti altrove

---

*Recap generato da sessione di debug diretta su log/screenshot reali — 8 luglio 2026.*
