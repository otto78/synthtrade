# SynthTrade — Riepilogo Completo: Dati Sessione Scalping & Supervisore AI

> **Versione:** 1.0 — Giugno 2026  
> **Fonte:** Analisi multi-agente (Cline/DeepSeek · Kilo · Claude Code/Laguna · Copilot/Laguna) + log sessione live BNBUSDC

---

## 1. Schema Relazionale Completo

```
scalping_sessions
    ├── scalping_trades          (FK: session_id)          — 1 a molti
    ├── supervisor_memory        (FK: session_id CASCADE)  — 1 a molti
    └── supervisor_decisions     (FK: session_id)          — legacy, deprecata

market_intel_snapshots   — per symbol, indipendente dalla sessione
opportunities            — deduplicata per content_hash
scalping_runtime_config  — config dinamica (es. signal_strength_threshold)
```

---

## 2. Dati Salvati per Tabella

### 2.1 `scalping_sessions` — La Sessione Madre

Creata all'avvio, aggiornata a ogni trade chiuso e allo stop.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `id` | UUID (PK) | Identificatore univoco |
| `mode` | TEXT | `paper` / `live` / `backtest` |
| `symbol` | TEXT | Es. `BNBUSDC` |
| `timeframe` | TEXT | Default `1m` |
| `status` | TEXT | `running` / `paused` / `stopped` |
| `started_at` / `stopped_at` | TIMESTAMPTZ | Durata sessione |
| `total_pnl` | NUMERIC | PnL cumulato sessione |
| `trade_count` / `win_count` | INTEGER | Statistiche trade |
| `strategy` / `active_strategy` | TEXT | Strategia corrente |
| `strategy_params` | JSONB | Parametri strategia attiva |
| `risk_config` | JSONB | Configurazione risk (SL%, TP%, max loss) |
| `trade_value` | NUMERIC | USD per singolo trade (default 100) |

**Trigger:** INSERT all'avvio → UPDATE dopo ogni trade chiuso → UPDATE finale allo stop.

---

### 2.2 `scalping_trades` — I Trade Eseguiti

Un record per ogni apertura di posizione; aggiornato alla chiusura.

**Dati base:**

| Campo | Descrizione |
|-------|-------------|
| `session_id` | FK → scalping_sessions |
| `side` | `BUY` / `SELL` |
| `entry_price` / `exit_price` | Prezzi di ingresso e uscita |
| `quantity` | Quantità asset |
| `pnl` / `pnl_pct` | Profitto/Perdita assoluto e percentuale |
| `strategy_type` | Es. `rsi_bollinger`, `ema_cross` |
| `signal_reason` | Testo descrittivo del segnale (es. "RSI oversold + BB touch") |
| `status` | `open` / `closed` / `cancelled` |
| `entry_time` / `exit_time` | Timestamp precisi |
| `tp_price` / `sl_price` | Livelli TP/SL impostati |
| `oco_order_list_id` | ID lista OCO Binance |
| `sl_order_id` / `tp_order_id` | ID singoli ordini Binance |
| `binance_order_id` | Ordine principale |

**Contesto intelligence al momento dell'entry:**

| Campo | Descrizione |
|-------|-------------|
| `signal_score` | Score aggregato SignalScoreEngine (-100/+100) |
| `funding_rate_at_entry` | Funding rate Binance Futures al momento |
| `fear_greed_at_entry` | Fear & Greed Index (0-100) |
| `cvd_trend_at_entry` | Trend CVD (`bullish`/`bearish`/`neutral`) |

**Contesto macro-BTC (aggiunto in TASK-866):**

| Campo | Descrizione |
|-------|-------------|
| `btc_price_at_entry` | Prezzo BTC al momento dell'entry |
| `btc_change_1h_pct` | Variazione BTC 1h |
| `btc_change_24h_pct` | Variazione BTC 24h |
| `macro_regime` | Regime macro (es. `trending_down`) |

**Contesto TA (analisi tecnica avanzata):**

