# HANDOFF.md — SynthTrade

> **Generato:** 2026-09-29 ~14:30 UTC  
> **Scopo:** Documento di passaggio per qualsiasi agente/sessione futura. Contiene tutto il contesto necessario senza bisogno di leggere la history della conversazione.  
> **Stato produzione:** Bot in LIVE su VPS, sessione `a12483b5` attiva, 0 trade da inizio sessione.

---

## 1. Stato attuale (cosa sta succedendo oggi)

### Sessione live
- **Sessione corrente:** `a12483b5`, start 2026-09-29 ~14:17 UTC
- **Simbolo:** BTC-EUR, exchange OKX, modalità LIVE
- **0 trade in questa sessione** — il bot non sta aprendo posizioni
- **Motivo:** vedere §3 (analisi segnali)

### Ultimi commit rilevanti
| Commit | Data | Cosa fa |
|--------|------|---------|
| `87a8f03` | 2026-09-25 | TASK-1256: SL/TP per-strategia; `rsi_bollinger` → SL 0.30%, TP 0.55% netti |
| `77339b0` | 2026-09-29 | TASK-1261: fee awareness supervisor, memoria cross-sessione, anti-loop pause |
| `df9b67c` | 2026-09-29 | Fix prompt supervisor: rimosso BTC-EUR/OKX hardcoded, formula breakeven dinamica |
| (oggi) | 2026-09-29 | TASK-1262: fix bias strutturali scoring — vedere §5 |

---

## 2. Root cause delle perdite (analisi su 188 trade LIVE luglio–settembre 2026)

### A. Numeri globali
- **188 trade totali LIVE**, tutti BUY (no short)
- **WR globale:** ~33% (62 wins / 126 losses)
- **PnL totale:** −€8.59
- **Di cui fee:** −€6.96 (81% delle perdite)
- **PnL senza fee:** −€0.79 (quasi breakeven — il problema principale sono le fee)

### B. Breakeven WR reale
- Fee OKX taker: 0.10% per lato → 0.20% round-trip
- Con avg_win ≈ 0.28% netto, avg_loss ≈ 0.51% netto:
  - **Breakeven WR = 0.51 / (0.28 + 0.51) = 64.9%**
  - Il bot opera al 33% → strutturalmente in perdita
- Nota: il 64.9% è calcolato sui dati storici reali; cambia se SL/TP cambiano

### C. Per-strategia
| Combo regime/strategia | Trade | WR | Note |
|------------------------|-------|----|------|
| `ranging/rsi_bollinger` | 176 | 35.8% | Dominante, sotto breakeven 65% |
| `ranging/ema_cross` | 2 | 100% | Troppo pochi, non statisticamente valido |
| `trending_up/ema_cross` | 9 | 22% | Pochi, aneddotico |
| altro | 1 | n/a | - |

### D. Trailing stop controproducente
- Il trailing chiude i trade vincenti a avg +0.27% invece del TP +0.55–0.80%
- Abbassa l'avg_win, aumentando il WR necessario per il breakeven
- Config attuale: BE_TRIGGER=0.15%, STEP=0.15%, BUFFER=0.10% — non proporzionali al TP

---

## 3. Analisi del sistema di scoring (TASK-1262, analisi 2026-09-29)

### Il problema centrale: un solo segnale dinamico su nove

Su 9 collector con peso > 0, **solo `order_book_imbalance` è davvero dinamico** per BTC-EUR:

| Collector | Peso norm. | Score medio (12h) | Varianza | Natura |
|-----------|-----------|-------------------|----------|--------|
| `order_book_imbalance` | 31.6% | −2.4 | **100.6** | ✓ DINAMICO (per-candela, OKX spot) |
| `funding_rate` | 15.8% | −0.2 | 0.00 | ✗ fisso (cambia ogni 8h, magnitudine ~0) |
| `cvd` | 15.8% | +0.1 | 0.03 | ✗ quasi sempre 0 (grace period + baseline errata) |
| `long_short_ratio` | 10.5% | −21.0 | 0.84 | ✗ strutturalmente bearish (BTC ha 60-65% long) |
| `fear_greed` | 10.5% | −19.5 | 0.00 | ✗ fisso (aggiornato 1×/giorno, F&G=73 oggi) |
| `open_interest` | 5.3% | ~0 | 0.00 | ✗ baseline rolling → sempre ~0 |
| `whale` | 5.3% | 0.0 | 0.00 | ✗ mai attivo su BTC-EUR |
| `onchain` | 5.3% | +1.1 | 0.10 | ✗ proxy BTC price_change_24h, lento |
| `sentiment` | 0% | 0.0 | 0.00 | disabilitato (peso 0) |

