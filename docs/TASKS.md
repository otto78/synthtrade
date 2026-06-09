# TASKS.md — SynthTrade Task Tracking

## Active Tasks

### TASK-814 — Live Mode Bug Fixes (2026-06-05 → 2026-06-09)

Fix issues identified from live session logs:
- [x] **Issue 1**: WS initial handshake timeout — warmup blocks event loop
- [x] **Issue 2**: Binance RSS Poller — empty/non-XML response
- [x] **Issue 3**: CoinGecko News Poller — 401 Unauthorized (news endpoint needs API key)
- [x] **Issue 4**: News RSS Feed URLs — CoinDesk redirect (add www), TheBlock 404
- [x] **Issue 5**: No trades executing in live mode — *fixed: OCO balance settlement, logging visibility, session restore pipeline*
- [x] **Issue 6**: Session restore non avviava il pipeline WS — *fix: `_restore_scalping_session()` ora chiama `_start_ws_broadcast()` con `restore_mode=True`*
- [x] **Issue 7**: Log moduli scalping invisibili su Windows — *fix: handler forzato nei logger scalping in logging.py*
- [x] **Issue 8**: OCO placement falliva per balance post-fee — *fix: `place_oco_order()` ora legge balance reale prima di piazzare*
- [x] Update docs and commit

---

### TASK-815 — SignalScoreEngine: soglia dinamica e pesi calibrati (2026-06-09)

**Priorità:** Alta (sblocca tradeable=True)

**Problema:** Con 7 collector configurati ma soli 3-4 che rispondono (funding_rate, OI, long/short, fear_greed falliscono su simboli USDC), la soglia fissa 15.0 blocca `tradeable=True` anche con score 12-14 validi.

**Soluzione:** Applicare soglia scalata in base alla coverage dei collector che hanno effettivamente risposto:
- `effective_threshold = threshold * total_weight`
- Con coverage 0.5 (3 collector su 7): soglia ≈ 7.5 invece di 15.0
- Con coverage 0.3 (2 collector): soglia ≈ 4.5

**Modifiche:**
- `signal_score_engine.py`:
  - Ridistribuire pesi: funding_rate 0.20, cvd 0.20, open_interest 0.15, long_short_ratio 0.15, fear_greed 0.15, whale 0.10, sentiment 0.05, onchain 0.0
  - Normalizzare simbolo futures: USDC → USDT (Binance Futures non ha perpetual USDC)
  - Soglia scalata: `total >= threshold * coverage` invece di `total >= threshold`

**Rischio:** Basso — la soglia scalata è più permissiva ma riflette la reale affidabilità dei dati.

---

### TASK-816 — RSI Bollinger: soglie calibrate per mercato ranging (2026-06-09)

**Priorità:** Alta (genera segnali in ranging)

**Problema:** In mercato ranging a bassa volatilità (es. BNBUSDC), le soglie standard RSI 30/70 non vengono quasi mai toccate. La strategia rsi_bolligner produce solo segnali NONE.

**Soluzione:** Abbassare le soglie per catturare mean-reversion anche su range stretti:
- RSI_OVERSOLD: 30 → 38
- RSI_OVERBOUGHT: 70 → 62
- BB tolleranza: 1.01 → 1.015
- Confidence: 0.7 → 0.6 (leggermente ridotta per evitare falsi)

**Modifiche:**
- `rsi_bollinger.py`: Soglie e tolleranza

**Rischio:** Basso — confidence ridotta compensa il maggior numero di segnali.

---

### TASK-817 — SignalAggregator: bypass mean-reversion per ranging (2026-06-09)

**Priorità:** Media (sblocca SELL legittimi)

**Problema:** Il SignalAggregator blocca i segnali SELL se il bias intelligence è bullish, anche quando la strategia attiva è rsi_bollinger (mean-reversion in ranging). In ranging, i SELL non sono short direzionali ma **chiusura di range** — il prezzo tocca la banda superiore di Bollinger e la strategia suggerisce di vendere perché è probabile un ritorno verso la media.

**Soluzione:** Aggiungere bypass per strategie mean-reversion:
```
MEAN_REVERSION_STRATEGIES = ("rsi_bollinger", "stoch_rsi_bb_squeeze")
if bias == "bullish" and technical.type == "SELL" and technical.source in MEAN_REVERSION_STRATEGIES:
    # Permetti: non è short direzionale, è chiusura range
```

**Modifiche:**
- `signal_aggregator.py`: Bypass conflitto bias/segnale per strategie mean-reversion

**Rischio:** Medio — potrebbe lasciar passare qualche falso SELL, ma la confidence ridotta (0.6) e la combined confidence check limitano il rischio.

---

