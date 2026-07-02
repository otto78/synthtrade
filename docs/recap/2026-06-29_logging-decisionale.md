SynthTrade — Piano di Implementazione: Persistenza Log Decisionale (Livello 1)
Data: 29 giugno 2026
Obiettivo: dare al futuro AI Supervisor (e a qualsiasi analisi storica) dati grezzi interrogabili su ogni decisione del sistema — non solo i trade eseguiti — senza ancora toccare il Supervisor stesso.
Principio guida: una fase = una modifica verificabile, nessuna fase parte prima che la precedente sia confermata in log/DB reali. Nessuna stima: ogni campo deve venire da un dato realmente disponibile nel codice esistente, non da un valore calcolato "a occhio".
Fuori scope per questo piano: modifiche al ContextBuilder, al SUPERVISOR_SYSTEM_PROMPT, o a qualunque logica di decisione del Supervisor. Questo piano si ferma alla scrittura dei dati. La lettura/uso da parte del Supervisor è un piano successivo (Livello 2/3).

Perché queste fasi e non altre
Oggi (vedi sessione 503b663d come caso reale) il sistema produce moltissime informazioni a runtime — PIPELINE: regime=... strategy=... tech=... intel=..., BLOCK: conflitto intelligence-tecnico, MEAN-REVERSION BUY permesso, Live trade failed — ma solo come righe di log testuale, che:

non sono interrogabili (nessuna query "quanti BLOCK su ema_cross in regime ranging questa settimana")
si perdono nel rumore di centinaia di righe APScheduler/heartbeat
in caso di errore exchange, troncano il body reale della risposta (vedi punto 1.2 del recap sessione 503b663d)

Le 5 fasi sotto risolvono questi problemi nell'ordine di dipendenza tecnica più basso possibile: prima la tabella e lo schema (Fase 1), poi il logging delle decisioni (Fase 2), poi il collegamento outcome (Fase 3), poi la qualità dei dati di errore (Fase 4), infine la vista derivata di sola lettura (Fase 5) — che è l'unico pezzo "aggregato", ma resta a livello di query, non di Supervisor.