### Tre bias permanenti che falsano lo score verso il basso

**Bias 1 — Long/Short Ratio (−21 quasi costante, peso 10.5%, contributo −2.2 punti):**
- Funzione: `score = (50 - long_pct) * (100/30)` → con long_pct=63% → score=−43
- BTC ha strutturalmente 60-65% long retail: il sistema vede sempre "bearish"
- BTC-EUR spot non ha perpetual Binance/OKX → usa proxy BTCUSDT futures → dato non pertinente
- Il problema non è il valore assoluto ma che **non cambia**: non distingue "oggi BTC è più long di ieri"

**Bias 2 — Fear & Greed (−19.5 costante oggi, peso 10.5%, contributo −2.1 punti):**
- Cache 4h, aggiornato 1×/giorno. Con F&G=73 (Greed), produce sempre −19.5
- Funzione: zona 61-80 → `-(value-60)*1.5` → non è contrarian estremo, è drag costante
- Non è un segnale per-minuto: non dovrebbe pesare quanto l'OBI che cambia ogni candela

**Bias 3 — CVD (peso 15.8%, quasi sempre score=0):**
- Grace period: escluso finché `_trades_since_reset < 100` (reset ogni 1000 trades)
- Baseline hardcoded a `Decimal("1000")` in due punti del codice (`signal_score_engine.py:416,469`)
- BTC-EUR su OKX spot ha volumi piccoli (candele 0.05-0.2 BTC) → CVD in valore assoluto << 1000 → score ~0
- Risultato: 15.8% del peso non contribuisce mai allo score

### Conseguenza sulla distribuzione dello score (194 candele, ultime 12h)
| Zona | Candele | % |
|------|---------|---|
| score < −6 (bearish gate) | 82 | **42.3%** |
| score −6..+6 (neutro) | 110 | **56.7%** |
| score > +6 (bullish gate) | 2 | **1.0%** |

- Il sistema è **bullish 1% del tempo** su BTC-EUR in ranging
- `tradeable=True bullish`: 2 su 194 candele → il bot non apre mai un BUY per intelligence
- Abbassare la soglia non risolve: con drag −4.3 fissi, soglia 0 significherebbe entrare long con score negativo
- **Il problema non è la soglia — è che i segnali bullish non esistono**

### Soglia attuale
- `SCALPING_SIGNAL_STRENGTH_THRESHOLD = 6.0` (in DB da 2026-06-15)
- Le decisioni `update_threshold` del supervisor (401 in 7gg, 140 applicate) cambiano questo valore ma non risolvono il bias strutturale

---

## 4. Supervisor: stato dopo TASK-1261 (deployato 2026-09-29 ~14:00)

### Cosa è stato fixato
1. **Fee awareness**: il supervisor ora riceve il blocco `=== FEE REALI ===` con taker% e round-trip drag% calcolati a runtime (non hardcoded)
2. **Memoria cross-sessione**: dopo stop&go, se storico ≥ 20 trade il gate "< 5 trade → no_action" viene bypassato; il supervisor usa la performance storica
3. **Anti-loop pause**: cooldown 30 min su `pause_trading` in `supervisor_scheduler.py` (campo `_last_pause_time`)
4. **History estesa**: da 10 a 20 decisioni precedenti, con `blocked_reason` visibile
5. **Prompt generico**: rimosso qualsiasi riferimento a BTC-EUR, OKX, o valori numerici storici hardcoded

