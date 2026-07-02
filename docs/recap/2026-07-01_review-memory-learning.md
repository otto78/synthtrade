SynthTrade — Recap Sessione: Review Epica Memory & Learning Supervisor AI
Data: 1 luglio 2026
Contesto: review critica del report "EPICA MEMORY & LEARNING SUPERVISOR AI" (Livelli 1-3, dichiarato "COMPLETATO ✅ / PRODUCTION READY") fatta da un altro strumento/sessione, seguita da verifica diretta sui dati reali via Supabase MCP.

1. Obiettivo della sessione
Validare le affermazioni del report Memory & Learning contro:

i principi cardine del progetto ("one change at a time", "no estimates, only real data")
i gate di verifica espliciti definiti in SynthTrade_Piano_Logging_Decisionale_Livello1.md (Fasi 1-5)
lo stato noto di bug pregressi (sync bug strategia, regime detection inaffidabile, campione dati limitato)


2. Punti sollevati nella review iniziale (analisi a tavolino, pre-verifica DB)
#PuntoStato a fine sessione1Livello 2/3 dichiarati "completati" senza menzione delle verifiche empiriche richieste esplicitamente dal piano originale (Fase 2 confronto 1:1 log↔DB, Fase 3 su almeno 3 trade reali, Fase 5 confronto col bilancio storico noto)🟡 Verificato via Supabase in questa sessione — vedi sezione 32Bug sync strategy_selected vs strategy_executed non menzionato nel report, nonostante fosse segnato come bloccante nel MASTER_RECAP✅ Confermato dall'utente come già risolto (fix non discusso in questa chat)3Soglie usate nella regola performance storica (n_trades>=10, win_rate 35%/70%) potenzialmente arbitrarie/overfitting su campione piccolo (70 trade totali storici)🟡 Osservazione concettuale, non ri-verificata quantitativamente in questa sessione4Comportamento reale della regola "performance storica → change_strategy" mai osservato su un caso vivo🟡 In corso di osservazione da parte dell'utente, appena iniziato — vedi finding rilevante in sezione 35Dati storici usati per il training/context (70 trade, 18/06-29/06) includono periodo pre-fix fee/PnL — possibile "contaminazione" del win rate storico🟡 Segnalato, non affrontato in questa sessione

3. Verifica diretta su Supabase (progetto vnxijoyiarmaihqrwnsq)
3.1 — Copertura scalping_trades.signal_log_id (Fase 3 del piano logging)
sqlSELECT COUNT(*) AS total_closed_trades,
       COUNT(*) FILTER (WHERE signal_log_id IS NOT NULL) AS with_signal_log_id
FROM scalping_trades WHERE status = 'closed';
Risultato: 106 trade chiusi totali, 20 con signal_log_id popolato. Analizzando la sequenza temporale: tutti i trade con entry_time >= 2026-06-29 12:57:02 hanno il campo popolato (20/20), tutti quelli precedenti sono NULL (86/86) — nessun buco intermedio, transizione netta e pulita.
✅ Esito: Fase 3 del piano logging risulta correttamente e stabilmente attiva da fine giugno. Comportamento coerente con quanto atteso (i trade pre-esistenti all'introduzione del campo non possono averlo, per design — non un bug).
3.2 — Distribuzione decision_type su session_signal_log
sqlSELECT decision_type, COUNT(*) FROM session_signal_log GROUP BY decision_type;
decision_typenhold_existing_position319rejected_other301execute102block_conflict34execution_error18mean_reversion_override0
🔴 Bug trovato: mean_reversion_override non viene mai scritto.
Query mirata su righe che corrispondono esattamente al pattern documentato più volte nel progetto (rsi_bollinger BUY con bias bearish):
sqlSELECT decision_type, COUNT(*) FROM session_signal_log
WHERE strategy_type='rsi_bollinger' AND intel_bias='bearish' AND tech_signal='BUY'
GROUP BY decision_type;
→ 44 righe, tutte con decision_type='execute'. Il mapping a 5 valori previsto in Fase 2 del piano logging non distingue più un'esecuzione "pulita" da un override mean-reversion contro il bias — esattamente il dato che sarebbe servito per validare/confutare la Falling Knife Protection (mai implementata, in attesa di dati con trend_direction sul ramo mean-reversion).
🔴 Secondo problema: segnali SELL scartati (short non implementato) loggati come execute.
sqlSELECT tech_signal, COUNT(*) FROM session_signal_log WHERE decision_type='execute' GROUP BY tech_signal;
→ SELL: 56, BUY: 46. Più della metà delle righe execute sono SELL — segnali che sappiamo con certezza vengono scartati (nessuna implementazione short), quindi non sono mai diventati ordini reali. Osservato anche ri-logging ripetuto ogni minuto per lo stesso segnale persistente sulla stessa sessione (es. 307997ef..., 10 righe SELL identiche consecutive 12:44→12:55) — possibile assenza di guardia "logga solo al cambio di decisione".
Questo spiega il gap numerico osservato: 102 righe execute contro 25 trade realmente aperti nella stessa finestra temporale.
3.3 — Integrità della vista aggregata (Fase 5, signal_outcome_by_strategy_regime)
sqlSELECT * FROM signal_outcome_by_strategy_regime ORDER BY n_trades DESC;
strategy_typeregimen_tradeswin_rate_pctavg_pnlrsi_bollingerranging1811.1-0.0444ema_crosstrending_up20.0-0.0500
✅ La vista NON è inquinata dai due bug sopra. Il JOIN passa per signal_log_id (popolato solo sui trade reali all'apertura), quindi le righe fantasma (SELL scartate, override mal etichettati come execute semplice) restano non collegate e non entrano nel calcolo. Somma corretta: 18+2 = 20, coincide esattamente col conteggio di 3.1.
3.4 — Finding rilevante per il punto 4 (comportamento regola performance storica)
rsi_bollinger/ranging ha già superato la soglia n_trades >= 10 prevista da TASK-902, con un win rate dell'11.1% — ben sotto la soglia del 35% che dovrebbe far scattare "considera fortemente change_strategy". Non verificato in questa sessione se questa regola ha effettivamente prodotto una decisione osservabile del Supervisor — segnalato come primo caso reale utile da controllare, dato che il punto 4 è "appena iniziato" lato utente.

4. Conclusione della sessione
Il Livello 1 (Fase 1-3-5 dello schema/scrittura/vista) risulta strutturalmente solido e verificato sui dati reali: nessun buco di copertura, nessuna contaminazione della vista aggregata. Il problema non è nell'infrastruttura DB ma nella qualità semantica di due dei cinque decision_type scritti dalla Fase 2 — bug isolato, a basso rischio di fix, che non richiede di rifare nulla del lavoro già svolto su Livello 2/3.
Non modifica la validità del Livello 2 (historical context builder) e Livello 3 (integrazione nel prompt) rispetto ai dati che effettivamente usano (la vista, non la tabella grezza) — ma va comunque risolto prima di usare session_signal_log per qualunque analisi futura più fine-grained (es. shadow tracking sui BLOCK, proposta 3.6 del recap 29/06, o qualunque studio sul comportamento mean-reversion vs bias).
I due bug trovati sono stati trasformati in task dettagliati — vedi documento collegato SynthTrade_TASK_Fix_Signal_Log_Decision_Types.md.

5. File prodotti in questa sessione

Questo recap
SynthTrade_TASK_Fix_Signal_Log_Decision_Types.md — task pronti per l'implementazione