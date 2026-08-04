# SynthTrade — Recap: Consolidamento a 3 Strategie Runtime + Correzione Fee Reali

> **Data:** 29 luglio 2026
> **Contesto:** analisi congiunta (documentale + discussione diretta) su stato delle 5 strategie runtime, alla luce di un dato aggiornato: fee reale confermata dall'account, non più quella osservata nello spike OKX Demo di luglio.
> **Stato:** decisione presa, piano di implementazione prodotto (`docs/plans/strategy-consolidation-3-strategie-piano.md`). Zero codice toccato in questa sessione.

---

## 1. Correzione fee — perché cambia la prospettiva

Il documento `docs/analysis/scalping-strategies-analysis.md` e il piano `docs/plans/okx-sl-tp-recalibration-task.md` riportavano un round-trip fee OKX di 0,70% (taker 0,35% × 2), basato sullo screenshot del pannello fee OKX osservato l'11 luglio e sui dati dello spike Demo Trading. **Questo dato è ora superato**: la fee reale confermata sull'account è taker 0,10%, round-trip 0,20%.

Non è chiaro se il tier sia cambiato per volume di trading, per una promozione OKX, o se lo screenshot di riferimento fosse relativo a un periodo/account diverso — non rilevante ai fini pratici. Quello che conta: **il costo fisso per trade è 3,5 volte più basso** di quanto usato finora per calibrare SL/TP.

### Implicazione sui target attuali

Con SL netto 0,50% / TP netto 0,80% (valori attualmente in `scalping_risk_config`), la distanza lorda calcolata su round-trip 0,20% è:
- SL lordo ≈ 0,60%
- TP lordo ≈ 0,90%

Questi valori sono **già sostenibili** sul fee reale — non c'è urgenza di ricalibrare come temuto in un primo momento leggendo la documentazione storica (che assumeva ancora il fee alto). Il vecchio `TASK-OKX-RECAL` (SL 1,05%/TP 1,55%, pensato per round-trip 0,70%) è quindi **superato dai fatti**, anche se non revocato esplicitamente in questo recap — chi riprende questo lavoro deve sapere che i target attualmente in produzione (0,50%/0,80%) sono coerenti col fee reale attuale, non con quello documentato nei piani precedenti.

### Domanda aperta, non affrontata in questo piano

Con costi fissi più bassi, il sistema potrebbe sostenere una cadenza di trading più vicina allo scalping classico (SL/TP più stretti, più trade/giorno) rispetto al modello "micro-swing 10-30 trade/giorno" nato quando il fee era alto. Questa è una decisione di prodotto separata, esplicitamente **non presa** in questa sessione — va riaffrontata solo dopo aver osservato l'effetto del consolidamento strategico qui deciso.

---

## 2. Le 5 strategie runtime — cosa emerge dall'analisi long-only