| Campo | Descrizione |
|-------|-------------|
| `candlestick_pattern` | Pattern candlestick rilevato |
| `volume_anomaly` | Boolean — volume anomalo rilevato |
| `regime_classified` | Regime classificato dall'engine |
| `support_resistance_data` | JSONB dati S/R al momento |
| `slippage_pct` | Slippage effettivo sull'ordine |
| `signal_to_fill_ms` | Latenza segnale → fill ordine |
| `strategies_considered` | Lista strategie valutate |
| `strategy_rejection_reason` | Perché le altre strategie sono state scartate |

**Trigger:** INSERT su `_save_open_position_to_db()` → UPDATE su `_update_closed_position_in_db()` (match per `oco_order_list_id` o fallback `session_id+entry_price+entry_time`).

---

### 2.3 `supervisor_memory` — Decisioni AI (tabella principale)

Sostituisce la tabella legacy `supervisor_decisions`. Più ricca di contesto.

| Campo | Descrizione |
|-------|-------------|
| `session_id` | FK → scalping_sessions (CASCADE DELETE) |
| `symbol` | Symbol su cui opera la sessione |
| `action` | `change_strategy` / `update_params` / `update_threshold` / `pause_trading` / `resume_trading` / `no_action` |
| `reason` | Spiegazione in italiano dell'AI |
| `confidence` | Float 0–1 |
| `market_bias` | `bullish` / `bearish` / `neutral` |
| `primary_signal` | Segnale che ha guidato la decisione |
| `new_strategy` | Nuova strategia (se action = change_strategy) |
| `new_params` | JSONB nuovi parametri (se action = update_params) |
| `was_applied` | Boolean — la decisione è stata effettivamente applicata? |
| `blocked_reason` | Testo se `was_applied = false` (es. cooldown attivo) |
| `market_context` | JSONB snapshot completo mercato: regime, funding, score, CVD, OI |
| `session_perf` | JSONB performance sessione: trade totali, wins, losses, PnL, win_rate, ultimi 5 trade |
| `outcome_verified_at` | TIMESTAMPTZ — quando è stato verificato l'outcome |
| `outcome_pnl_delta` | NUMERIC — delta PnL misurato 25-35min dopo la decisione |
| `outcome_label` | `positive` / `negative` / `neutral` |

**Trigger:** INSERT a ogni tick supervisor (ogni 10 minuti) → UPDATE da `verify_supervisor_outcomes_job` (ogni ~3 minuti, verifica decisioni applicate 25-35 min fa).

---

### 2.4 `market_intel_snapshots` — Snapshot Intelligence Periodici

| Campo | Descrizione |
|-------|-------------|
| `symbol` | Symbol monitorato |
| `funding_rate` | Funding rate Binance Futures |
| `open_interest` | Open interest in USD |
| `long_pct` / `short_pct` | % posizioni long/short |
| `cvd_trend` | `bullish` / `bearish` / `neutral` |
| `fear_greed_value` / `fear_greed_label` | Valore e classificazione F&G |
| `signal_score` | Score aggregato corrente |
| `signal_bias` | Bias del segnale |
| `recorded_at` | Timestamp snapshot |

**Trigger:** INSERT ogni 60 secondi dal `intelligence_snapshot_job`.  
**Index:** `(symbol, recorded_at DESC)` per query storiche efficienti.

---

### 2.5 `scalping_runtime_config` — Config Dinamica

Tabella chiave-valore per configurazioni modificabili a runtime dal supervisor.

| Configurazione | Descrizione |
|----------------|-------------|
| `signal_strength_threshold` | Soglia score per eseguire trade (default ~10.5, range 5.0–30.0) |

**Trigger:** UPDATE da `ParameterUpdater` quando il supervisor decide `update_threshold`.  
*Log osservato:* `Updating signal strength threshold to: 5.0` alle 11:38:30 — il supervisor ha abbassato la soglia dopo molti `no_action` consecutivi su mercato neutro.

---

### 2.6 `opportunities` — Opportunità Rilevate

| Campo | Descrizione |
|-------|-------------|
| `source` | `binance_rss` / `cryptopanic` / `coingecko` / `whale_alert` |
| `category` | `new_listing` / `launchpool` / `promotion` / `delisting` / `irrelevant` |
| `urgency` | `high` / `medium` / `low` |
| `scalping_opportunity` | Boolean |
| `title` / `action` | Titolo e azione suggerita |
| `symbol` | Symbol se applicabile (nullable, indicizzato) |
| `content_hash` | UNIQUE — chiave di deduplicazione |
| `classified_by_ai` | Boolean |
| `user_action` | `watched` / `ignored` / `acted` |