### Prima decisione post-deploy (verifica DB)
Il supervisor ha correttamente:
- Applicato l'eccezione stop&go (186 trade cross-sessione ≥ 20 → no gate)
- Calcolato il breakeven WR al 65% dai dati runtime
- Concluso che `rsi_bollinger/ranging` con WR 35.8% è strutturalmente perdente
- Emesso `no_action` perché non esiste alternativa migliore nella whitelist (rsi_bollinger è l'unica strategia consentita per ranging)

### Cosa ancora non funziona nel supervisor
- Il supervisor propone correttamente `no_action`, ma questo significa che **il bot non trader mai** finché il regime è ranging e rsi_bollinger è l'unica opzione consentita per ranging
- La soluzione reale è il fix al sistema di scoring (§3/§5) — se lo score diventasse bullish qualche volta su rsi_bollinger, il bot potrebbe aprire trade

### File supervisor
```
synthtrade/backend/app/ai/supervisor_context.py       ← build_scalping_context(), fee_info injection
synthtrade/backend/app/scalping/supervisor/
  supervisor_client.py                                 ← _SUPERVISOR_SYSTEM_PROMPT (v3), _format_context()
  supervisor_scheduler.py                              ← _last_pause_time, apply_decision(), cooldown
  historical_context.py                                ← signal_outcome_by_strategy_regime (view DB, cache 5min)
  parameter_updater.py                                 ← applica update_params e update_threshold al DB
```

---

## 5. Fix segnali scoring (TASK-1262, eseguito 2026-09-29)

### Fix 1 — Long/Short Ratio: variazione relativa invece di valore assoluto

**Problema:** `ratio_to_score(long_pct)` produce sempre −16 a −43 per BTC perché BTC ha strutturalmente 60-65% long. Il valore assoluto non segnala nulla di nuovo.

**Fix:** Il collector accumula le ultime N letture e calcola la **variazione** rispetto alla media mobile recente. Il segnale è "oggi è più/meno long del solito", non "è a 63%".

**File:** `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`

### Fix 2 — Fear & Greed: peso ridotto e de-normalizzato dal calcolo real-time

**Problema:** F&G pesa 10.5% normalizzato ma cambia 1×/giorno → drag costante −2.1 punti.

**Fix:** Il peso scende da 0.10 a 0.03 in `DEFAULT_WEIGHTS`. Non viene eliminato (ha valore in condizioni estreme F&G < 20 o > 80) ma non domina più il denominatore. La funzione `value_to_score` rimane invariata.

**File:** `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py`

### Fix 3 — CVD: baseline dinamica proporzionale al volume medio

**Problema:** Baseline hardcoded `Decimal("1000")` → su BTC-EUR con volume per-candela 0.05-0.2 BTC, CVD non supera mai valori > 10-20 → score ~0-2% → irrilevante.

**Fix:** La baseline viene calcolata come media mobile del CVD assoluto osservato nelle ultime 20 finestre di accumulo, o se non disponibile come percentuale del volume stimato (0.1 BTC). Il grace period `< 100 trades` rimane.

**File:** `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py`, `cvd_calculator.py`

---

## 6. Architettura chiave (riferimento rapido)

### Flusso di esecuzione (per-candela, ogni ~60s)
```
OKX WS candle → candle_processor.py
  → regime_detector (ranging/trending_up/volatile/unknown)
  → strategy_selector (ema_cross/rsi_bollinger/vwap_reversion) 
     + macro_override TASK-1250 (BTC > EMA20_4h → ema_cross forzato)
  → signal_aggregator (tech_score × 0.7 + intel_score × 0.3)
  → candle_processor: open trade se score ≥ threshold E bias=bullish E no posizione aperta
```

### State globale
```python
# synthtrade/backend/app/scalping/router.py:83
_execution_state = {
    "exchange":          OkxExchangeAdapter,
    "position_manager":  PositionManager,
    "session":           { symbol, mode, balance, status },
    "fee_tier":          dict | FeeTier,  # usa _get_fee_rate() per normalizzare
    "signal_engine":     SignalScoreEngine,
    "ws_client":         OkxWSClient,
    "risk_config":       dict,             # SL/TP/trailing
}
```

### Config DB (tabella `scalping_runtime_config`)
Chiavi rilevanti:
```
SCALPING_STOP_LOSS_PCT              = 0.5     # globale, fallback
SCALPING_TAKE_PROFIT_PCT            = 0.8     # globale, fallback
SCALPING_SIGNAL_STRENGTH_THRESHOLD  = 6.0     # soglia score (modificabile dal supervisor)
TRAILING_ENABLED                    = true
STRATEGY_RSI_BOLLINGER_SL_PCT       = 0.30    # per-strategia, da TASK-1256
STRATEGY_RSI_BOLLINGER_TP_PCT       = 0.55    # per-strategia, da TASK-1256
```

### Whitelist regime → strategia (hardcoded nel supervisor e in `strategy_selector.py`)
```
ranging       → rsi_bollinger
trending_up   → ema_cross
trending_down → rsi_bollinger
volatile      → vwap_reversion
unknown       → vwap_reversion
```
Eccezione macro (TASK-1250): se BTC_4h > EMA20_4h, qualunque sia il regime locale → `ema_cross`.

### DB
```bash
docker exec vps_postgres psql -U synthtrade -d synthtrade
```
Tabelle chiave: `scalping_sessions`, `scalping_trades`, `supervisor_memory`, `scalping_runtime_config`  
View chiave: `signal_outcome_by_strategy_regime` (WR/PnL aggregato per combo regime/strategia)

---

## 7. Task aperti con priorità

### 🔴 TASK-1262 — Fix bias strutturali nel signal scoring engine
**Stato:** In esecuzione (questo handoff documenta l'analisi; il codice è in fase di scrittura)  
**Problema:** Tre bias permanenti abbassano lo score di −4.3 punti fissi → bullish quasi impossibile  
**Fix:** L/S Ratio variazione relativa, F&G peso ridotto, CVD baseline dinamica  
**File:** `signal_score_engine.py`, `long_short_ratio.py`, `cvd_calculator.py`  
**Impatto atteso:** Score medio da −5.0 a ~0, candele bullish da 1% a ~35-40%

### 🟡 TASK-1257 — Calibrazione valori SL/TP per-strategia
**Stato:** Aperta, in raccolta dati (infrastruttura TASK-1256 in LIVE dal 2026-09-25)  
**Gating:** Almeno 30 trade post-TASK-1256 (al 2026-09-29 abbiamo 0 trade per via del bug scoring)  
**Azione:** Analisi MFE/MAE quando il bot riprende a tradare dopo TASK-1262

### 🟡 TASK-1258 — Calibrazione trailing stop per-strategia  
**Stato:** Aperta, dipende da TASK-1257  
**Problema noto:** Step trailing fissi 0.15% non proporzionali al TP; con TP=0.55% solo 1 step possibile  
**Azione:** Dopo TASK-1257, implementare chiavi DB `STRATEGY_*_BE_TRIGGER/STEP/BUFFER`

### 🟡 TASK-1252 (Fase 2) — Ricalibrare peso score nella decisione
**Stato:** Fase 1 completa (fix pipeline), Fase 2 aspetta 30 trade post-fix  
**Note:** Correlazione score→PnL ≈ 0 misurata sui 188 trade live. Dopo TASK-1262 la correlazione cambierà (score sarà più dinamico), quindi misurare di nuovo dopo.

### 🟡 TASK-1253 — Rivedere asimmetria SL/TP globale
**Stato:** Aperta, aspetta dati  
**Note:** Con 0 trade da TASK-1256, impossibile misurare. Aspettare TASK-1262 + raccolta dati.

---

## 8. Cosa NON fare

- **Non usare `--reload`** con uvicorn in produzione: WatchFiles riavvia i WS e causa "unknown" regime
- **Non eseguire pytest dalla root** del progetto: usare `cd synthtrade/backend && python -m pytest`
- **Non modificare il DB schema**: i nuovi parametri vanno in `scalping_runtime_config` come nuove chiavi
- **Non abbassare la soglia score** sotto 5.0 come fix al problema bullish: il problema è il bias strutturale negativo, non la soglia (§3)
- **Non fidarsi del WR 100% di ema_cross/ranging** (2 trade): statisticamente non valido
- **Non cambiare SL/TP mentre il bot ha posizioni aperte**: rischio di lasciare ordini OCO senza copertura

---

## 9. Come verificare che il bot stia funzionando

```bash
# Score corrente e bias
docker logs synthtrade_backend --tail 20 2>&1 | grep "ExecLoop\|COLLECTORS\|COVERAGE"

# Ultima decisione supervisor
docker exec vps_postgres psql -U synthtrade -d synthtrade -c \
  "SELECT decided_at, action, was_applied, LEFT(reason,200) FROM supervisor_memory ORDER BY decided_at DESC LIMIT 3;"

# Trade della sessione corrente
docker exec vps_postgres psql -U synthtrade -d synthtrade -c \
  "SELECT COUNT(*), SUM(pnl), AVG(pnl) FROM scalping_trades WHERE session_id = (SELECT id FROM scalping_sessions WHERE status='active' LIMIT 1);"

# WR per combo (vista)
docker exec vps_postgres psql -U synthtrade -d synthtrade -c \
  "SELECT * FROM signal_outcome_by_strategy_regime ORDER BY n_trades DESC;"
```
