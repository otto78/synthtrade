SynthTrade — Recap Errori Log Notturno (29-30 Giugno 2026)
Sessione analizzata: sess_03b55b8c
Periodo log: 29/06 20:19 → 30/06 08:47
Tipo documento: errori da controllare, non ancora verificati/risolti

1. Falso positivo tasks_alive dopo recovery da standby (🔴 NUOVO, da approfondire)
Dove: da 30/06 08:10:53 in poi, ogni 30s, fino alla fine del log (~40 minuti)
Session health check FAILED: ['tasks_alive'] (status=running, symbol=BNBUSDC, mode=live)
Osservazione: il sistema continua a processare candele, gestire PIPELINE e HOLD posizione normalmente — il trading non è impattato. Il check sembra non "resettarsi" dopo il restart dei task fatto dal watchdog.
Ipotesi da verificare: il check tasks_alive probabilmente confronta riferimenti a task asyncio salvati in uno stato di sessione che il watchdog non riassegna correttamente dopo aver ricreato i task (vedi punto 3).
Stato: non documentato nei recap precedenti — possibile bug nuovo. Da decidere se è un problema solo cosmetico (falso allarme nei log) o se nasconde un rischio reale (es. un task realmente morto che non viene rilevato perché il check è rotto).

2. Live trade failed — messaggio ancora troncato (🟡 conferma bug noto)
Dove: 30/06 20:26, 20:28, 20:29, 20:30, 20:31, 20:32 (5 occorrenze consecutive, una per minuto)
Live trade failed: ExchangeOrderError: binance POST https://api.binance.com/api/v3/order
Osservazione: stesso identico problema già descritto nel recap sessione 503b663d (29/06) — il body reale della risposta Binance non viene loggato, solo l'URL. Tutte le occorrenze seguono lo stesso pattern: MEAN-REVERSION BUY permesso → tentativo apertura → fallisce silenziosamente sul motivo.
Ipotesi plausibile (non confermata): saldo già eroso in sessione (alle 08:11 risulta USDC free=24.70), quindi probabile insufficient balance o MIN_NOTIONAL — ma senza il body completo non è verificabile con certezza.
Collegamento: la Fase 4 di SynthTrade_Piano_Logging_Decisionale_Livello1.md (loggare str(e) completo sull'eccezione CCXT) risolverebbe direttamente questo punto. A giudicare dal log, non risulta ancora applicata.
Da controllare: verificare nel codice (router.py) se il fix di logging è stato effettivamente applicato o solo pianificato.

3. Watchdog: gap dati di ~11h38m per standby PC (🟢 comportamento atteso, da confermare ok)
Dove: 30/06 08:09:57
CANDLE_PROC WATCHDOG: No data for 41875s. Force-reloading candles via REST API...
Osservazione: standby PC tra le 20:32 e le 08:09. Il watchdog ha reagito correttamente: reload REST di 100 candele, restart WS client, refresh balance. Stesso meccanismo già confermato funzionante nella sessione 503b663d.
Da controllare: se questo restart dei task è la causa root del falso positivo tasks_alive (punto 1) — cioè se il bug è proprio nella sequenza di restart innescata da questo watchdog.

4. Cascata job APScheduler "missed" al risveglio (🟢 conseguenza attesa del punto 3)
Dove: 30/06 08:10:04
Job mancati: heartbeat_job, monitor_pnl_job, intelligence_snapshot_job, session_health_job, run_active_strategies_job, verify_supervisor_outcomes_job, supervisor_check_job, run_pipeline_job (51 min di ritardo), funding_rate_update_job, spot_reconciliation_job (1h51m di ritardo).
Osservazione: tutti recuperati al primo run successivo, nessuna perdita di dati distruttiva osservata. Conferma indiretta del problema #15 già noto nel MASTER_RECAP (chiamate AI sincrone che bloccano il thread APScheduler).
Da controllare: se il ritardo di 51min/1h51m su pipeline e funding rate ha avuto impatti reali sulla qualità delle decisioni nella finestra di recovery (es. dati funding rate non aggiornati per quasi 2 ore).

5. OCO fallito per saldo insufficiente + market sell emergenza (🟢 comportamento già accettato by design)
Dove: 30/06 08:11:02
OCO placement FAILED: insufficient balance for requested action
OCO_FLOW CASO B: OCO fallito — eseguo market sell emergenza
Osservazione: comportamento auto-correttivo già accettato come corretto (sessione 22-23/06, "dust OCO"). Un minuto dopo, riprovato e riuscito (OCO ATTIVO: BUY BNBUSDC @ 552.17 | TP=554.93 | SL=550.51).
Da controllare: nessuna azione necessaria — solo verificare se la frequenza di questo evento sta aumentando nel tempo (potrebbe indicare un problema di sizing trade vs balance reale, non solo un caso isolato).

6. Rumore DNS FearGreed (🟢 non bloccante, solo pulizia log)
Dove: ricorrente ogni minuto per tutta la notte
FearGreed alternative.me error: Cannot connect to host api.alternative.me:443 ssl:default [Domain name not found]
FearGreed: uso cache (valore=12)
Osservazione: fallimento DNS locale, non un problema dell'endpoint. Fallback su cache funziona correttamente. Centinaia di righe di traceback completo per ogni occorrenza rendono il log poco leggibile.
Da controllare: non è un bug funzionale — solo valutare se vale la pena silenziare il traceback completo e tenere una riga di warning compatta dopo il primo fallimento consecutivo (per non perdere il segnale "è giù da X minuti" ma senza il rumore).

Riepilogo priorità
#PuntoPrioritàTipo1Falso positivo tasks_alive post-standby🔴 AltaBug nuovo, da indagare2Live trade failed ancora troncato🟡 MediaBug noto, fix non confermato applicato3Watchdog gap 11h38m🟢 BassaVerifica comportamento atteso4Cascata APScheduler missed🟢 BassaConseguenza nota, impatto da valutare5OCO insufficient balance + emergency sell🟢 BassaComportamento accettato, monitorare frequenza6Rumore DNS FearGreed🟢 BassaPulizia log, non funzionale
Nota: nessuna modifica al codice è stata fatta in questa sessione di analisi — solo lettura log, coerente col principio "one change at a time".