### TASK-818 — StrategySelector: mapping regimi corretto (2026-06-09)

**Priorità:** Media

**Problema:** Il mapping regimi attuale assegna `momentum_base` a TUTTI i regimi (ranging, volatile, unknown). Momentum_base produce segnali frequenti ma non è ottimale per nessun regime specifico.

**Soluzione:** Mappare i regimi alle strategie più adatte:
- `ranging` → `rsi_bollinger` (mean-reversion)
- `volatile` → `stoch_rsi_bb_squeeze` (cattura breakout)
- `trending_up/trending_down` → `ema_cross` (trend following)
- `unknown` → `momentum_base` (default sicuro)

**Modifiche:**
- `strategy_selector.py`: Mappa regimi aggiornata

**Rischio:** Basso — le strategie sono testate singolarmente.

---

### TASK-819 — Supervisor: cooldown e regime validation (2026-06-09)

**Priorità:** Media (stabilizza il sistema)

**Problema:** Il supervisor AI cambia strategia ogni 1-2 minuti (rsi_bollinger ↔ ema_cross ↔ rsi_bollinger), causando instabilità. Inoltre può proporre strategie sbagliate per il regime corrente (es. ema_cross in ranging).

**Soluzione:**
- Cooldown cambio strategia: 20 minuti
- Cooldown aggiornamento parametri: 10 minuti
- Regime validation: blocca strategie non compatibili col regime corrente
- Se la strategia proposta non è ammessa, resetta il cooldown per permettere il prossimo tick valido

**Regime→Strategie permesse:**
| Regime | Strategie |
|--------|-----------|
| ranging | rsi_bollinger, momentum_base, stoch_rsi_bb_squeeze |
| volatile | stoch_rsi_bb_squeeze, momentum_base |
| trending_up/down | ema_cross |
| unknown | momentum_base |

**Modifiche:**
- `supervisor_scheduler.py`: Cooldown + regime validation
- `supervisor_client.py`: Regole mapping nel prompt AI

**Rischio:** Basso — le validazioni sono barriere di sicurezza.

---

### TASK-820 — EMA Cross: rimuovere slope filter + registrazione nuove strategie (2026-06-09)

**Priorità:** Alta (ripristina segnali EMA)

**Problema 1 — Slope filter:** Il filtro pendenza EMA21 (MIN_SLOPE = 0.03%) blocca TUTTI i segnali in ranging perché le EMA sono piatte. Questo ha bloccato i segnali per ore durante i test. È un anti-pattern: se il mercato è in ranging, ema_cross non dovrebbe essere selezionata (task TASK-818), ma se viene selezionata per errore deve almeno produrre segnali.

**Soluzione:** Rimuovere completamente MIN_SLOPE e la logica di pendenza da ema_cross.py. Ripristinare il comportamento originale: segnale BUY se EMA9 > EMA21, SELL se EMA9 < EMA21.

**Problema 2 — Nuova strategia:** stoch_rsi_bb_squeeze non è registrata nel registry e il file non esiste.

**Soluzione:** Creare il file `stoch_rsi_bb_squeeze.py` con la strategia StochRSI + BB Squeeze per regime volatile. Registrarla in `registry.py`.

**Modifiche:**
- `ema_cross.py`: Rimuovere slope filter (ripristinare versione semplice)
- `stoch_rsi_bb_squeeze.py`: Creare nuova strategia (dallo stash)
- `registry.py`: Registrare stoch_rsi_bb_squeeze

**Rischio:** Basso — lo slope filter era un anti-pattern dimostrato. La nuova strategia è opzionale.

---

### TASK-821 — Frontend: default BNBUSDC e rimozione initial load (2026-06-09)

**Priorità:** Bassa

**Problema:** Il frontend usa BTCUSDT come simbolo predefinito, ma l'utente fa trading principalmente su BNBUSDC. Inoltre la Trade Log e Performance Panel facevano chiamate API al caricamento, causando errori 404 quando non c'era una sessione attiva.

**Soluzione:**
- Cambiare default symbol da BTCUSDT a BNBUSDC in tutti i componenti scalping
- Cambiare strategia default da scalping_v2 a momentum_base
- Rimuovere initial load da TradeLog e PerformancePanel (attendono sessione attiva)

**Modifiche:**
- `live-chart.component.ts`: default BNBUSDC
- `market-intel-panel.component.ts`: default BNBUSDC
- `session-controls.component.ts`: default BNBUSDC, strategia momentum_base
- `session-api.service.ts`: default BNBUSDC
- `trade-log.component.ts`: rimuovere initial load
- `performance-panel.component.ts`: rimuovere initial load

**Rischio:** Zero — solo valori di default.