---

## 3. Stato In-Memory (`_execution_state`)

Dati live mantenuti in RAM durante la sessione — non persistiti tra restart (con eccezione del recovery da DB).

```python
_execution_state = {
    "session": {
        "session_id": str,
        "status": "running|paused|stopped",
        "mode": "live|paper",
        "strategy": str,
        "symbol": str,
        "paper_balance": float,     # solo in paper mode
        "live_balance": float,      # solo in live mode
        "trade_value": float,       # USD per trade
        "started_at": str,
    },
    "position_manager": PositionManager,  # posizione aperta corrente + info OCO
    "execution_loop": ExecutionLoop,       # loop principale
    "risk_config": RiskConfig,            # max_daily_loss, SL%, TP%, leverage
    "candle_buffer": CandleBuffer,        # 100+ candele storiche
    "signal_engine": SignalScoreEngine,   # motore score con _score_history (deque maxlen=60)
    "ws_client": BinanceWSClient,
    "supervisor_scheduler": SupervisorScheduler,
}
```

**Componenti critici in-memory:**
- `_score_history` (deque maxlen=60): ultimi 60 score per calcolo trend (`trend_5m`, `velocity`, `trend_direction`)
- `CVDCalculator`: accumulatore real-time dei trade WebSocket per calcolo CVD
- `CandleBuffer`: 50 candele warmup + buffer circolare continuo

---

## 4. Flusso Completo di Archiviazione

```
AVVIO APP
    └─> Lifespan checks DB per sessione "running" → restore _execution_state
        └─> INSERT scalping_sessions (se nuova) o aggiorna in-memory (se restore)

OGNI CANDELA CHIUSA (1 minuto)
    └─> ExecutionLoop._process_candle()
        ├─> RegimeDetector → aggiorna regime corrente
        ├─> StrategySelector → seleziona strategia per regime
        ├─> SignalScoreEngine → aggiorna score da tutti i collector
        ├─> SignalAggregator → decide execute/block
        │
        ├─ Se EXECUTE (BUY/SELL approvato):
        │   ├─> OrderExecutor.place_oco_order() → Binance REST
        │   ├─> PositionManager.open_position()
        │   └─> _save_open_position_to_db() → INSERT scalping_trades (status=open)
        │
        └─ Se BLOCK → log reason, nessun DB write

EVENTO OCO FILL (via UserDataStream)
    └─> _update_closed_position_in_db()
        ├─> UPDATE scalping_trades (exit_price, pnl, status=closed)
        └─> UPDATE scalping_sessions (total_pnl, trade_count, win_count)

OGNI 60 SECONDI
    └─> intelligence_snapshot_job()
        └─> INSERT market_intel_snapshots

OGNI 10 MINUTI
    └─> SupervisorScheduler._run_tick()
        ├─> build_scalping_context() → assembla tutto il contesto
        ├─> SupervisorClient → chiamata AI (cascade modelli)
        ├─> ParameterUpdater.apply() → aggiorna parametri/strategia/threshold
        └─> INSERT supervisor_memory (con was_applied + market_context + session_perf)

OGNI ~3 MINUTI
    └─> verify_supervisor_outcomes_job()
        └─> UPDATE supervisor_memory (outcome_pnl_delta, outcome_label)
            per decisioni applicate 25-35 minuti fa
```

---

## 5. Il Supervisore AI — Funzionamento Dettagliato

### 5.1 Input: Cosa Riceve il Supervisor

Il `ContextBuilder` assembla un contesto strutturato che include:

**Performance sessione:**
- Trade totali, win count, loss count
- Win rate percentuale
- PnL totale sessione
- Ultimi 5 trade con PnL e `signal_reason` (per pattern analysis)
- Perdite consecutive correnti

