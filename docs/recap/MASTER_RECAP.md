# SynthTrade — MASTER RECAP DI PROGETTO

**Generato il:** 26 giugno 2026
**Fonte:** consolidamento di 8 documenti di recap sessione (20-28 giugno 2026)
**Scopo:** punto di riferimento unico per capire cosa è stato fatto, cosa è ancora aperto, e dove riprendere

---

## Indice

1. [Cronologia sessioni](#1-cronologia-sessioni)
2. [Cosa è stato portato a termine (confermato)](#2-cosa-è-stato-portato-a-termine-confermato)
3. [Bug ancora aperti](#3-bug-ancora-aperti)
4. [Proposte/architetture progettate ma non implementate](#4-proposte-architetture-progettate-ma-non-implementate)
5. [Cose da verificare empiricamente (nessun bug noto, ma non confermate)](#5-cose-da-verificare-empiricamente)
6. [Stato dei moduli architetturali principali](#6-stato-dei-moduli-architetturali-principali)
7. [Contraddizioni/punti da chiarire tra sessioni](#7-contraddizioni-punti-da-chiarire-tra-sessioni)
8. [Cosa manca ancora, in ordine di impatto suggerito](#8-cosa-manca-ancora-in-ordine-di-impatto-suggerito)

---

## 1. Cronologia sessioni

| Data | Sessione | Focus principale |
|---|---|---|
| 20/06 | Audit Risk Controls & Roadmap | Verifica reale di cosa funziona nei Risk Controls; pianificazione Supervisor+log e short |
| 22-23/06 | Debug & Analisi | Bug log/Binance, SignalScoreEngine duplicato, dust OCO, trend tracking Intelligence Score |
| 24-25/06 | Fee/PnL Trasparenza (TASK-876→886) | Fee hardcoded errata, commissioni reali da WS, net SL/TP |
| 25/06 | Mean-Reversion Bug & Short Selling | 4° stop_loss consecutivo, causa = comportamento intenzionale ma regime detection inaffidabile |
| 26/06 | EMA Angle / Short Selling Margin / Wallet Orchestrator | Solo analisi: margin Binance, WalletOrchestrator, EMA slope |
| 26/06 | Trailing Stop Loss Strategy | Solo analisi: nuova strategia "growth" con SL variabile |
| 27-28/06 | Strategie Scalping, Bug Fix a Cascata & Regressione | Sessione più operativa: nuova strategia implementata, regressione, rollback |

**Nota metodologica:** alcuni argomenti (sync bug strategia, short selling, fee/PnL, regime detection) sono stati toccati in più sessioni in momenti diversi. In questo recap riporto lo **stato più recente conosciuto**, non quello della singola sessione in cui sono stati menzionati per la prima volta.

---

## 2. Cosa è stato portato a termine (confermato)

### 2.1 Risk Controls (20/06)
- ✅ Confermato via codice reale che **Stop Loss e Take Profit sono realmente applicati** (calcolano i prezzi OCO reali su Binance).
- ✅ Confermato che **Max Daily Loss è realmente applicato** (`_check_daily_loss()` blocca nuovi trade).
- ✅ Confermato (e accettato come stato attuale, non bug) che **Leverage non è mai letto da nessuna logica di trading** — solo salvato/mostrato, coerente con margin non ancora implementato.
- ✅ Confermato che **Max Drawdown non blocca nulla** — solo metrica storica scollegata dalla soglia configurata.
- ✅ Fix: aggiunto `updated_at` al payload di upsert in `update_risk_config` (`router.py`).
- ✅ Fix: campi Leverage/Max Drawdown disabilitati in UI con badge "non attivo" (`risk-controls.component.ts`).
- ✅ Test end-to-end: cambio `max_daily_loss` 10→2 via UI, verificato persistito su Supabase — **persistenza confermata al 100%**.
- ✅ Risolto dubbio sulla migration SQL mancante: la tabella `scalping_risk_config` esiste, la migration che la crea semplicemente non era stata allegata in chat.

### 2.2 Debug 22-23/06
- ✅ **Bug "aperto" vs "chiuso" su Binance**: causa identificata (match fragile su `entry_price` float), fix proposto/discusso con match primario su `oco_order_list_id`.
- ✅ **SignalScoreEngine duplicato** (score live ≠ score DB snapshot): fix implementato con pattern singleton `get_or_create()`, CVD calculator condiviso, grace period CVD (`trades_count < 100`), `id(self)` nei log per verifica.
- ✅ **Dust OCO/quantità BUY-SELL disallineate**: chiuso concettualmente — comportamento auto-correttivo (emergency market sell su mismatch) accettato come corretto, non più trattato come bug.
- ✅ **hold_pnl_pct / vs Hold**: risolto autonomamente dall'utente con Gemini (dettagli non discussi con Claude).
- ✅ **Trend tracking Intelligence Score** (`trend_5m`, `velocity`, `trend_direction`) implementato e verificato nei log come funzionante in modalità osservazione/log-only.

### 2.3 Fee/PnL Trasparenza (24-25/06)
- ✅ Causa radice identificata con certezza: fee hardcoded `0.1%` simmetrica in 6 punti di `router.py`, mentre la realtà è maker=0.001/taker=0.00095 (confermato da log reale).
- ✅ Causa aggravante risolta: `user_data_stream.py` ora cattura `n`/`N` (commissione reale) dal payload WS invece di scartarli.
- ✅ `get_trade_fee()` implementato in `exchange.py`, chiamato all'avvio sessione live.
- ✅ Tutte le 6 occorrenze hardcoded `0.001` sostituite con lettura da `_execution_state["fee_tier"]` — verificate, nessun residuo.
- ✅ Calcolo e broadcast di `stop_loss_pct_net`/`take_profit_pct_net` (target netti dopo fee) verso il frontend — confermato nel codice.
- ✅ Fix minore di scope su `exchange` recuperato esplicitamente da `_execution_state`.

### 2.4 Mean-Reversion Bug (25/06)
- ✅ Causa del 4° stop_loss consecutivo chiarita con certezza dai log: **non un bug**, comportamento intenzionale di `rsi_bollinger` che compra contro il bias quando classifica il mercato come "ranging". Il problema reale è l'affidabilità della classificazione regime, non la logica di eccezione mean-reversion in sé.
- ✅ Calcolo campo "Investito" (20→19.44 USDC) spiegato: non è la fee, è **LOT_SIZE rounding** (floor allo stepSize Binance) — confermato anche nei log (`qty_raw=0.0344...→qty_precise=0.034, step_size=0.001`).
- ✅ Matematica win/loss asimmetrica chiarita concettualmente (expectancy).
- ✅ Pannello Performance disallineato dal Trade Log (Total Trades 2 vs 3): confermato **auto-risolto** tra uno screenshot e il successivo nella stessa sessione.

### 2.5 EMA Angle / Margin / Wallet Orchestrator (26/06) — solo analisi, nessun codice nel progetto
- ✅ Meccanismo EMA slope come proxy di momentum chiarito, snippet `_compute_ema_slope()` proposto.
- ✅ Minimo borrow Binance Margin chiarito da fonti ufficiali: `userMinBorrow` = 0 per USDC, vincolo reale è il `minNotional` del pair.
- ✅ Meccanismo short (borrow→sell→buy→repay) spiegato con esempio numerico.
- ✅ Chiarito che il collaterale richiesto è l'asset di garanzia (USDC) nel Margin account, non l'asset preso a prestito.
- ✅ Identificata Universal Transfer API (`POST /sapi/v1/asset/transfer`) per movimenti Funding/Spot/Margin.
- ✅ Identificato endpoint dedicato per riscatto Earn→Spot (`POST /sapi/v1/simple-earn/flexible/redeem`).
- ✅ Architettura `WalletOrchestrator` disegnata come snippet completo (snapshot→resolve→execute→verify).

### 2.6 Trailing Stop Loss (26/06) — solo analisi, nessun codice nel progetto
- ✅ Idea validata concettualmente e mappata sul pattern noto "Trailing Stop Loss / Chandelier Exit".
- ✅ 4 varianti TSL presentate (Percentage, ATR/Chandelier, Parabolic SAR, Swing Low) con raccomandazione su ATR Trailing Stop.
- ✅ Proposta di separazione architetturale Entry (SignalAggregator standard) / Exit (loop trailing periodico separato).

### 2.7 Strategie Scalping & Bug Fix a Cascata (27-28/06)
- ✅ Analisi completa delle 4 strategie esistenti (EMA Cross, Momentum Base, RSI+Bollinger, VWAP Reversion) con valutazione robustezza per regime.
- ✅ Bug risolto: `rsi_bollinger` e `vwap_reversion` non erano mappate nel `StrategySelector` — fix applicato.
- ✅ Nuova strategia **`stoch_rsi_bb_squeeze`** implementata e registrata (`registry.py`).
- ✅ Risolto: "nessun segnale tecnico in live".
- ✅ Risolto: soglia `tradeable` incoerente (14.1 < soglia 14.1) — ora dinamica (`signal_score_engine.py`).
- ✅ Diagnosticato stato 8 collector intelligence: funzionanti (Fear&Greed, Long/Short, Open Interest = 0.30), non funzionanti (Funding Rate, CVD, Sentiment, Whale, On-Chain = 0.70).
- ✅ Risolto: USDC non visibili in Spot — erano nel Funding wallet.
- ✅ Risolto: oscillazione del Supervisor tra strategie — cooldown 20 minuti (`supervisor_scheduler.py`).
- ✅ Risolto: Supervisor assegnava `ema_cross` anche in regime ranging — whitelist regime→strategia (`supervisor_scheduler.py`, `supervisor_client.py`).
- ✅ Soglie RSI/BB abbassate (`rsi_bollinger.py`).
- ✅ Script PowerShell per la gestione dei processi uvicorn orfani (parent+worker via `netstat -ano`) fornito.
- ✅ Decisione presa: **rollback** delle modifiche del 27/06 che avevano causato la regressione, con ordine di re-implementazione incrementale definito (vedi sezione 8).

---

## 3. Bug ancora aperti

| # | Bug | Prima osservato | Stato/dettaglio | Priorità suggerita |
|---|---|---|---|---|
| 1 | **`strategy_selected` vs `strategy_executed` sync bug** — UI Strategy panel mostra strategia sbagliata (es. "Momentum Base" mentre i log mostrano `strategy=rsi_bollinger`) | 20/06, confermato di nuovo il 25/06 con screenshot+log | Bug di frontend Angular probabile (valore non aggiornato all'evento giusto, o agganciato a stato stantio). **Bloccante** per alimentare il Supervisor con dati di sessione attendibili. Mai fixato in nessuna sessione. | 🔴 Alta — quick fix, specializzazione Angular dell'utente |
| 2 | **Regressione 27-28/06: sessione non produce log/trade** | 27-28/06 | Causa identificata: doppio avvio `_start_ws_broadcast()` (uno da `main.py` in fase di restore, uno da nuovo start da frontend). Fix **non applicato** — si è scelto il rollback invece del fix diretto. | 🔴 Alta — bloccante operativo |
| 3 | **Buffer mismatch warmup/ExecutionLoop** | 27-28/06 | Non risolto | 🔴 Alta |
| 4 | **`pause_trading` permanente su regime `unknown`** | 27-28/06 | Fix non applicato | 🔴 Alta — il bot si blocca e non riparte da solo |
| 5 | **`Position.entry_commission` non popolato** — campo dataclass esiste (TASK-876) ma `PositionManager.open_position()` non lo accetta come parametro, resta sempre `None` | 24-25/06 | Patch scritta (punto A) per `exchange.py`, `position_manager.py`, `router.py` — **non confermata applicata** | 🟡 Media — impatta precisione PnL su entry |
| 6 | **`get_trade_fee()` fallback silenzioso** a `{maker:0.001, taker:0.001}` in caso di errore | 24-25/06 | Patch scritta (punto B): flag `fee_tier_certified: bool` — **non confermata applicata** | 🟡 Media |
| 7 | **`GET /position` non converte BNB→USDC** per `entry_commission_asset` (assunzione di codice "non possiamo chiamare exchange qui" probabilmente errata, l'endpoint è async) | 24-25/06 | Patch scritta (punto C) — **non confermata applicata** | 🟡 Media |
| 8 | **SELL mean-reversion bloccato da bias bullish** (simmetrico al problema BUY mean-reversion vs bias bearish) | 27-28/06 | Solo proposto, non implementato | 🟡 Media |
| 9 | **Insufficient funds per minNotional** | 27-28/06 | Fix scritto in `router.py`, **non confermato end-to-end** | 🟡 Media |
| 10 | **Assenza di cooldown dopo consecutive losses** (trade riapertosi 42s dopo uno stop_loss, senza pausa, nonostante 3 perdite consecutive in quadro Extreme Fear) | 20/06, ribadito 25/06 | Proposta: `cooldown_minutes` + `_check_cooldown()` sul modello di `_check_daily_loss()`. **Non implementato.** Distinto dal cooldown strategia esistente (20 min). | 🟡 Media |
| 11 | **Regime misclassification** (volume-confirmed breakdown classificato come ranging) — causa architetturale radice della "Falling Knife" | 22-23/06, ribadito 25/06 | Nessuna soluzione implementata. Soluzione preferita: `trend_direction`/velocità invece di soglia statica hardcoded (proposta Gemini `score <= -10.0` respinta per rischio overfitting) | 🔴 Alta — root cause di più sintomi osservati |
| 12 | **Falling Knife Protection non implementata** | 22-23/06, 25/06 | In attesa di un nuovo episodio con trend-logging attivo anche nel ramo mean-reversion (oggi loggato solo nel ramo BLOCK generico) per validare la soglia/condizione in modo informato | 🟡 Media — dipende dal punto 11 |
| 13 | **`trend_direction` classificato `stable` anche con variazioni piccole ma persistenti** (+0.3/+0.4 in pochi minuti) | 22-23/06 | Possibile soglia di sensibilità troppo larga, da verificare con più dati | 🟢 Bassa |
| 14 | **Supervisor non ha visibilità sul blocco SHORT** nel system prompt — propone `update_threshold`/`change_strategy` quando il vero blocco è architetturale (assenza short) | 22-23/06 | Fix semplice proposto (riga di contesto nel system prompt), **non implementato** | 🟢 Bassa (fix facile, impatto medio) |
| 15 | **APScheduler job "missed" ripetuti**, probabile causa: chiamate AI sincrone che bloccano il thread principale | 22-23/06 | Fix proposto: isolare chiamate AI in `ThreadPoolExecutor` — non affrontato in nessuna sessione successiva | 🟡 Media |
| 16 | **CryptoCompare/RSS feed intermittenti** (`getaddrinfo failed`) | 22-23/06 | Non affrontato | 🟢 Bassa |
| 17 | **Bias nella metrica `outcome_label` del Supervisor**: in mercato laterale, quasi ogni `no_action` produce delta PnL ~0, dando falsa impressione di "decisioni corrette" | 22-23/06 | Solo osservazione concettuale, nessuna azione presa | 🟢 Bassa |
| 18 | **Soglia dinamica del Supervisor senza decadimento**: `signal_strength_threshold` cambiata 5 volte in una sessione (8.0→6.0→5.5→7.5→10.5), persiste tra sessioni dopo riavvio senza rivalutazione | 22-23/06 | Non affrontato; parzialmente mitigato dal cooldown 20min introdotto il 27-28/06, ma nessun meccanismo di decadimento/reset implementato | 🟡 Media |
| 19 | **Collector Intelligence non funzionanti**: Funding Rate, CVD, Sentiment, Whale Alert, On-Chain (5 su 8, ~70% del layer Intelligence) | 27-28/06 | Solo diagnosticato, nessun fix applicato | 🔴 Alta — il layer Signal Intelligence è il cuore architetturale del progetto (v2.0), e oggi opera al 30% della capacità prevista |
| 20 | **Slope filter su EMA Cross causa di regressione** | 27-28/06 | Causa nota di regressione; nella sequenza di rollback è l'ultimo step ("decidere su slope filter") — nessuna decisione presa su se/come reintrodurlo. Nota dal 26/06: il progetto aveva già rimosso un filtro di slope EMA in passato — motivo non chiarito | 🟡 Media |

---

## 4. Proposte/architetture progettate ma non implementate

### 4.1 Short Selling (architettura completa, zero codice nel progetto)
Architettura a 4 fasi, confermata coerente su più sessioni (25/06, 26/06):

1. **Fase 1 — Borrow/repay isolato e testabile** (`margin_short.py`, solo testnet): `open_short()` (borrow+sell), `close_short()` (buy+repay). **Prossimo passo concordato e non ancora iniziato.**
   - Alternativa emersa il 26/06: `sideEffectType: "AUTO_BORROW_REPAY"` su `create_margin_order`, che automatizza borrow/repay — da validare su testnet e decidere se sostituisce o si combina con `margin_short.py` manuale.
2. **Fase 2 — Entry-side awareness nel `signal_aggregator`**: decisione di prodotto aperta tra short trend-following (consigliato per iniziare) vs short anche mean-reversion (più rischioso).
3. **Fase 3 — OCO mirrorato**: TP sotto l'entry, SL sopra, PnL invertito (entry−exit) ovunque oggi si assume long-only.
4. **Fase 4 — Risk Controls/StrategySelector simmetrici**: % SL/TP per direzione, non solo long.

**Dettagli tecnici raccolti il 26/06 (margin):**
- `userMinBorrow` = 0 per USDC; vincolo reale = `minNotional` del pair.
- Margin Level minimo 1.1 (liquidazione), buffer sicuro consigliato >2.0.
- Isolated Margin raccomandato per lo scalping short.
- Collaterale: serve USDC nel Margin account, non l'asset preso a prestito; con leva 5x, 10-15 USDC fissi coprono trade da 10 USDC sia long che short.
- Interessi orari trascurabili per scalping (~0.0001 USDC/ora su trade da 10 USDC).

**WalletOrchestrator** (lavoro propedeutico, non scritto nel progetto):
- Architettura a 4 fasi: `snapshot()` (legge tutti i wallet in parallelo) → `resolve()` (puro, calcola piano minimo di trasferimenti, priorità Spot→Funding→Earn) → `execute()` → `verify()` (polling con retry).
- Entry point: `ensure_funded(asset, required, target)`.
- Collocazione proposta: `app/execution/wallet_orchestrator.py`.
- Richiede: Universal Transfer API (`POST /sapi/v1/asset/transfer`, con permesso "Permits Universal Transfer" abilitato sulla API Key) + endpoint dedicato Earn→Spot.

### 4.2 Trailing Stop Loss Strategy ("Growth Strategy")
- Nuovo tipo strategia proposto: `StrategyType.TREND_FOLLOW_TSL`.
- Solo Stop Loss, nessun Take Profit; SL si alza col prezzo, mai scende; nessuna uscita "di proposito".
- Raccomandazione: **ATR Trailing Stop (Chandelier Exit)** come punto di partenza — il moltiplicatore ATR è il parametro naturale da affidare al Supervisor AI.
- Entry: stesso gate del `SignalAggregator` esistente (Intelligence Score + filtro tecnico).
- Exit: loop periodico separato (APScheduler, frequenza da decidere) che ricalcola e aggiorna lo SL via API Binance.
- **Punti non decisi:**
  - Dove collocare nel codice (struttura `strategies/`, integrazione `StrategySelector`/`registry.py`)
  - Frequenza di rivalutazione del trailing (ogni candle? ogni N minuti? agganciata al ciclo Supervisor 5-15 min?)
  - Comportamento su regime change (uscita forzata anticipata vs lasciare lavorare solo il trailing?)
  - Se competere con le altre 4 strategie nella selezione regime, o essere complementare/attivabile solo in `TRENDING_UP` forte
  - Interazione con Risk Manager esistente (max daily loss, consecutive losses), dato che questa strategia non ha mai un take profit che chiude il ciclo nel modo classico
  - Collegamento naturale con Short Selling (stessa logica TSL mirrorata per posizioni short, una volta implementate)

### 4.3 Market Structure / Supporti-Resistenze
- Nuovo collector proposto: **`MarketStructureCollector`** — deriva supporti/resistenze da swing high/low su dati OHLCV già disponibili, clusterizzando livelli vicini pesati per numero di "touch".
- Uso: evitare entry contro resistenza forte, o piazzare SL oltre il livello strutturale più vicino invece che a % fissa.
- Distinto dal concetto di "muri" da order book depth (endpoint `depth` Binance) — fonte dati più rumorosa, da considerare come segnale separato nel `SignalScoreEngine`.
- **Flag `volume_confirmation`** proposto in combinazione: rottura con volume >1.5-2x media recente → breakout reale; avvicinamento senza volume anomalo → probabile test/rimbalzo.
- Raccomandazione metodologica: backtestare il rilevamento livelli isolatamente prima di agganciarlo a decisioni live ("one change at a time").

### 4.4 Supervisor AI — miglioramenti proposti, non implementati
- Job di riflessione periodica del Supervisor: digest in tempo reale + job APScheduler periodico con tabella `supervisor_notes`.
- Persistere anche le decisioni di BLOCK/REJECTED, non solo i trade eseguiti — oggi l'informazione resta solo nei log testuali volatili.
- Nota nel system prompt sul blocco architetturale SHORT (vedi bug #14 sopra).
- Isolare le chiamate AI sincrone dal thread principale APScheduler (vedi bug #15).
- Rivedere sensibilità soglie `trend_direction` (`stable`/`converging`/`diverging`).
- Meccanismo di decadimento/reset della soglia dinamica tra sessioni o cambi di regime significativi.
- Schema esteso `session_trade_log` con `regime_confidence` numerico e `signal_breakdown` jsonb.
- Vista mismatch in UI sulla pagina session log: evidenziare righe dove strategia selezionata ≠ eseguita (utile come debug manuale e come data-quality gate prima di alimentare il Supervisor).
- Badge di confidenza regime sulla riga del log.

### 4.5 UI/UX minori (Angular)
- Toast di conferma su Save Config (oggi "fire and forget", solo `console.error` su errore) — riusare il pattern evento custom `scalping-error` già esistente.
- Centralizzare l'accesso al fee tier in una singola funzione `get_fee_tier()` invece dei vari `_execution_state.get("fee_tier", {...})` sparsi nel codice.
- Distinguere visivamente in UI tra "target netto atteso" (pre-chiusura, da fee tier) e "PnL realizzato" (post-chiusura, da commissioni reali) — backend fornisce già entrambi i dati separatamente, non verificato se il frontend Angular li espone distintamente.
- Estendere la cattura di commissione reale anche al lato paper/mock trading (oggi intenzionalmente lasciato a fee tier puro — scelta da documentare come tale, non come gap).

### 4.6 Macro context per Supervisor (TASK-866)
- Campi `btc_change_1h_pct`, `btc_change_24h_pct`, `macro_regime` per permettere al Supervisor di distinguere "la strategia ha fallito" da "tutto il mercato crollava".
- **Nota di stato (dal recap 22-23/06):** risulterebbe già parzialmente implementato secondo il documento di riferimento del progetto (`btc_price_at_entry`, `btc_change_1h_pct`, `btc_change_24h_pct`, `macro_regime`) — **da confermare se attivo e popolato correttamente**, nessuna sessione successiva l'ha verificato.

---

## 5. Cose da verificare empiricamente

Punti dove il codice/fix esiste (o si ritiene esista) ma manca una verifica end-to-end su dati reali:

1. **Fee/PnL — verifica end-to-end su trade reale chiuso**: nessun trade è stato osservato e confrontato a mano dopo i fix di Fasi 1-3 (fee tier reale, cattura commissione WS, eliminazione hardcode) per certificare che il calcolo finale di PnL usi davvero i numeri corretti. Era il punto D esplicito della sessione 24-25/06, **mai chiuso nelle sessioni successive**.
2. **Patch A/B/C fee/PnL** (entry_commission, fee_tier_certified, conversione BNB→USDC in `/position`) — fornite come patch testuali precise, non confermate applicate né testate.
3. **Frontend Angular — rendering di `stop_loss_pct_net`/`take_profit_pct_net`**: non verificato se il componente card POSITION espone questi due nuovi campi separatamente dai valori lordi.
4. **Match `oco_order_list_id`** per il fix del bug "aperto/chiuso" (22-23/06): da verificare che funzioni anche su righe storiche dove il campo potrebbe essere `NULL` (pre-esistente all'introduzione del campo).
5. **Singleton `SignalScoreEngine`**: da verificare nei log live che l'`id(self)` loggato da pipeline e da snapshot job coincidano (prova diretta più affidabile del solo confronto valori).
6. **Soglia grace period CVD** (100 trade): arbitraria, potenzialmente lunga su BNBUSDC — da osservare quanti minuti richiede in pratica.
7. **Fix `insufficient funds per minNotional`** (27-28/06): scritto ma non testato end-to-end.
8. **Fix `pause_trading` permanente** e **buffer mismatch warmup**: secondo il recap 27-28/06 risultano "non risolto"/"fix non applicato" — da ripianificare esplicitamente nel rollback.

---

## 6. Stato dei moduli architetturali principali

| Modulo | Stato | Note |
|---|---|---|
| **Execution Engine (L1)** | 🟢 Operativo, con bug noti | SL/TP/Max Daily Loss reali; regressione 27-28/06 in corso di rollback |
| **Risk Manager** | 🟡 Parziale | SL, TP, Max Daily Loss reali; Leverage e Max Drawdown decorativi (per design attuale) |
| **Signal Intelligence Layer** | 🔴 30% funzionante | Solo Fear&Greed, Long/Short Ratio, Open Interest attivi; Funding Rate, CVD, Sentiment, Whale Alert, On-Chain non funzionanti — gap critico dato che è il cuore architetturale v2.0 |
| **Strategie tecniche** | 🟢 4+1 implementate | EMA Cross, Momentum Base, RSI+Bollinger, VWAP Reversion + nuova `stoch_rsi_bb_squeeze`; mapping regime→strategia fixato il 27-28/06 |
| **Regime Detector** | 🔴 Inaffidabile | Misclassifica breakdown con volume come ranging — root cause di più sintomi (falling knife, mean-reversion contro-trend) |
| **AI Supervisor** | 🟡 Operativo con limiti noti | Cooldown 20min e whitelist regime→strategia fixati; bias `outcome_label`, mancanza di consapevolezza del blocco SHORT, soglie senza decadimento |
| **Short Selling** | 🔴 Zero implementazione | Architettura completa a 4 fasi pronta, nessun codice scritto |
| **Fee/PnL transparency** | 🟡 Strutturalmente fixato, verifica empirica mancante | Fix principali applicati; asimmetria entry/exit residua nota; nessuna verifica end-to-end su trade reale |
| **Trailing Stop Loss** | 🔴 Solo proposta | Nessun codice, nessuna decisione su collocazione |
| **Market Structure (S/R)** | 🔴 Solo proposta | `MarketStructureCollector` non esiste ancora |
| **Wallet Orchestrator** | 🔴 Solo snippet di riferimento | Non scritto nel progetto reale |
| **Frontend Angular** | 🟡 Funzionale con bug noto | Sync bug strategia selezionata/eseguita mai fixato; risk-controls component aggiornato |

---

## 7. Contraddizioni/punti da chiarire tra sessioni

- **Slope filter EMA**: nella sessione del 26/06 emerge che "il progetto ha già rimosso un filtro di slope dall'EMA Cross in passato" (motivo non chiaro), ma poi nella sessione 27-28/06 lo slope filter su EMA21 risulta tra le modifiche applicate **e** tra le cause della regressione, con decisione finale di rimuoverlo di nuovo nel rollback. Vale la pena, quando si riprende, **documentare esplicitamente perché lo slope filter continua a essere instabile** prima di una terza introduzione.
- **Stato dei campi macro (TASK-866)**: il recap 22-23/06 dice che risulterebbero "già parzialmente implementati secondo il documento di riferimento del progetto" ma **nessuna sessione successiva conferma se sono realmente attivi e popolati**. Da verificare prima di considerarlo chiuso o aperto.
- **AUTO_BORROW_REPAY vs `margin_short.py` manuale**: emerso il 26/06 come alternativa al piano Fase-1 già esistente, ma non è stata presa una decisione su quale dei due approcci usare per partire.

---

## 8. Cosa manca ancora, in ordine di impatto suggerito

Sintesi operativa per la prossima sessione, basata sulla severità e sulle dipendenze osservate tra i punti:

### 🔴 Bloccanti/alta priorità
1. **Fix regressione 27-28/06**: doppio avvio `_start_ws_broadcast()`, buffer mismatch warmup, `pause_trading` permanente su regime unknown. Senza questi, il sistema potrebbe non produrre trade/log in modo affidabile.
2. **Sync bug `strategy_selected` vs `strategy_executed`**: bloccante per qualunque lavoro futuro sul Supervisor basato su dati di sessione attendibili. Quick fix lato Angular.
3. **Regime Detector inaffidabile**: root cause di Falling Knife, mean-reversion contro-trend, e probabilmente di parte dell'instabilità del Supervisor. Considerare `MarketStructureCollector` + `volume_confirmation` come prossimo passo concreto, in isolamento ("one change at a time").
4. **Collector Intelligence non funzionanti** (5 su 8): il layer Signal Intelligence è il principio guida v2.0 del progetto ("le strategie tecniche sono filtri, il segnale primario viene dall'intelligence") — oggi opera al 30%. Vale la pena capire perché Funding Rate, CVD, Sentiment, Whale, On-Chain non funzionano prima di costruire altro sopra un layer monco.

### 🟡 Media priorità
5. **Ordine di re-implementazione già deciso il 27-28/06** (da seguire): minNotional → soglia dinamica → soglie RSI/BB → bypass SELL mean-reversion → cooldown → whitelist → fix pause → nuova strategia (`stoch_rsi_bb_squeeze`) → decidere su slope filter.
6. **Patch fee/PnL A/B/C** (entry_commission, fee_tier_certified, conversione BNB→USDC) + verifica empirica end-to-end mai fatta — chiudere definitivamente il capitolo fee/PnL apertosi il 24-25/06.
7. **Cooldown su consecutive losses** (`cooldown_minutes` + `_check_cooldown()`), distinto dal cooldown strategia.
8. **Short Selling Fase 1**: `margin_short.py` isolato su testnet, oppure validare prima `AUTO_BORROW_REPAY` per decidere l'approccio.

### 🟢 Bassa priorità / quando il resto è stabile
9. Nota SHORT nel system prompt del Supervisor.
10. Isolare chiamate AI sincrone in `ThreadPoolExecutor` (APScheduler missed jobs).
11. Trailing Stop Loss Strategy (decisioni di collocazione e integrazione ancora tutte aperte).
12. Wallet Orchestrator (propedeutico solo quando si parte sul serio con il margin/short).
13. Toast di conferma su Save Config e altri micro-miglioramenti UI Angular.
14. Meccanismo di decadimento soglia dinamica Supervisor tra sessioni.

---

## Nota finale

Il principio "one change at a time" e "niente stime, solo dati reali" è stato rispettato nella maggior parte delle sessioni di analisi (20/06, 22-23/06, 24-25/06), mentre la sessione 27-28/06 è stata la più "a cascata" (molte modifiche correlate insieme) ed è quella che ha prodotto la regressione che ha richiesto il rollback. Vale la pena, riprendendo da qui, tornare rigorosamente al ritmo incrementale per ciascuno dei punti 🔴 sopra elencati.