Fase 1 — Schema DB: tabella session_signal_log
Cosa fare:
Creare in Supabase una nuova tabella (migration SQL), senza toccare nessuna tabella esistente.
sqlCREATE TABLE session_signal_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    symbol TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- snapshot del contesto al momento della decisione
    regime TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    tech_signal TEXT,                  -- BUY/SELL/HOLD/CLOSE
    tech_confidence NUMERIC(5,3),
    intel_score NUMERIC(6,2),
    intel_bias TEXT,                   -- bullish/bearish/neutral
    trend_direction TEXT,              -- converging/diverging/stable
    trend_value NUMERIC(6,2),

    -- esito della decisione
    decision_type TEXT NOT NULL CHECK (decision_type IN (
        'execute', 'block_conflict', 'mean_reversion_override',
        'hold_existing_position', 'rejected_other'
    )),
    decision_reason TEXT,              -- testo libero, es. "conflitto intelligence-tecnico"

    -- collegamento al trade, se la decisione ha portato a un trade (Fase 3)
    trade_id UUID REFERENCES scalping_trades(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signal_log_session ON session_signal_log(session_id, decided_at);
CREATE INDEX idx_signal_log_strategy_regime ON session_signal_log(strategy_type, regime);
CREATE INDEX idx_signal_log_decision_type ON session_signal_log(decision_type);
Perché questi campi: ricalcano esattamente i campi già presenti in ogni riga PIPELINE: del log attuale (regime=, strategy=, tech=BUY@0.75, intel=-9.4 (bearish), [trend=-5.7 diverging]) — nessun campo nuovo da inventare, solo da persistere quello che già viene calcolato e loggato a runtime.
Task da generare:

Scrivere la migration SQL (file in supabase/migrations/)
Applicare la migration su Supabase, verificare con query diretta che la tabella esista con lo schema corretto (stesso pattern di verifica già usato per scalping_risk_config nella sessione del 20/06)

Verifica di completamento Fase 1: tabella visibile su Supabase, zero righe, nessun impatto sul codice applicativo esistente (la tabella non è ancora scritta da nessuno).

Fase 2 — Scrittura: loggare ogni decisione del SignalAggregator/ExecutionLoop
Cosa fare:
Nei punti del codice dove oggi viene solo loggato testualmente uno dei seguenti eventi, aggiungere una scrittura su session_signal_log:
Evento attuale (log testuale)File notodecision_typePIPELINE: ... tradeable=True seguito da DECISION APPROVEDexecution_loop.py / router.pyexecuteBLOCK: conflitto intelligence-tecnicosignal_aggregator.pyblock_conflictMEAN-REVERSION BUY permesso ... nonostante bias=bearishsignal_aggregator.pymean_reversion_overrideHOLD: existing BUY position matches BUY signalexecution_loop.pyhold_existing_positionaltri DECISION REJECTED non coperti soprarouter.pyrejected_other
Importante — un solo punto di scrittura: centralizzare in una funzione unica (es. _log_signal_decision(...)) chiamata da tutti i punti sopra, per evitare 5 implementazioni divergenti dello stesso insert (stesso errore già visto con la fee hardcoded duplicata in 6 punti — da non ripetere).
Task da generare:

Creare funzione helper _log_signal_decision() in router.py o in un nuovo modulo signal_log_writer.py
Collegare la funzione ai 5 punti della tabella sopra, uno alla volta, verificando in log/DB dopo ciascun collegamento che la riga venga scritta con i valori giusti
Decidere e documentare la politica di errore: se l'insert su Supabase fallisce, NON deve bloccare il trading — loggare l'errore e continuare (stesso principio già adottato per "Balance check failed (non-blocking)")

Verifica di completamento Fase 2: dopo una sessione live di test, contare le righe in session_signal_log e confrontarle a mano con il numero di righe PIPELINE:/BLOCK:/MEAN-REVERSION nel log testuale della stessa sessione — devono corrispondere 1:1 (stesso tipo di verifica già fatta per il bilancio storico).

Fase 3 — Collegamento trade_id: outcome della decisione
Cosa fare:
Quando un trade viene effettivamente chiuso (_close_position_and_record o equivalente), aggiornare la riga session_signal_log con decision_type='execute' corrispondente, impostando trade_id con l'id del trade chiuso appena creato in scalping_trades.
Punto critico da chiarire prima di scrivere codice: qual è la chiave di match tra la riga di log "execute" (scritta in Fase 2, al momento dell'apertura) e il trade chiuso (creato/aggiornato alla chiusura)? Candidati, in ordine di preferenza:

session_id + timestamp di apertura più vicino (match temporale, fragile come il bug già noto su entry_price float — da evitare se possibile)
Aggiungere un campo signal_log_id su scalping_trades, popolato subito dopo l'insert della riga in Fase 2, prima di piazzare l'ordine — così il collegamento è per ID, non per timestamp o prezzo (preferibile, stesso principio del fix già fatto sul bug "aperto/chiuso" che ha sostituito un match fragile su float con un ID univoco)

Task da generare:

Aggiungere colonna signal_log_id UUID REFERENCES session_signal_log(id) a scalping_trades (migration separata)
Popolare signal_log_id nel punto di apertura trade (subito dopo l'insert di Fase 2, prima dell'ordine Binance)
Verificare su un trade reale chiuso che il join session_signal_log.trade_id ↔ scalping_trades.id (o l'inverso via signal_log_id) restituisca la riga corretta

Verifica di completamento Fase 3: su almeno 3 trade chiusi reali, query di join che recupera regime/strategy/intel_score al momento dell'apertura insieme al PnL finale — confrontati a mano con quanto visibile nei log testuali dello stesso trade.

Fase 4 — Qualità dati di errore: body completo eccezioni Binance
Cosa fare:
Risolve direttamente il punto 1.2 della sessione 503b663d (blocco "Live trade failed" 16:38-16:44, messaggio troncato).
Nel blocco try/except attorno a place_market_order/place_oco_order (probabilmente in router.py, dove oggi si logga solo Live trade failed: binance POST ...), loggare il body completo dell'eccezione CCXT:
pythonexcept ccxt.BaseError as e:
    logger.error(f"Live trade failed: {e}")  # invece di un messaggio troncato
    # opzionale: anche e.args se str(e) non basta a includere il body HTTP
Aggiungere anche al session_signal_log (collegandosi alla Fase 1) un nuovo decision_type='execution_error' con decision_reason contenente il messaggio d'errore completo — così un fallimento exchange non collassa nello stesso "non-evento" indistinguibile di un blocco intelligence o di un semplice no-signal (problema descritto nel punto 3.5 del recap del 29/06).
Task da generare:

Modificare il logging dell'eccezione per includere il body completo (fix isolato, basso rischio, nessuna modifica a logica di trading)
Aggiungere execution_error come valore valido del CHECK constraint su decision_type (richiede ALTER TABLE se la Fase 1 è già in produzione)
Collegare il punto di catch dell'eccezione alla scrittura session_signal_log con decision_type='execution_error'

Verifica di completamento Fase 4: riprodurre (o attendere) un nuovo fallimento Live trade failed e confermare che il log mostri il body reale (es. insufficient balance, LOT_SIZE, MIN_NOTIONAL) invece del messaggio troncato attuale.

Fase 5 — Vista di sola lettura: win rate per (strategy, regime)
Cosa fare:
Unica fase "aggregata" del piano, ma resta una query, non uno stato salvato/accumulato — coerente con la decisione presa di evitare sia il recap testuale illimitato sia il bilancio cumulativo senza bordi temporali.
sqlCREATE VIEW signal_outcome_by_strategy_regime AS
SELECT
    sl.strategy_type,
    sl.regime,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(COUNT(t.id) FILTER (WHERE t.pnl > 0)::numeric / NULLIF(COUNT(t.id), 0) * 100, 1) AS win_rate_pct,
    ROUND(AVG(t.pnl), 4) AS avg_pnl,
    ROUND(SUM(t.pnl), 4) AS total_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE sl.decision_type = 'execute'
GROUP BY sl.strategy_type, sl.regime;
Volutamente non parametrizzata su una finestra temporale fissa in questa fase — la decisione su finestra mobile (ultimi 14gg / ultimi N trade) è una scelta di design che riguarda come il Supervisor consumerà questo dato (Livello 2/3, fuori scope), non come viene calcolato qui. In questa fase la vista resta semplice e verificabile a mano.
Task da generare:

Creare la vista SQL
Verificarla contro il bilancio storico già calcolato a mano (18 sessioni, 70 trade, 34.3% win rate aggregato) — la somma di n_trades su tutte le righe della vista deve coincidere con 70, a meno di trade precedenti all'introduzione della Fase 1-3 (che ovviamente non hanno signal_log_id e quindi non compariranno: comportamento corretto, da documentare esplicitamente come limite noto, non bug)

Verifica di completamento Fase 5: query eseguita su Supabase, risultati confrontati a mano con almeno una sessione reale già nota (es. 503b663d: ci si aspetta una riga rsi_bollinger/ranging e una riga ema_cross/trending_up o trending_down coerenti con quanto già analizzato).

Riepilogo sequenza task (per generazione ticket)
#FaseTipo modificaRischioDipendenze1Schema session_signal_logMigration SQLBassissimo (nessun codice applicativo toccato)Nessuna2Scrittura decisioni (5 punti)Backend, nuova funzione + 5 call siteBasso (solo aggiunta, nessuna modifica a logica esistente)Fase 13Collegamento trade_id/signal_log_idMigration + backendMedio (tocca il flusso di apertura trade, va testato su trade reale)Fase 1, 24Fix logging errori BinanceBackend, fix isolatoBassissimoFase 1 (per il nuovo decision_type)5Vista aggregataSQL view, sola letturaBassissimo (nessuna scrittura, nessun impatto su trading)Fase 1, 2, 3
Nota per chi genera i task: ogni fase deve essere un task (o gruppo di task) chiuso e verificato con dati reali prima di passare alla successiva — esattamente come da principio "one change at a time" già in uso nel progetto. Non aprire la Fase 3 prima che la Fase 2 sia confermata da almeno una sessione live; non aprire la Fase 5 prima che la Fase 3 abbia almeno un trade reale collegato correttamente.
Esplicitamente escluso da questo piano: qualsiasi modifica al ContextBuilder, al prompt del Supervisor, o introduzione dello shadow tracking sui BLOCK (proposta 3.6 del recap del 29/06) — quello richiede prima che i dati di questo piano esistano e siano verificati, ed è materia di un piano successivo (Livello 2/3).