**Intelligenza di mercato (snapshot corrente):**
- Score aggregato SignalScoreEngine con breakdown per collector
- Regime corrente (`ranging` / `trending_up` / `trending_down` / `volatile`)
- Funding rate e bias contrarian
- CVD trend e velocità
- Open Interest con baseline rolling
- Long/Short ratio
- Fear & Greed Index
- Coverage % dei collector attivi (fondamentale per affidabilità)

**Storico decisioni (ultime 10):**
- Azioni prese, reason, was_applied, outcome_label
- Usato per prevenire loop di decisioni duplicate

**Contesto TA:**
- Pattern candlestick bullish/bearish count
- Volume anomaly flag
- Soglia corrente signal_strength_threshold

**Prompt esplicito** include: score corrente, gap vs threshold, threshold attiva, lista collector attivi.

---

### 5.2 Output: Azioni Disponibili

| Action | Trigger tipico | Effetto immediato |
|--------|---------------|-------------------|
| `change_strategy` | Regime cambiato, strategia incompatibile | Swap strategia al prossimo candle |
| `update_params` | ATR cambiato, win rate in calo | Aggiorna SL%/TP%/size senza fermare |
| `update_threshold` | Score troppo spesso sotto soglia, mercato neutro | Modifica `signal_strength_threshold` in DB |
| `pause_trading` | Mercato caotico, troppe perdite consecutive | Blocca ExeLoop |
| `resume_trading` | Dopo pausa, condizioni migliorate | Riavvia ExeLoop |
| `no_action` | Tutto ok o dati insufficienti | Solo log |

---

### 5.3 Regole di Non-Azione (hardcoded, precedono l'AI)

Il supervisor NON chiama l'AI (o ignora la risposta) se:
- Meno di 5 trade totali AND nessun volume anomaly
- Stessa action già presa 3+ volte nelle ultime 10 decisioni
- `win_rate > 60%` AND `total_pnl > 0` (sistema funziona, non toccare)
- Coverage collector < 50% (dati insufficienti per decidere)
- Score in range `[-5, +5]` (troppo neutro per agire)

---

### 5.4 Regime → Strategia Mapping

| Regime | Strategie Consentite |
|--------|---------------------|
| `ranging` | `rsi_bollinger`, `momentum_base`, `stoch_rsi_bb_squeeze` |
| `trending_up` | `ema_cross` |
| `trending_down` | `ema_cross` |
| `volatile` | `stoch_rsi_bb_squeeze`, `momentum_base` |
| `unknown` | `momentum_base` |

---

### 5.5 Cooldown e Protezioni

| Tipo | Durata | Scopo |
|------|--------|-------|
| Strategy change | `SCALPING_STRATEGY_COOLDOWN_SEC` | Evita cambi strategia troppo frequenti |
| Param update | `SCALPING_PARAM_UPDATE_COOLDOWN_SEC` | Evita oscillazioni parametri |
| Threshold update | 30 minuti (1800s) | Evita modifiche soglia continue |
| Daily AI calls | Max 100/giorno | Limita costi API |

**Bounded threshold:** min 5.0, max 30.0.

---

### 5.6 Loop di Feedback e Outcome Verification

```
Supervisor tick (ogni 10 min)
    │
    ├─> Decisione applicata? → was_applied = True
    │       └─> +25-35 minuti dopo:
    │               verify_supervisor_outcomes_job()
    │               ├─> Calcola PnL delta dalla sessione
    │               ├─> positive  se PnL delta > +0.01
    │               ├─> negative  se PnL delta < -0.01
    │               └─> neutral   altrimenti
    │
    └─> Decisione bloccata (cooldown)? → was_applied = False, blocked_reason = "..."
```

*Dai log:* Il supervisor ha verificato 5 outcomes nella sessione odierna, tutti classificati `negative` o `neutral` — coerente con un mercato in consolidamento dove nessuna azione avrebbe migliorato il PnL.

---

### 5.7 Threshold Dinamico — Meccanismo

Il supervisor può abbassare o alzare la soglia con logica adattiva:

**Abbassa la soglia (più permissivo):**
- Volume anomaly rilevato → abbassa a 5.0–6.0
- Score borderline ma segnale tecnico forte + coverage > 70% → abbassa a ~10.0