| Strategia | Regime assegnato | Diagnosi |
|---|---|---|
| `rsi_bollinger` | ranging | 🟢 La più solida per il caso d'uso. Mean-reversion cattura bene il rimbalzo dal basso di un range, che esiste sempre indipendentemente dalla direzione generale del mercato |
| `ema_cross` | trending_up, trending_down | 🟡 Metà sprecata per costruzione. Su `trending_down` genera quasi solo segnali SELL, sistematicamente bloccati dal motore long-only (short cancellato, vedi `docs/analysis/audit-short-selling-cancelled.md`) |
| `stoch_rsi_bb_squeeze` | volatile | 🟡/⚪ Circa 50% dei segnali bloccati per costruzione (breakout direzionale casuale), e il regime `volatile` **non risulta mai osservato** in produzione secondo l'utente — quindi il problema è più teorico che pratico |
| `momentum_base` | unknown (fallback) | 🔴 Margine di trigger 0,01% sopra/sotto EMA9 — dentro il rumore di una candela 1m, non un edge misurabile. Il regime `unknown` è però solo un transiente iniziale (secondo l'utente), non uno stato persistente — quindi l'impatto pratico di questa debolezza è più limitato di quanto temuto leggendo `trend_analysis_report.md` (dove appariva nel 100% dei 19 trade pre-TASK-903) |
| `vwap_reversion` | *nessuno* | 🔴 Orfana — registrata in `registry.py` ma mai assegnata da `StrategySelector`/`config_loader.py`. Zero telemetria di produzione: non ha mai girato |

---

## 3. Decisione presa

Consolidare a **3 strategie realmente attive**, riassegnando i regimi:

```
ranging       → rsi_bollinger    (invariato)
trending_up   → ema_cross        (invariato)
trending_down → rsi_bollinger    (era ema_cross)
volatile      → vwap_reversion   (era stoch_rsi_bb_squeeze)
unknown       → vwap_reversion   (era momentum_base)
```

### Perché `rsi_bollinger` su `trending_down` è sicuro

Non serve costruire un nuovo stato "pausa" con eccezione manuale per i rimbalzi — il meccanismo **esiste già**: la Falling Knife Protection (TASK-906, in produzione dal 16/07) blocca l'override mean-reversion BUY quando il trend è in caduta verticale confermata (`trend_direction=="diverging"` + `trend_5m < -20.0`). Nei bearish "normali" (non crash), l'override tenta comunque il rimbalzo. Riassegnare il regime alla strategia giusta ottiene esattamente il comportamento "pausa nei crash, tenta il rimbalzo altrimenti" richiesto, riusando codice già testato invece di introdurne di nuovo.

### Perché `volatile` e `unknown` confluiscono entrambi su `vwap_reversion`

Nessuno dei due regimi giustifica una strategia dedicata separata:
- `volatile` non è mai stato osservato in produzione (secondo conferma diretta dell'utente)
- `unknown` è solo uno stato transiente a inizio sessione, prima che il regime si stabilizzi (non un regime persistente)

Un unico fallback (`vwap_reversion`, pensata esplicitamente per "qualsiasi regime, specialmente intraday" con soglia di distanza 0,2% da VWAP) è più solido del rumore di `momentum_base` e più semplice da monitorare di due strategie diverse per due casi degradati.

### Cosa NON si tocca

- `momentum_base.py` e `stoch_rsi_bb_squeeze.py` restano nel registry come opzioni tecnicamente disponibili — nessuna cancellazione di codice
- Il codice delle 3 strategie mantenute non viene modificato in questa fase — solo il mapping regime→strategia (interamente DB-driven da TASK-904, `scalping_runtime_config`)
- SL/TP restano quelli attuali (0,50%/0,80% netti) — coerenti col fee reale, nessuna urgenza di ricalibrazione
- I pesi del `SignalScoreEngine` (TASK-1159) restano bloccati in attesa di campione più ampio, come già deciso

---

## 4. Rischio noto e onestà sui limiti

`vwap_reversion` non ha **mai girato in produzione**. Questo consolidamento è, di fatto, anche il suo primo collaudo reale — non un semplice redeploy di logica nota e testata sul campo. Va osservata con attenzione superiore al solito nelle prime sessioni post-cambio (vedi Fase 4 del piano di implementazione).

Il vincolo strutturale di fondo (long-only + singolo simbolo) **non viene risolto** da questo consolidamento — resta tagliata fuori a monte tutta l'opportunità nei trend ribassisti confermati e parte dei breakout volatili. Questo intervento non genera nuovo edge: elimina spreco di cicli su combinazioni regime/strategia che sappiamo in anticipo produrre segnali sistematicamente bloccati, permettendo un uso più efficiente del campione di trade che il sistema riesce a raccogliere.

---

## 5. Prossimi passi

1. Eseguire il piano di implementazione (`docs/plans/strategy-consolidation-3-strategie-piano.md`, 4 fasi: config DB, default backend, dropdown frontend, osservazione post-deploy)
2. Dopo 15-20 trade con il nuovo mapping, query di verifica su distribuzione/win-rate per `strategy_type` × `regime`
3. Solo dopo aver validato che `vwap_reversion` si comporta come atteso, riaprire la discussione sospesa sulla cadenza di trading (scalping più stretto vs micro-swing attuale) alla luce del fee reale più basso
4. Aggiornare esplicitamente `docs/plans/okx-sl-tp-recalibration-task.md` con una nota di superamento (fee reale 0,20% round-trip, non 0,70%) per evitare che un futuro agente lo legga come ancora valido

---

## 6. File collegati

| File | Ruolo |
|---|---|
| `docs/analysis/scalping-strategies-analysis.md` | Mappa completa strategie/regime/config, base di questa analisi |
| `docs/plans/strategy-consolidation-3-strategie-piano.md` | Piano di implementazione operativo (questo recap ne è la motivazione) |
| `docs/plans/okx-sl-tp-recalibration-task.md` | **Superato** dal fee reale più basso — da annotare, non ancora aggiornato |
| `signal_aggregator.py` (TASK-906 Falling Knife) | Meccanismo riusato per rendere sicuro `rsi_bollinger` su `trending_down` |
| `config_loader.py` / `scalping_runtime_config` (TASK-904) | Meccanismo DB-driven che rende il riassegnamento regime→strategia possibile senza deploy di codice |
