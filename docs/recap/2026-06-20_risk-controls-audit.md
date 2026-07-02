# SynthTrade — Recap Sessione: Audit Risk Controls & Considerazioni Roadmap

**Data:** 20 giugno 2026
**Documento collegato:** `synthtrade-considerazioni-roadmap.md` (analisi architetturale completa dei 3 punti)

---

## Obiettivo della sessione

Richiesta iniziale in 3 punti:
1. Strategia per alimentare il Supervisor AI con i dati del session log di scalping
2. Pianificazione del ragionamento su short selling / margin trading
3. Analisi e audit della card "Risk Controls" (funziona? è usata davvero dal trader?)

---

## 1. Stato dei 3 punti richiesti

| Punto | Stato | Note |
|---|---|---|
| 1. Session log → Supervisor AI | 🟡 **In sospeso** — solo pianificazione | Nessun codice toccato. Schema dati e pipeline proposti, ma bloccati dal sync bug `strategy_selected`/`strategy_executed` da fixare prima |
| 2. Short selling / margin | 🟡 **In sospeso** — solo pianificazione | Riepilogate le 4 fasi già note + aggiunte considerazioni su margin level, interesse, `WalletOrchestrator`. Nessuna implementazione iniziata |
| 3. Audit Risk Controls | 🟢 **Risolto** — con fix applicati | Diventato il fulcro della sessione, vedi dettaglio sotto |

---

## 2. Audit Risk Controls — cronologia dettagliata

**Punto di partenza:** un'analisi fatta con un altro modello (deepseek) si contraddiceva da sola — prima diceva che la route `POST /risk/config` non esiste, poi diceva che esiste e funziona.

**Verifica fatta leggendo il codice reale** (`router.py`, `risk-controls.component.ts`, `scalping-dashboard.component.ts`, migration SQL):

- ✅ `GET`/`POST /scalping/risk/config` esistono entrambe nel backend
- ✅ **Stop Loss e Take Profit sono realmente applicati**: calcolano i prezzi dell'ordine OCO reale piazzato su Binance
- ✅ **Max Daily Loss è realmente applicato**: `_check_daily_loss()` blocca nuovi trade se la soglia è superata
- ❌ **Leverage non viene mai usato** da nessuna logica di trading — solo salvato/mostrato (coerente col fatto che il margin non è ancora implementato)
- ❌ **Max Drawdown non blocca nulla** — esiste un valore omonimo calcolato altrove ma è solo una metrica storica scollegata dalla soglia configurata

**Dubbio sollevato e poi risolto:** la migration SQL allegata (`20260527...`) aggiungeva solo una colonna a `scalping_sessions`, non creava la tabella `scalping_risk_config` usata dal codice. Risolto con screenshot diretti da Supabase: la tabella esiste davvero con lo schema corretto — la migration che la crea (`20260603...`) semplicemente non era stata allegata in chat.

**Test end-to-end deciso e fatto da Andrea:** cambiato `max_daily_loss` da 10 a 2 tramite Save Config nell'app reale, confermato il cambiamento via query diretta su Supabase → **persistenza confermata funzionante al 100%**.

**Difetto minore individuato:** `updated_at` non si aggiornava mai, perché non era incluso nel payload della `POST` (nessun trigger DB a compensare).

---

## 3. Fix applicati in questa sessione

| # | Fix | File | Tipo |
|---|---|---|---|
| 1 | Aggiunto `"updated_at": datetime.now(timezone.utc).isoformat()` al payload di upsert | `router.py` → `update_risk_config` | Backend, 1 riga |
| 2 | Campi `Leverage` e `Max Drawdown` disabilitati (input greyed-out) con badge "non attivo" e tooltip esplicativo | `risk-controls.component.ts` | Frontend, no logica |

Entrambi i fix: **zero modifiche alla logica di trading**, basso rischio, coerenti con il principio "one change at a time". File modificato consegnato pronto per essere sostituito nel progetto.

---

## 4. Punti ancora in sospeso / prossimi passi

- **Cooldown dopo perdite consecutive** — non esiste ancora come campo di `RiskConfig`; proposta: aggiungere `cooldown_minutes` + funzione `_check_cooldown()` sullo stesso modello di `_check_daily_loss()`
- **Decisione su `max_drawdown` a lungo termine** — diventa un vero blocco (stile `_check_daily_loss`, su base sessione) o resta disabilitato definitivamente
- **Fix sync bug `strategy_selected` vs `strategy_executed`** — prerequisito bloccante per il punto 1 (alimentare il Supervisor con dati di sessione attendibili)
- **Schema esteso `session_trade_log`** — con `regime_confidence` numerico e `signal_breakdown` jsonb (proposto, non implementato)
- **Job di riflessione periodica del Supervisor AI** — digest in tempo reale + job APScheduler periodico con tabella `supervisor_notes` (proposto, non implementato)
- **Fase 1 short selling**: `margin_short.py` isolato, solo testnet — non ancora iniziata

---

## 5. Proposte di miglioramento aggiuntive emerse (non urgenti)

- **Feedback visivo su Save Config**: oggi è "fire and forget" — proposto un toast di conferma (successo) invece del solo `console.error` (errore)
- **Coerenza con il pattern di error toast** già esistente nella dashboard (evento custom `scalping-error`), riutilizzabile anche da `saveConfig()`
- **Vista mismatch nella pagina session log** (Angular): evidenziare le righe dove strategia selezionata ≠ eseguita, utile sia per debug manuale che come data-quality gate prima di alimentare il Supervisor
- **Badge di confidenza regime** sulla riga del log, per individuare a colpo d'occhio i casi limite di misclassificazione

---

## 6. File prodotti in questa sessione

1. `synthtrade-considerazioni-roadmap.md` — analisi architetturale completa dei 3 punti, aggiornata più volte con i findings reali
2. `risk-controls.component.ts` — componente Angular con i fix applicati, pronto da sostituire nel progetto
3. Questo recap