**Alza la soglia (più conservativo):**
- Trade in perdita consecutivi → alza di 2-3 punti

*Log osservato alle 11:38:30:*
```
Supervisor: update_threshold → 5.0
ParameterUpdater: Threshold saved to DB: 5.0
ScalpingConfigLoader: reload richiesto → 16 override DB caricati
new threshold active: 5.0
```
Il supervisor ha abbassato la soglia da ~10.5 a 5.0 dopo ~2 ore di mercato neutro con blocchi continui. Tuttavia i trade SELL successivi sono stati bloccati per mancanza di supporto SHORT — non per soglia.

---

## 6. Analisi della Sessione Live (23 Giugno 2026, BNBUSDC)

### Timeline Riepilogativa

| Orario | Evento |
|--------|--------|
| 09:46 | App avviata in LIVENET mode |
| 09:46 | Sessione `37ff3388` ripristinata da DB (BUY aperta @ 580.82, qty=0.034) |
| 09:46–10:13 | Posizione aperta, signal score neutro (-9.7/-9.8), nessun nuovo ingresso possibile |
| 10:14:11 | OCO EXPIRED (ordine SL) → OCO FILLED (TP @ 579.0) → `stop_loss`, PnL=-0.10 (-0.51%) |
| 10:15–10:22 | Regime cambia in `trending_down`, strategia → `ema_cross`, SELL signals approvati |
| 10:15–10:35 | **~15 segnali SELL consecutivi approvati** ma bloccati da `BLOCKING SHORT ENTRY` |
| 10:38–11:37 | Score torna neutro, soglia 10.5, blocchi per "intelligence neutrale" |
| 11:38:30 | Supervisor abbassa threshold a 5.0 |
| 11:39–12:10 | Score rimane ~-3.3 (neutro), blocchi continuano nonostante soglia 5.0 |

### Osservazioni Chiave dai Log

**1. Il sistema funziona come progettato:**
- La posizione aperta era protetta da OCO server-side su Binance — quando il prezzo ha toccato lo SL (579.0), l'ordine è stato eseguito automaticamente anche durante un breve drop di connettività.
- I blocchi `intelligence neutrale` con score ~-3.3 sono corretti: il mercato era in consolidamento laterale stretto.

**2. Il segnale SHORT è sistematicamente perso:**
- Dalle 10:15 alle 10:35, BNB era in chiaro `trending_down` con segnali SELL allineati (intelligence bearish, tecnico EMA cross SELL). Il sistema approvava i segnali ma li bloccava con `BLOCKING SHORT ENTRY: side=SELL is not supported`.
- **Opportunità mancata stimata:** ~7 segnali SELL validi in un trend ribassista da 580 a 572 (~1.4% di movimento).

**3. Discrepanza signal_score / intel_score:**
- Il SignalScoreEngine riporta score live ~-3.3 (neutro)
- Lo snapshot DB riporta costantemente `score=-12.9, bias=bearish`
- Questa discrepanza è da investigare: i due valori usano finestre temporali o pesi diversi?

**4. APScheduler job missed ripetuti:**
- Heartbeat, monitor_pnl, session_health, intelligence_snapshot vengono saltati periodicamente (1-6 secondi di ritardo).
- Causati dall'evento AI del supervisor (chiamata HTTP sincrona che blocca il thread principale APScheduler).
- **Raccomandazione:** Isolare le chiamate AI in un ThreadPoolExecutor separato.

**5. Supervisor: 6 `no_action`, 1 `update_threshold`:**
- Tutti i `no_action` sono corretti data la situazione (mercato neutro, posizione già aperta, poi nessuna posizione ma score basso).
- Il `update_threshold` a 5.0 è una risposta appropriata ma inefficace in questo contesto specifico (il blocco era `SHORT not supported`, non la soglia).

---

## 7. Flusso Dati Architetturale Completo

