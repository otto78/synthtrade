# SynthTrade — Recap Sessione di Debug & Analisi (22-23 Giugno 2026)

> Riepilogo della conversazione di troubleshooting e analisi sul sistema di scalping BNBUSDC, condotta in parallelo su più strumenti AI (Claude, Gemini, DeepSeek).

---

## 1. Bug Identificati e Risolti

### 1.1 Disallineamento log "aperto" vs stato reale su Binance
**Sintomo:** la UI mostrava trade come "aperto" quando erano già chiusi su Binance (confermato via storico ordini reale).

**Causa:** `_update_closed_position_in_db()` cercava la riga "open" da aggiornare via match su `entry_price` come float — confronto fragile per arrotondamento Postgres FLOAT8. Quando il match falliva, scattava un fallback che faceva **INSERT** di una nuova riga `closed` invece di UPDATE sulla riga `open` esistente, lasciando quest'ultima orfana.

**Fix:** match primario via `oco_order_list_id` (univoco, deterministico), fallback legacy solo come extrema ratio. Proposta accompagnata da query di pulizia dei duplicati esistenti (con raccomandazione di backup prima dell'esecuzione).

**Stato:** ✅ Diagnosi confermata e fix proposto/discusso. Da verificare empiricamente sul prossimo ciclo di trade che il match `oco_order_list_id` funzioni anche su righe storiche dove il campo potrebbe essere NULL (pre-esistente al campo).

---

### 1.2 SignalScoreEngine — istanza duplicata (score live vs DB snapshot)
**Sintomo:** lo score "vivo" usato dal pipeline (~-3.3) e quello salvato/mostrato al supervisor (~-12.9) divergevano sistematicamente nello stesso istante.

**Causa:** router e snapshot job istanziavano due oggetti `SignalScoreEngine` separati invece di condividerne uno solo — quindi history, CVD calculator e stato interno erano disallineati.

**Fix:** introdotto pattern singleton via `get_or_create()` con registry di classe; CVD calculator condiviso automaticamente; grace period (`trades_count < 100`) per escludere il CVD dallo score durante l'inizializzazione; aggiunto `id(self)` nei log per verifica diretta.

**Stato:** ✅ Fix implementato. **Da verificare nei prossimi log live:** controllare che l'`id(self)` loggato da pipeline e da snapshot job coincidano (prova diretta, più affidabile del solo confronto dei valori di score).

**Attenzione residua:** la soglia di 100 trade per il grace period CVD è arbitraria e potenzialmente lunga su BNBUSDC (volume non altissimo) — da osservare quanti minuti richiede in pratica.

---

### 1.3 Quantità OCO / dust residuo (BUY vs SELL disallineati)
**Sintomo:** acquisto di una quantità (es. 0.034 BNB) e vendita di una quantità leggermente diversa (es. 0.033), con accumulo di "polvere" residua nel wallet.

**Percorso di diagnosi:** diversi tentativi (floor pre-buy, sottrazione fee stimata, lettura balance con delta pre/post buy) si sono rivelati ciascuno parzialmente corretto ma insufficiente, fino alla soluzione pragmatica adottata.

**Soluzione adottata:** lasciare il comportamento "auto-correttivo" del sistema — quando l'OCO richiede più di quanto il balance reale contiene (per fee), scatta un emergency market sell che vende tutto il disponibile, generando un piccolo dust che viene poi "assorbito" dal trade successivo. Comportamento accettato come corretto al livello di concetto, non più trattato come bug.

**Stato:** ✅ Chiuso concettualmente. Nessuna ulteriore azione richiesta a meno di anomalie di accumulo dust nel tempo.

---

### 1.4 hold_pnl_pct / vs Hold — discrepanza numerica
**Sintomo:** il valore "vs Hold" mostrato in UI non sembrava coerente con il calcolo manuale fatto confrontando il prezzo di primo trade e il prezzo di chiusura sessione letto dal grafico Binance.

**Stato:** ✅ **Risolto autonomamente dall'utente con Gemini** (dettagli della risoluzione non discussi in questa chat).

---

## 2. Funzionalità Implementate (Osservazione, non ancora operative)

### 2.1 Tracciamento trend Intelligence Score
**Motivazione:** lo score di Intelligence può essere in rapida convergenza/divergenza, ma il sistema lo trattava come valore statico — causando blocchi prolungati di breakout tecnici validi durante fasi di sentiment fortemente negativo che si stava già "raffreddando".

**Implementato:**
- `SignalScore` esteso con `trend_5m`, `velocity`, `trend_direction` (`converging`/`diverging`/`stable`)
- Coda circolare (`deque(maxlen=60)`) in `SignalScoreEngine` per la storia dello score
- Log dei BLOCK arricchiti con `[trend=+X.X converging/diverging/stable]`

**Verificato nei log:** il campo si popola correttamente e i valori numerici hanno senso (es. trend crescente +0.1 → +0.4 su score in lenta risalita). **Osservazione aperta:** con variazioni piccole ma persistenti (+0.3/+0.4 in pochi minuti) la classificazione resta `stable` — possibile soglia di sensibilità troppo larga per la classificazione testuale, da verificare con più dati.

**Stato:** 🟡 Attivo solo in modalità log/osservazione, come previsto dal piano "one change at a time". Non ancora usato operativamente nelle decisioni del signal_aggregator.

**Limite noto:** la history in RAM si azzera a ogni riavvio del processo (PC spento, crash, restart) — comportamento **corretto e voluto**, non un bug: dopo un'interruzione di ore il contesto di mercato è comunque cambiato, e mantenere la storia pre-riavvio falserebbe il trend.

---

### 2.2 Falling Knife Protection (proposta Gemini) — IN SOSPESO
**Contesto:** una sessione ha subito 5 stop-loss consecutivi perché l'eccezione "mean-reversion BUY permesso nonostante bias bearish" non ha un limite di sicurezza — durante un crollo verticale (falling knife), l'RSI tocca il fondo e il bot continua a comprare ad ogni mini-rimbalzo, venendo sistematicamente stoppato.

**Proposta di Gemini:** soglia fissa hardcoded (`score <= -10.0`) per annullare l'eccezione mean-reversion durante crolli estremi.

**Obiezione mossa in questa chat:**
1. La soglia `-10.0` rischia overfitting su un singolo evento osservato, senza dati storici sul comportamento dello score durante i mean-reversion "buoni" (ranging benigno)
2. Manca la dimensione di **velocità**: un crollo verticale si distingue meglio dalla *velocità di deterioramento* dello score (`trend_direction == diverging`) che dal solo valore assoluto
3. Il trend tracking appena implementato (punto 2.1) non era ancora collegato a questo punto del codice (l'eccezione mean-reversion), quindi non si avevano ancora dati con `trend=` calcolato durante un vero episodio di falling knife per validare l'ipotesi

**Stato:** 🔴 **Non implementato.** In attesa di un nuovo episodio di crollo verticale con il trend-logging attivo *anche nel ramo mean-reversion* (oggi loggato solo nel ramo BLOCK generico) per decidere la soglia/condizione in modo informato.

**Azione consigliata prima di procedere:** estendere il logging del trend anche al ramo `⚡ MEAN-REVERSION BUY permesso` per avere il dato disponibile al prossimo episodio.

---

## 3. Issue Architetturali Aperti (da `SynthTrade_Scalping_DataFlow_Reference.md`)

| Issue | Priorità | Stato |
|---|---|---|
| SHORT non supportato — stimati ~15-22 segnali SELL persi in due sessioni distinte osservate | 🔴 Alta | Noto, in roadmap (fasi 1-4 già pianificate) |
| Supervisor non ha visibilità sul blocco SHORT nel prompt — continua a proporre `update_threshold`/`change_strategy` quando il vero blocco è architetturale | 🟢 Bassa (fix semplice) | **Non discusso in dettaglio in questa chat** — proposta: aggiungere una riga nel context del supervisor che segnali esplicitamente l'assenza di supporto SHORT |
| APScheduler job "missed" ripetuti, causati probabilmente da chiamate AI sincrone che bloccano il thread principale | 🟡 Media | **Non affrontato in questa chat** — fix proposto: isolare le chiamate AI in `ThreadPoolExecutor` (era già nei piani precedenti dell'utente) |
| CryptoCompare/RSS feed intermittenti (`getaddrinfo failed`) | 🟡 Media | Non affrontato in questa chat |
| Possibile bias nella metrica `outcome_label` del supervisor: in mercato laterale, quasi ogni `no_action` produce delta PnL vicino a zero, dando una falsa impressione di "decisioni corrette" indipendentemente dalla loro reale qualità | 🟡 Media | Segnalato come osservazione concettuale, nessuna azione presa |

---

## 4. Comportamento del Supervisor — Osservazioni dai Log

- In una sessione, il supervisor ha modificato `signal_strength_threshold` **5 volte** (8.0 → 6.0 → 5.5 → 7.5 → 10.5) e cambiato strategia 2 volte nell'arco di poche ore.
- La soglia alzata a 10.5 a fine sessione **persiste nella sessione successiva** dopo riavvio — nessun meccanismo di decadimento o rivalutazione al cambio di contesto/giorno. Possibile area di miglioramento futura, non affrontata in dettaglio.
- Il bug "BLOCKING SHORT ENTRY" ha vanificato diverse modifiche di soglia fatte dal supervisor: la soglia non era il vero collo di bottiglia in quei momenti, ma il supervisor non aveva modo di saperlo.

---

## 5. Proposte di Miglioramento — Non ancora implementate

Raccolte da tutta la conversazione, in ordine di impatto stimato:

1. **Aggiungere contesto macro (BTC change 1h/24h, `macro_regime`)** ai trade salvati — gap identificato all'inizio della conversazione come prerequisito per permettere al supervisor di distinguere "la strategia ha fallito" da "tutto il mercato crollava". *Risulta già parzialmente implementato secondo il documento di riferimento (TASK-866: `btc_price_at_entry`, `btc_change_1h_pct`, `btc_change_24h_pct`, `macro_regime`) — da confermare se attivo e popolato correttamente.*
2. **Persistere anche le decisioni di BLOCK/REJECTED**, non solo i trade eseguiti — oggi se non si arriva all'esecuzione, l'informazione resta solo nei log testuali (volatili), impedendo al supervisor di imparare dai casi di "blocco prolungato ingiustificato" come quello del 22/06.
3. **Estendere il trend-logging al ramo mean-reversion** (prerequisito per la Falling Knife Protection, punto 2.2).
4. **Inserire nel system prompt del supervisor la nota sul blocco SHORT** per evitare azioni inefficaci.
5. **Isolare le chiamate AI sincrone** dal thread principale di APScheduler.
6. **Rivedere la sensibilità della classificazione `trend_direction`** (soglie per `stable`/`converging`/`diverging`) alla luce dei primi dati osservati.
7. **Valutare un meccanismo di decadimento/reset della soglia dinamica** tra sessioni o cambi di regime di mercato significativi.

---

## 6. Metodologia Osservata

In linea con il principio "one change at a time" già adottato dall'utente:
- Le nuove funzionalità (trend tracking) sono state introdotte **solo in modalità log/osservazione**, senza impatto operativo immediato sulle decisioni di trading.
- Le proposte di soglie hardcoded (Falling Knife Protection) sono state messe in discussione prima dell'implementazione, in attesa di dati osservativi reali invece che di numeri scelti per intuito.
- Più bug sono stati diagnosticati attraverso il confronto diretto tra log applicativi e storico ordini reale su Binance — pratica che ha permesso di scoprire il disallineamento "aperto/chiuso" (punto 1.1).

---

*Recap generato il 23 Giugno 2026, a copertura del periodo di analisi 21-23 Giugno 2026.*