```
Binance WS Streams
    ├── bnbusdc@kline_1m  ──→  CandleBuffer (100 candele)
    │                              └─> ExecutionLoop._process_candle()
    │                                      ├─> RegimeDetector
    │                                      ├─> StrategySelector
    │                                      └─> SignalAggregator
    │
    ├── bnbusdc@trade     ──→  CVDCalculator (accumulatore real-time)
    │                              └─> SignalScoreEngine.cvd component
    │
    └── UserDataStream    ──→  OCO event handler
                                   └─> _update_closed_position_in_db()

External APIs (periodic)
    ├── Binance Futures   ──→  FundingRateCollector / OpenInterestCollector
    ├── Alternative.me    ──→  FearGreedCollector
    ├── CryptoCompare     ──→  SentimentCollector (intermittente, errori getaddrinfo)
    └── Whale Alert       ──→  WhaleCollector

SignalScoreEngine
    └─> Combina tutti i collector → score [-100, +100]
            └─> _score_history (deque 60) → trend_5m, velocity, trend_direction

SupervisorScheduler (ogni 10 min)
    ├─> build_scalping_context()    ← assembla tutto
    ├─> AI call (cascade modelli)   ← poolside/laguna-m.1:free (primary)
    ├─> ParameterUpdater.apply()
    └─> INSERT supervisor_memory

verify_supervisor_outcomes_job (ogni ~3 min)
    └─> UPDATE supervisor_memory.outcome_label per decisioni 25-35 min fa

intelligence_snapshot_job (ogni 60 sec)
    └─> INSERT market_intel_snapshots

Supabase PostgreSQL
    ├── scalping_sessions
    ├── scalping_trades
    ├── supervisor_memory
    ├── market_intel_snapshots
    ├── scalping_runtime_config
    └── opportunities
```

---

## 8. Recovery su Restart

Sequenza di ripristino implementata nel lifespan di `main.py`:

1. Query `scalping_sessions WHERE status = 'running'`
2. Verifica coerenza mode (session_mode == global_mode) — se diversi, marca come `stopped`
3. Ripristina `_execution_state` da DB (session_id, symbol, mode, trade_value)
4. `exchange_phase`: connessione Binance, fetch saldo
5. `position_phase`: carica posizione aperta da DB se presente
6. `buffer_phase`: carica 100 candele storiche da Binance REST
7. `pipeline_phase`: avvia ExecutionLoop, WS streams, UserDataStream, SupervisorScheduler

**SessionLoadGuard** traccia le fasi e emette warning se il loading supera 5 secondi.  
*Log osservato:* session READY after 14.2s — normale per restore con posizione aperta.

---

## 9. Issues Noti e Raccomandazioni

| Issue | Priorità | Raccomandazione |
|-------|----------|-----------------|
| SHORT not supported — ~15 segnali SELL persi | 🔴 Alta | Implementare WalletOrchestrator + margin borrow (già pianificato) |
| APScheduler job missed da AI call bloccante | 🟡 Media | Isolare chiamate AI in ThreadPoolExecutor |
| Discrepanza score live vs DB snapshot | 🟡 Media | Verificare pesi/finestre temporali nei due calcoli |
| CryptoCompare intermittente (getaddrinfo failed) | 🟡 Media | Aggiungere retry con backoff, fallback a cache locale |
| Supervisor abbassa threshold ma il blocco è sul tipo di ordine | 🟢 Bassa | Il supervisor non ha visibilità sul blocco SHORT — aggiungere questo context nel prompt |
| heartbeat/monitor missed ogni ~30 sec | 🟢 Bassa | Atteso su Windows con carico AI; tollerabile in produzione VPS |

---

## 10. Metriche di Performance Esposte

Endpoint `GET /scalping/performance`:

| Metrica | Descrizione |
|---------|-------------|
| `total_pnl` | PnL assoluto sessione |
| `total_pnl_pct` | PnL percentuale |
| `win_rate` | % trade vincenti |
| `profit_factor` | Gross profit / Gross loss |
| `max_drawdown` | Max drawdown dalla equity curve |
| `consecutive_losses` | Perdite consecutive correnti |
| `hold_pnl_pct` | Performance HODL equivalente nello stesso periodo |
| `trading_beats_hold` | Boolean: il trading supera la strategia buy & hold? |

---

*Documento generato da analisi multi-agente + log sessione live 23/06/2026*  
*Prossima revisione raccomandata: dopo implementazione SHORT selling (WalletOrchestrator)*
