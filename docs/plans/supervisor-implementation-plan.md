# SynthTrade — Piano di Implementazione
**Versione:** 3.1 — Fix Critici + Configurazione + Supervisor Intelligence  
**Data:** Giugno 2026  
**Destinatario:** Flash (implementazione) / Claude (review architettura)

---

## Indice

1. [Panoramica e Priorità](#1-panoramica-e-priorità)
2. [FASE A — Fix Bloccanti](#2-fase-a--fix-bloccanti)
3. [FASE B — Configurazione Centralizzata](#3-fase-b--configurazione-centralizzata)
4. [FASE C — Dati Intelligence Affidabili](#4-fase-c--dati-intelligence-affidabili)
5. [FASE D — Ricalibrazione Score Engine](#5-fase-d--ricalibrazione-score-engine)
6. [FASE E — Supervisor Potenziato](#6-fase-e--supervisor-potenziato)
7. [FASE F — Memoria del Supervisor](#7-fase-f--memoria-del-supervisor)
8. [Sequenza di Deploy](#8-sequenza-di-deploy)
9. [Test di Validazione](#9-test-di-validazione)

---

## 1. Panoramica e Priorità

### Stato attuale — problemi identificati

| # | Problema | Impatto | Fase |
|---|----------|---------|------|
| P1 | `force_execute=True` hardcoded nel router | **CRITICO** — bypassa tutto il sistema | A |
| P2 | Supervisor interval a 45s hardcoded nel codice | **CRITICO** — spreco API, non configurabile | A |
| P3 | Fear & Greed congelato a 8 (API CryptoCompare rotta) | **ALTO** — dato falso guida tutte le decisioni AI | C |
| P4 | Whale collector sempre None (peso 0.10 fantasma) | **ALTO** — coverage artificialmente ridotta | C |
| P5 | Score sempre < 1.0 con soglia a 15 (irraggiungibile) | **ALTO** — nessun trade passa mai il gate intelligence | D |
| P6 | Valori di config sparsi tra .env, router.py, codice | **MEDIO** — impossibile intervenire senza toccare codice | B |
| P7 | Supervisor non vede storico trade né PnL sessione | **MEDIO** — decisioni senza contesto reale | E |
| P8 | Supervisor propone stessa azione in loop (no memoria) | **MEDIO** — 8 chiamate AI identiche ogni 20 min | F |

### Principio guida
> Ogni valore che può cambiare tra ambienti o nel tempo sta nel `.env`.  
> Ogni valore che l'utente può voler cambiare a runtime sta nel DB (`scalping_runtime_config`).  
> Nessun valore di business è hardcoded nel codice.

---

## 2. FASE A — Fix Bloccanti

> **Prerequisito:** nessuno. Da fare prima di tutto il resto.  
> **Stima:** 1-2 ore  
> **File coinvolti:** `router.py`, `.env`, `supervisor_scheduler.py`

---

### A1 — Rimuovere `force_execute`

**Problema:** `execution_loop.force_execute = True` nel router bypassa `SignalAggregator`, `RiskManager` e qualsiasi filtro. In modalità live, qualsiasi candela chiusa genera un BUY.

**Soluzione:** Rimuovere il flag e il codice che lo gestisce. Non serve una modalità "force execute" in produzione — per testare l'esecuzione OCO si usa una sessione paper con segnali tecnici abilitati.

**Modifiche a `router.py`:**

```python
# RIMUOVERE queste righe (cercare nel file):
execution_loop.force_execute = True
# oppure ovunque compaia:
if self.force_execute:
    ...

# RIMUOVERE dalla classe ExecutionLoop:
self.force_execute = False  # o True — rimuovere completamente l'attributo
```

**Modifiche a `signal_aggregator.py`:**

```python
# RIMUOVERE il Caso 0 (FORCE_EXECUTE):
# Cercare e rimuovere il blocco:
# ── Caso 0: FORCE_EXECUTE (solo test) ──
if getattr(self, 'force_execute', False) or force_execute:
    ...
```

**Verifica:** dopo la rimozione, avviare una sessione paper e controllare nei log che appaia:
```
🔴 BLOCK: ... intelligence neutrale
```
oppure
```
🟢 SIGNAL: BUY ...
```
Ma NON:
```
📋 LIVE MODE: ... (intelligence bypassed)   ← questo non deve apparire se ci sono 4+ collector
```

---

### A2 — Supervisor interval da `.env`

**Problema:** `SupervisorScheduler` viene istanziato con `interval_seconds=45` hardcoded nel router (riga ~2079 e ~1599). Il valore in `.env` (`SCALPING_SUPERVISOR_INTERVAL_MIN=10`) viene ignorato.

**Soluzione:** leggere il valore da `settings` in entrambi i punti di istanziazione.

**Modifiche a `.env`:**

```bash
# Supervisor AI — intervallo tra analisi (secondi)
# Valore consigliato produzione: 600 (10 min)
# Valore minimo sensato: 300 (5 min, allineato al cooldown strategy/2)
# NON usare valori < 120 in produzione (spreco API + missed jobs scheduler)
SCALPING_SUPERVISOR_INTERVAL_SEC=600
```

**Modifiche a `config.py`** (nella sezione Scalping settings):

```python
# Supervisor
SCALPING_SUPERVISOR_INTERVAL_SEC: int = 600    # default 10 min
SCALPING_STRATEGY_COOLDOWN_SEC: int = 1200     # default 20 min
SCALPING_PARAM_UPDATE_COOLDOWN_SEC: int = 600  # default 10 min
```

**Modifiche a `router.py`** — cercare le due istanziazioni di `SupervisorScheduler`:

```python
# PRIMA (hardcoded):
supervisor = SupervisorScheduler(symbol=active_symbol, interval_seconds=45)

# DOPO (da settings):
from app.config import settings
supervisor = SupervisorScheduler(
    symbol=active_symbol,
    interval_seconds=settings.SCALPING_SUPERVISOR_INTERVAL_SEC,
)
```

Applicare la stessa modifica in **entrambi** i punti (start normale + restore_mode).

**Modifiche a `supervisor_scheduler.py`** — i cooldown:

```python
# PRIMA (hardcoded):
STRATEGY_CHANGE_COOLDOWN = 1200
PARAM_UPDATE_COOLDOWN = 600

# DOPO (da settings):
from app.config import settings
STRATEGY_CHANGE_COOLDOWN = settings.SCALPING_STRATEGY_COOLDOWN_SEC
PARAM_UPDATE_COOLDOWN = settings.SCALPING_PARAM_UPDATE_COOLDOWN_SEC
```

**Verifica:** riavviare il backend e controllare nei log che il supervisor giri ogni 10 minuti (non ogni 45 secondi). I "missed jobs" dell'APScheduler dovrebbero sparire quasi completamente.

---

## 3. FASE B — Configurazione Centralizzata

> **Prerequisito:** Fase A completata.  
> **Stima:** 3-4 ore  
> **File coinvolti:** `.env`, `config.py`, nuova migration Supabase, nuovo `scalping_config_loader.py`

---

### B1 — `.env` completo e documentato

Sostituire la sezione scalping del `.env` con questa versione completa e commentata:

```bash
# ============================================================
# SCALPING MODULE — Configurazione completa
# Tutti i valori hanno un default ragionevole per produzione.
# I valori contrassegnati con [RUNTIME] possono essere
# sovrascritti dal DB senza restart (via /api/scalping/config).
# ============================================================

# ── EXECUTION ────────────────────────────────────────────────
# Valore del trade singolo in USDC/USDT
SCALPING_TRADE_VALUE=10.0                    # [RUNTIME]

# Perdita giornaliera massima in USD prima dello stop automatico
SCALPING_MAX_DAILY_LOSS=50.0                 # [RUNTIME]

# Drawdown massimo % prima dello stop automatico
SCALPING_MAX_DRAWDOWN_PCT=10.0               # [RUNTIME]

# Stop loss % sul prezzo di entrata
SCALPING_STOP_LOSS_PCT=0.3                   # [RUNTIME]

# Take profit % sul prezzo di entrata
SCALPING_TAKE_PROFIT_PCT=0.5                 # [RUNTIME]

# Flag di sicurezza: True = usa solo paper trading, False = live reale
# DEVE essere False per trading live. Default True per sicurezza.
SCALPING_FORCE_PAPER=true

# Flag di test: bypassa tutti i filtri intelligence e tecnici.
# SEMPRE false in produzione. Usare solo per testare l'esecuzione OCO.
SCALPING_FORCE_EXECUTE=false

# ── SIGNAL INTELLIGENCE ──────────────────────────────────────
# Soglia minima score intelligence per considerare un segnale tradeable
# Range: 0-100. Con la nuova normalizzazione, valori sensati: 15-30.
SCALPING_SIGNAL_STRENGTH_THRESHOLD=15.0      # [RUNTIME]

# Confidenza minima combinata (intelligence + tecnico) per eseguire
# Range: 0.0-1.0
SCALPING_MIN_CONFIDENCE=0.3                  # [RUNTIME]

# Numero minimo di collector che devono rispondere prima di usare intelligence
# Se < questo valore, bypassa intelligence e usa solo segnale tecnico
SCALPING_MIN_COLLECTORS=4

# ── SUPERVISOR AI ────────────────────────────────────────────
# Intervallo tra analisi del supervisor (secondi)
# Produzione: 600 (10 min). Min sensato: 300 (5 min).
SCALPING_SUPERVISOR_INTERVAL_SEC=600

# Cooldown tra cambi di strategia (secondi)
SCALPING_STRATEGY_COOLDOWN_SEC=1200          # 20 min

# Cooldown tra aggiornamenti parametri (secondi)
SCALPING_PARAM_UPDATE_COOLDOWN_SEC=600       # 10 min

# Numero minimo di trade prodotti dalla strategia attuale prima che
# il supervisor possa proporre un cambio strategia
SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE=5

# Numero massimo di decisioni identiche consecutive prima che il
# supervisor venga forzato a considerare alternative
SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS=3

# ── FEAR & GREED ────────────────────────────────────────────
# Sorgente Fear & Greed: "alternative_me" (gratuita) o "cryptocompare"
SCALPING_FEAR_GREED_SOURCE=alternative_me

# ── WHALE ALERT ─────────────────────────────────────────────
# True = abilita il collector whale (richiede WHALE_ALERT_API_KEY)
SCALPING_WHALE_ENABLED=false
WHALE_ALERT_API_KEY=

# ── REGIME DETECTOR ─────────────────────────────────────────
# Soglia % price change per classificare trending (default 3%)
SCALPING_REGIME_TREND_THRESHOLD_PCT=3.0      # [RUNTIME]

# Soglia ATR/close ratio per classificare volatile (default 2%)
SCALPING_REGIME_VOLATILE_THRESHOLD=0.02      # [RUNTIME]
```

---

### B2 — `config.py` aggiornato

Aggiungere/sostituire la sezione scalping in `config.py`:

```python
# ── Scalping — Execution ─────────────────────────────────────
SCALPING_TRADE_VALUE: float = 10.0
SCALPING_MAX_DAILY_LOSS: float = 50.0
SCALPING_MAX_DRAWDOWN_PCT: float = 10.0
SCALPING_STOP_LOSS_PCT: float = 0.3
SCALPING_TAKE_PROFIT_PCT: float = 0.5
SCALPING_FORCE_PAPER: bool = True
SCALPING_FORCE_EXECUTE: bool = False          # SEMPRE False in produzione

# ── Scalping — Signal Intelligence ──────────────────────────
SCALPING_SIGNAL_STRENGTH_THRESHOLD: float = 15.0
SCALPING_MIN_CONFIDENCE: float = 0.3
SCALPING_MIN_COLLECTORS: int = 4

# ── Scalping — Supervisor AI ─────────────────────────────────
SCALPING_SUPERVISOR_INTERVAL_SEC: int = 600
SCALPING_STRATEGY_COOLDOWN_SEC: int = 1200
SCALPING_PARAM_UPDATE_COOLDOWN_SEC: int = 600
SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE: int = 5
SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS: int = 3

# ── Scalping — Collector specifici ──────────────────────────
SCALPING_FEAR_GREED_SOURCE: str = "alternative_me"
SCALPING_WHALE_ENABLED: bool = False
WHALE_ALERT_API_KEY: str = ""

# ── Scalping — Regime Detector ───────────────────────────────
SCALPING_REGIME_TREND_THRESHOLD_PCT: float = 3.0
SCALPING_REGIME_VOLATILE_THRESHOLD: float = 0.02
```

**Nota:** se `config.py` usa un modello Pydantic `BaseSettings` con una classe annidata `scalping`, adattare di conseguenza mantenendo la compatibilità con `settings.scalping.SCALPING_MIN_CONFIDENCE` (pattern già usato nel codice esistente).

---

### B3 — Tabella DB `scalping_runtime_config`

Questa tabella permette di modificare i parametri `[RUNTIME]` senza restart del backend.

**Migration SQL:**

```sql
-- Migration: scalping_runtime_config
-- Permette override runtime dei parametri scalping senza restart backend.
-- I valori qui sovrascrivono quelli di .env per la sessione corrente.

CREATE TABLE scalping_runtime_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    value_type  TEXT NOT NULL CHECK (value_type IN ('float', 'int', 'bool', 'str')),
    description TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Valori di default (specchio del .env — cambiarli qui non richiede restart)
INSERT INTO scalping_runtime_config (key, value, value_type, description) VALUES
('SCALPING_TRADE_VALUE',                  '10.0',  'float', 'Valore singolo trade in USDC'),
('SCALPING_MAX_DAILY_LOSS',               '50.0',  'float', 'Perdita giornaliera massima USD'),
('SCALPING_MAX_DRAWDOWN_PCT',             '10.0',  'float', 'Drawdown massimo %'),
('SCALPING_STOP_LOSS_PCT',                '0.3',   'float', 'Stop loss % sul prezzo entrata'),
('SCALPING_TAKE_PROFIT_PCT',              '0.5',   'float', 'Take profit % sul prezzo entrata'),
('SCALPING_SIGNAL_STRENGTH_THRESHOLD',    '15.0',  'float', 'Soglia score intelligence 0-100'),
('SCALPING_MIN_CONFIDENCE',               '0.3',   'float', 'Confidenza minima combinata 0-1'),
('SCALPING_MIN_COLLECTORS',               '4',     'int',   'Collector minimi per usare intelligence'),
('SCALPING_SUPERVISOR_INTERVAL_SEC',      '600',   'int',   'Intervallo supervisor AI (secondi)'),
('SCALPING_STRATEGY_COOLDOWN_SEC',        '1200',  'int',   'Cooldown cambio strategia (secondi)'),
('SCALPING_PARAM_UPDATE_COOLDOWN_SEC',    '600',   'int',   'Cooldown update params (secondi)'),
('SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE', '5', 'int', 'Trade minimi prima di cambiare strategia'),
('SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS', '3',  'int',   'Max decisioni identiche consecutive'),
('SCALPING_REGIME_TREND_THRESHOLD_PCT',   '3.0',   'float', 'Soglia % per regime trending'),
('SCALPING_REGIME_VOLATILE_THRESHOLD',    '0.02',  'float', 'Soglia ATR/close per regime volatile');
```

---

### B4 — `ScalpingConfigLoader` (nuovo file)

**File:** `app/scalping/config_loader.py`

```python
"""ScalpingConfigLoader — merge .env + DB runtime config.

Gerarchia (priorità crescente):
  1. Valori hardcoded come default di classe
  2. Valori da .env / config.py (settings)
  3. Valori da DB scalping_runtime_config (override runtime)

Il loader viene istanziato UNA volta all'avvio sessione e può essere
ricaricato on-demand via reload() senza restart del backend.
"""

import logging
from typing import Any
from app.config import settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class ScalpingConfigLoader:
    """Configurazione scalping con override runtime da DB."""

    def __init__(self):
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self):
        """Carica config: prima da settings (.env), poi override da DB."""
        # Step 1: valori base da settings
        base = {
            "SCALPING_TRADE_VALUE":                  settings.SCALPING_TRADE_VALUE,
            "SCALPING_MAX_DAILY_LOSS":               settings.SCALPING_MAX_DAILY_LOSS,
            "SCALPING_MAX_DRAWDOWN_PCT":             settings.SCALPING_MAX_DRAWDOWN_PCT,
            "SCALPING_STOP_LOSS_PCT":                settings.SCALPING_STOP_LOSS_PCT,
            "SCALPING_TAKE_PROFIT_PCT":              settings.SCALPING_TAKE_PROFIT_PCT,
            "SCALPING_SIGNAL_STRENGTH_THRESHOLD":    settings.SCALPING_SIGNAL_STRENGTH_THRESHOLD,
            "SCALPING_MIN_CONFIDENCE":               settings.SCALPING_MIN_CONFIDENCE,
            "SCALPING_MIN_COLLECTORS":               settings.SCALPING_MIN_COLLECTORS,
            "SCALPING_SUPERVISOR_INTERVAL_SEC":      settings.SCALPING_SUPERVISOR_INTERVAL_SEC,
            "SCALPING_STRATEGY_COOLDOWN_SEC":        settings.SCALPING_STRATEGY_COOLDOWN_SEC,
            "SCALPING_PARAM_UPDATE_COOLDOWN_SEC":    settings.SCALPING_PARAM_UPDATE_COOLDOWN_SEC,
            "SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE": settings.SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE,
            "SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS": settings.SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS,
            "SCALPING_REGIME_TREND_THRESHOLD_PCT":   settings.SCALPING_REGIME_TREND_THRESHOLD_PCT,
            "SCALPING_REGIME_VOLATILE_THRESHOLD":    settings.SCALPING_REGIME_VOLATILE_THRESHOLD,
        }
        self._config = base

        # Step 2: override da DB
        try:
            db = get_supabase()
            rows = db.table("scalping_runtime_config").select("key, value, value_type").execute()
            if rows.data:
                type_map = {"float": float, "int": int, "bool": lambda v: v.lower() == "true", "str": str}
                for row in rows.data:
                    key = row["key"]
                    if key in self._config:
                        converter = type_map.get(row["value_type"], str)
                        try:
                            self._config[key] = converter(row["value"])
                        except (ValueError, TypeError) as e:
                            logger.warning("Config DB: valore non valido per %s=%s: %s", key, row["value"], e)
                logger.info("ScalpingConfigLoader: %d override DB caricati", len(rows.data))
        except Exception as e:
            logger.warning("ScalpingConfigLoader: DB non raggiungibile, uso solo .env: %s", e)

    def reload(self):
        """Ricarica la config da DB senza restart. Chiamare da API /config/reload."""
        logger.info("ScalpingConfigLoader: reload richiesto")
        self._load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    # Shortcut con tipo corretto
    @property
    def trade_value(self) -> float:
        return self._config["SCALPING_TRADE_VALUE"]

    @property
    def signal_strength_threshold(self) -> float:
        return self._config["SCALPING_SIGNAL_STRENGTH_THRESHOLD"]

    @property
    def min_confidence(self) -> float:
        return self._config["SCALPING_MIN_CONFIDENCE"]

    @property
    def min_collectors(self) -> int:
        return self._config["SCALPING_MIN_COLLECTORS"]

    @property
    def supervisor_interval_sec(self) -> int:
        return self._config["SCALPING_SUPERVISOR_INTERVAL_SEC"]

    @property
    def strategy_cooldown_sec(self) -> int:
        return self._config["SCALPING_STRATEGY_COOLDOWN_SEC"]

    @property
    def supervisor_min_trades_before_change(self) -> int:
        return self._config["SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE"]

    @property
    def supervisor_max_repeat_decisions(self) -> int:
        return self._config["SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS"]

    @property
    def stop_loss_pct(self) -> float:
        return self._config["SCALPING_STOP_LOSS_PCT"]

    @property
    def take_profit_pct(self) -> float:
        return self._config["SCALPING_TAKE_PROFIT_PCT"]

    @property
    def max_daily_loss(self) -> float:
        return self._config["SCALPING_MAX_DAILY_LOSS"]

    @property
    def regime_trend_threshold_pct(self) -> float:
        return self._config["SCALPING_REGIME_TREND_THRESHOLD_PCT"]

    @property
    def regime_volatile_threshold(self) -> float:
        return self._config["SCALPING_REGIME_VOLATILE_THRESHOLD"]


# Singleton — istanziato all'avvio, condiviso da tutti i moduli scalping
_scalping_config: ScalpingConfigLoader | None = None


def get_scalping_config() -> ScalpingConfigLoader:
    global _scalping_config
    if _scalping_config is None:
        _scalping_config = ScalpingConfigLoader()
    return _scalping_config
```

---

### B5 — Endpoint API config

Aggiungere a `router.py` (o a un file `config_scalping_api.py` separato):

```python
# GET /api/scalping/config — legge config corrente (merge .env + DB)
@router.get("/scalping/config")
async def get_scalping_config_endpoint():
    cfg = get_scalping_config()
    return {"config": cfg._config, "source": "env+db_override"}

# POST /api/scalping/config — aggiorna un valore nel DB (override runtime)
@router.post("/scalping/config/{key}")
async def update_scalping_config(key: str, value: str):
    db = get_supabase()
    db.table("scalping_runtime_config").update({
        "value": value,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("key", key).execute()
    get_scalping_config().reload()
    return {"key": key, "value": value, "status": "updated"}

# POST /api/scalping/config/reload — ricarica senza restart
@router.post("/scalping/config/reload")
async def reload_scalping_config():
    get_scalping_config().reload()
    return {"status": "reloaded"}
```

---

## 4. FASE C — Dati Intelligence Affidabili

> **Prerequisito:** Fase B completata.  
> **Stima:** 2-3 ore  
> **File coinvolti:** `collectors/fear_greed.py`, `signal_score_engine.py`

---

### C1 — Sostituire Fear & Greed con alternative.me

**Problema:** CryptoCompare restituisce valore fisso 8 (API key non valida o endpoint cambiato). Il valore reale Fear & Greed di mercato è diverso e non viene mai aggiornato.

**Soluzione:** usare `https://api.alternative.me/fng/` — gratuita, no API key, aggiornata ogni 24h.

**File:** `app/scalping/intelligence/collectors/fear_greed.py`

```python
"""FearGreedCollector — usa alternative.me (gratuita, no API key).

Endpoint: GET https://api.alternative.me/fng/?limit=1
Risposta:
{
  "data": [{
    "value": "34",
    "value_classification": "Fear",
    "timestamp": "1718000000"
  }]
}

Aggiornamento: 1 volta ogni 24h (cacheare il valore intraday).
"""

import aiohttp
import logging
from datetime import datetime, timedelta
from app.scalping.models.intelligence import FearGreedSnapshot

logger = logging.getLogger(__name__)

ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/?limit=1"

# Cache intraday: il valore cambia al massimo 1 volta al giorno
_cached_value: int | None = None
_cached_at: datetime | None = None
_CACHE_TTL = timedelta(hours=4)  # rileggi ogni 4h per sicurezza


class FearGreedCollector:

    async def fetch(self) -> FearGreedSnapshot | None:
        global _cached_value, _cached_at

        # Usa cache se valida
        if _cached_value is not None and _cached_at is not None:
            if datetime.utcnow() - _cached_at < _CACHE_TTL:
                return FearGreedSnapshot(
                    value=_cached_value,
                    classification=self._classify(_cached_value),
                    timestamp=_cached_at,
                )

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(ALTERNATIVE_ME_URL) as resp:
                    if resp.status != 200:
                        logger.warning("FearGreed alternative.me: HTTP %d", resp.status)
                        return self._use_cache_or_none()
                    data = await resp.json()
                    value = int(data["data"][0]["value"])
                    _cached_value = value
                    _cached_at = datetime.utcnow()
                    logger.info("FearGreed aggiornato: %d (%s)", value, self._classify(value))
                    return FearGreedSnapshot(
                        value=value,
                        classification=self._classify(value),
                        timestamp=_cached_at,
                    )
        except Exception as e:
            logger.warning("FearGreed alternative.me error: %s", e, exc_info=True)
            return self._use_cache_or_none()

    def _use_cache_or_none(self) -> FearGreedSnapshot | None:
        if _cached_value is not None:
            logger.info("FearGreed: uso cache (valore=%d)", _cached_value)
            return FearGreedSnapshot(
                value=_cached_value,
                classification=self._classify(_cached_value),
                timestamp=_cached_at or datetime.utcnow(),
            )
        logger.warning("FearGreed: nessun dato disponibile (né live né cache)")
        return None

    @staticmethod
    def _classify(value: int) -> str:
        if value <= 20:   return "Extreme Fear"
        if value <= 40:   return "Fear"
        if value <= 60:   return "Neutral"
        if value <= 80:   return "Greed"
        return "Extreme Greed"

    @staticmethod
    def value_to_score(value: int) -> float:
        """Converte Fear & Greed (0-100) in score (-100 a +100).
        
        Logica contrarian:
          < 20 (Extreme Fear)  → score positivo (opportunità long)
          > 80 (Extreme Greed) → score negativo (cautela)
          40-60 (Neutral)      → score vicino a 0
        """
        if value < 20:
            return (20 - value) * 5.0          # max +100 a value=0
        elif value > 80:
            return -(value - 80) * 5.0         # max -100 a value=100
        elif value < 40:
            return (40 - value) * 1.5          # +30 max a value=20
        elif value > 60:
            return -(value - 60) * 1.5         # -30 max a value=80
        return 0.0
```

**Aggiungere a `.env`** (già previsto in B1):
```bash
SCALPING_FEAR_GREED_SOURCE=alternative_me
```

---

### C2 — Gestire Whale collector disabilitato

**Problema:** il whale collector ha peso 0.10 ma restituisce sempre `None`, riducendo la coverage senza contribuire. La formula di coverage conta il peso del whale anche quando è disabilitato.

**Soluzione:** escludere whale dalla coverage se `SCALPING_WHALE_ENABLED=false`.

**Modifiche a `signal_score_engine.py`:**

```python
# Nel metodo compute() o get_snapshot(), prima di raccogliere i collector:

from app.config import settings

# Costruisci la lista dei collector attivi in base alla configurazione
active_collectors = {
    "funding_rate":    (funding_rate_collector, 0.20),
    "cvd":             (cvd_calculator,         0.20),
    "open_interest":   (oi_collector,           0.15),
    "long_short_ratio":(ls_collector,           0.15),
    "fear_greed":      (fear_greed_collector,   0.15),
    "sentiment":       (sentiment_collector,    0.05),
    "onchain":         (onchain_collector,      0.00),  # peso 0 = raccolto ma non score
}

# Whale: aggiunto solo se configurato
if settings.SCALPING_WHALE_ENABLED:
    active_collectors["whale"] = (whale_collector, 0.10)
# Altrimenti: peso rimane 0, coverage non viene ridotta da un collector fantasma
```

**Importante:** verificare che la somma dei pesi dei collector attivi sia sempre normalizzata. Se whale è disabilitato, il peso 0.10 deve essere ridistribuito o la formula di coverage deve escluderlo esplicitamente:

```python
# Coverage = somma pesi dei collector che hanno RISPOSTO (non quelli configurati)
total_weight_configured = sum(w for _, w in active_collectors.values() if w > 0)
total_weight_responded  = sum(w for name, (_, w) in active_collectors.items() 
                              if results.get(name) is not None and w > 0)
coverage = total_weight_responded / total_weight_configured if total_weight_configured > 0 else 0.0
```

---

## 5. FASE D — Ricalibrazione Score Engine

> **Prerequisito:** Fase C completata (dati corretti prima di ricalibrare).  
> **Stima:** 3-4 ore  
> **File coinvolti:** `signal_score_engine.py`, `signal_aggregator.py`

---

### D1 — Diagnosi: perché lo score non supera mai 1.0

Il problema è nella pipeline di normalizzazione. Tracciare il flusso con valori reali:

```
Esempio con 6 collector attivi:

funding_rate_score = 0.0    (neutro)     peso = 0.20  → contributo = 0.0
cvd_score         = +15.0   (lieve buy)  peso = 0.20  → contributo = 3.0
oi_score          = -5.0    (neutro)     peso = 0.15  → contributo = -0.75
long_short_score  = -10.0   (60% long)   peso = 0.15  → contributo = -1.5
fear_greed_score  = +30.0   (fear=12)    peso = 0.15  → contributo = 4.5
sentiment_score   = +5.0    (neutro+)    peso = 0.05  → contributo = 0.25

weighted_sum = 3.0 - 0.75 - 1.5 + 4.5 + 0.25 = 5.5
total_weight = 0.20 + 0.20 + 0.15 + 0.15 + 0.15 + 0.05 = 0.90

weighted_avg = 5.5 / 0.90 = 6.11

→ Se i collector restituiscono score in [-100, +100]:
  weighted_avg max teorico = 100.0 → OK, la soglia 15 è raggiungibile

→ Se i collector restituiscono score in [-1, +1] (problema attuale):
  weighted_avg max teorico = 1.0 → soglia 15 IRRAGGIUNGIBILE
```

**Azione:** aggiungere un log di diagnostica temporaneo per verificare la scala reale:

```python
# In signal_score_engine.py, nel metodo compute(), dopo aver calcolato i singoli score:
logger.debug(
    "[ScoreEngine] breakdown raw: %s | weighted_avg=%.4f | total_weight=%.2f | coverage=%.2f",
    {k: round(v, 4) for k, v in raw_scores.items()},
    weighted_avg,
    total_weight,
    coverage,
)
```

Eseguire per 2-3 cicli e leggere il breakdown. Il risultato rivela se il problema è nella scala dei singoli score o nella formula di aggregazione.

---

### D2 — Fix normalizzazione (dopo diagnosi)

**Scenario A — collector restituiscono già [-100, +100]:**  
Il problema è altrove (formula di aggregazione). Verificare che `weighted_avg` non venga diviso per 100 da qualche parte prima di essere confrontato con la soglia.

**Scenario B — collector restituiscono [-1, +1]:**  
Ogni metodo `*_to_score()` deve scalare a [-100, +100]:

```python
# ESEMPIO: funding_rate_to_score
# PRIMA (scala -1..+1):
def rate_to_score(rate: float) -> float:
    return max(-1.0, min(1.0, rate / 0.001))

# DOPO (scala -100..+100):
def rate_to_score(rate: float) -> float:
    raw = rate / 0.001 * 50      # 0.1% → 50 punti
    return max(-100.0, min(100.0, raw))
```

Applicare la stessa conversione a tutti i collector. La funzione `value_to_score` di `FearGreedCollector` nel punto C1 già restituisce valori in [-100, +100].

---

### D3 — Aggiornare soglie in `.env` dopo fix scala

Dopo aver verificato la scala corretta, aggiornare le soglie:

```bash
# Con scala corretta [-100, +100]:
SCALPING_SIGNAL_STRENGTH_THRESHOLD=15.0   # 15/100 = segnale debole ma presente
# Interpretazione:
#   < 15  = mercato neutrale, no trade
#  15-30  = segnale debole, trade con cautela
#  30-60  = segnale moderato, trade normale
#   > 60  = segnale forte, trade con piena confidenza
```

---

### D4 — Aggiornare SignalAggregator con min_collectors da config

```python
# In signal_aggregator.py, nel metodo should_execute():

# PRIMA (hardcoded):
if num_collectors_responded <= 3:

# DOPO (da config):
from app.scalping.config_loader import get_scalping_config
min_collectors = get_scalping_config().min_collectors

if num_collectors_responded < min_collectors:
```

---

## 6. FASE E — Supervisor Potenziato

> **Prerequisito:** Fasi A, B, C completate.  
> **Stima:** 4-5 ore  
> **File coinvolti:** `supervisor_client.py`, `supervisor_scheduler.py`

---

### E1 — Arricchire il contesto utente (`build_scalping_context`)

Il supervisor attualmente riceve solo dati di mercato istantanei. Deve ricevere anche:
- Performance della sessione corrente
- Storico trade recenti
- Le proprie decisioni precedenti

**Modifiche a `supervisor_scheduler.py`** o dove risiede `build_scalping_context()`:

```python
async def build_scalping_context(
    symbol: str,
    snapshot,           # MarketIntelSnapshot
    regime: str,
    regime_confidence: float,
    score: SignalScore,
    session_id: str,    # NUOVO
) -> dict:
    """Costruisce il contesto completo per il supervisor AI."""

    # Dati esistenti (mercato)
    market_data = {
        "symbol": symbol,
        "regime": regime,
        "regime_confidence": round(regime_confidence, 2),
        "funding_rate": snapshot.funding_rate,
        "cvd": snapshot.cvd_trend,
        "open_interest": snapshot.open_interest,
        "long_short": {
            "long_pct": snapshot.long_pct,
            "short_pct": snapshot.short_pct,
        },
        "fear_greed": {
            "value": snapshot.fear_greed_value,
            "label": snapshot.fear_greed_label,
        },
        "signal_score": {
            "total": score.total,
            "bias": score.bias,
            "collectors_responded": len(score.breakdown),
        },
    }

    # NUOVO: Performance sessione corrente
    db = get_supabase()
    session_perf = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0, "win_rate": 0.0}
    current_strategy_trades = 0

    try:
        trades_res = db.table("scalping_trades")\
            .select("side, pnl, strategy_type, status, created_at")\
            .eq("session_id", session_id)\
            .eq("status", "closed")\
            .order("created_at", desc=True)\
            .limit(20)\
            .execute()

        if trades_res.data:
            trades = trades_res.data
            wins = [t for t in trades if (t.get("pnl") or 0) > 0]
            losses = [t for t in trades if (t.get("pnl") or 0) <= 0]
            total_pnl = sum(t.get("pnl") or 0 for t in trades)
            session_perf = {
                "trades": len(trades),
                "wins": len(wins),
                "losses": len(losses),
                "pnl": round(total_pnl, 4),
                "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
                "recent_5": [
                    {"strategy": t["strategy_type"], "pnl": round(t.get("pnl") or 0, 4)}
                    for t in trades[:5]
                ],
            }
    except Exception as e:
        logger.warning("build_context: errore lettura trade: %s", e)

    # NUOVO: Strategia attiva e da quanto tempo
    active_strategy_info = {}
    try:
        from app.scalping.router import _execution_state
        active_strategy_info = {
            "name": _execution_state["session"].get("strategy", "unknown"),
            "overridden_by_supervisor": _execution_state["session"].get("strategy_overridden", False),
        }
    except Exception:
        pass

    return {
        "market": market_data,
        "session_performance": session_perf,
        "active_strategy": active_strategy_info,
    }
```

---

### E2 — Aggiornare `_format_context()` per il prompt utente

```python
def _format_context(ctx: dict) -> str:
    m = ctx["market"]
    p = ctx["session_performance"]
    s = ctx["active_strategy"]
    hist = ctx.get("supervisor_history", [])

    # Sezione mercato (come prima)
    market_section = f"""
=== MERCATO: {m['symbol']} ===
Regime: {m['regime']} (confidenza: {m['regime_confidence']:.0%})
Funding Rate: {m['funding_rate']}
CVD: {m['cvd']}
Open Interest: {m['open_interest']}
Long/Short: {m['long_short']['long_pct']}% / {m['long_short']['short_pct']}%
Fear & Greed: {m['fear_greed']['value']} ({m['fear_greed']['label']})
Signal Score: {m['signal_score']['total']:.1f} ({m['signal_score']['bias']}) — {m['signal_score']['collectors_responded']} collector attivi
"""

    # NUOVA sezione performance
    perf_section = f"""
=== PERFORMANCE SESSIONE ===
Trade chiusi: {p['trades']} (Win: {p['wins']}, Loss: {p['losses']}, Win Rate: {p['win_rate']}%)
PnL totale sessione: {p['pnl']:.4f} USDC
Strategia attiva: {s['name']} {'(override supervisor)' if s['overridden_by_supervisor'] else '(auto-selezionata)'}
Ultimi 5 trade: {p.get('recent_5', 'nessuno')}
"""

    # NUOVA sezione decisioni precedenti del supervisor
    history_section = ""
    if hist:
        history_section = "\n=== ULTIME DECISIONI SUPERVISOR ===\n"
        for h in hist[-5:]:  # ultime 5
            history_section += f"- {h['action']} → {h['reason'][:80]}... (applicata: {h['applied']})\n"

    return market_section + perf_section + history_section + "\nFornisci la tua decisione:"
```

---

### E3 — Aggiornare il System Prompt

Il system prompt attuale va integrato con istruzioni su quando NON agire e come interpretare il proprio storico.

**Sostituzione completa di `SUPERVISOR_SYSTEM_PROMPT` in `supervisor_client.py`:**

```python
SUPERVISOR_SYSTEM_PROMPT = """
Sei un supervisore AI esperto in trading scalping su criptovalute.
Il tuo ruolo è analizzare i dati di mercato e di performance per ottimizzare
la strategia di scalping attiva. Sei un trader disciplinato: non cambi
rotta senza evidenza concreta.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGOLA CRITICA — MAPPING REGIME → STRATEGIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ranging        → rsi_bollinger, momentum_base, stoch_rsi_bb_squeeze
- trending_up    → ema_cross
- trending_down  → ema_cross
- volatile       → stoch_rsi_bb_squeeze, momentum_base
- unknown        → momentum_base

NON assegnare mai ema_cross in ranging: genera falsi segnali.
NON assegnare stoch_rsi_bb_squeeze in trending: spreca i breakout.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GERARCHIA DEI SEGNALI (priorità decrescente)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Funding Rate: > +0.1% = leva eccessiva long (bias short)
                 < -0.1% = leva eccessiva short (bias long)
2. CVD: crescente = pressione buy reale; calante = pressione sell
3. Open Interest: crescita + prezzo laterale = breakout imminente
4. Long/Short Ratio: > 70% long = sovraesposizione; < 30% = oversold
5. Fear & Greed: < 20 o > 80 = potenziale inversione contrarian
6. On-chain Exchange Flow: inflow = bearish, outflow = bullish
7. Sentiment news: solo per conferma, mai come segnale primario
8. Indicatori tecnici (EMA, RSI, BB): solo come filtri di timing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUANDO NON AGIRE (no_action)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scegli no_action se:
- La strategia attuale ha prodotto meno di 5 trade chiusi: non hai
  abbastanza dati per valutarla. Attendi evidenza prima di cambiare.
- Hai già proposto la stessa azione nelle ultime 3 decisioni:
  se la proposta è stata ignorata (cooldown), non ha senso ripeterla.
  Invece, considera se il problema è altrove (dati insufficienti,
  collector non attivi, regime instabile).
- I dati di intelligence sono parziali (< 4 collector attivi):
  con dati incompleti, la decisione migliore è mantenere lo status quo.
- Il signal score è neutrale (|score| < 15) e non hai altri segnali forti.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUANDO AGIRE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
change_strategy: il regime è cambiato in modo confermato (confidence > 0.6)
  E la strategia attuale non è compatibile con il nuovo regime
  E ci sono almeno 5 trade che mostrano performance scarse.

update_params: la strategia è giusta per il regime ma i parametri
  non sono ottimali (es. ATR alto → allarga SL/TP, win rate basso
  con molti trade → riduci confidenza minima).

pause_trading: segnali contraddittori forti su più timeframe,
  volatilità estrema, o drawdown > soglia configurata.

resume_trading: solo dopo una pausa, quando le condizioni sono migliorate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO RISPOSTA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rispondi SOLO con JSON valido, senza markdown né testo extra:
{
  "action": "update_params|change_strategy|pause_trading|resume_trading|no_action",
  "reason": "spiegazione in italiano con riferimento ai dati reali ricevuti",
  "confidence": 0.0-1.0,
  "market_bias": "bullish|bearish|neutral",
  "primary_signal": "quale dato ha guidato la decisione",
  "new_params": {...} oppure null,
  "new_strategy": "ema_cross|rsi_bollinger|stoch_rsi_bb_squeeze|momentum_base|vwap_reversion" oppure null
}
"""
```

---

## 7. FASE F — Memoria del Supervisor

> **Prerequisito:** Fase E completata.  
> **Stima:** 3-4 ore  
> **File coinvolti:** nuova tabella DB, `supervisor_scheduler.py`, `supervisor_client.py`

---

### F1 — Tabella `supervisor_memory`

```sql
-- Storico decisioni supervisor con outcome verificato
CREATE TABLE supervisor_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES scalping_sessions(id),
    symbol          TEXT NOT NULL,
    decided_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Decisione presa
    action          TEXT NOT NULL,
    reason          TEXT NOT NULL,
    confidence      NUMERIC(4,3),
    market_bias     TEXT,
    primary_signal  TEXT,
    new_strategy    TEXT,
    new_params      JSONB,

    -- Fu applicata o bloccata (cooldown, regime mismatch, ecc.)?
    was_applied     BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_reason  TEXT,       -- es. "cooldown attivo", "regime mismatch"

    -- Contesto al momento della decisione (snapshot completo)
    market_context  JSONB,      -- regime, score, funding_rate, fear_greed, ecc.
    session_perf    JSONB,      -- trade_count, win_rate, pnl al momento

    -- Outcome verificato (popolato dopo N minuti/trade)
    -- Permette al supervisor di imparare se la decisione era giusta
    outcome_verified_at  TIMESTAMPTZ,
    outcome_pnl_delta    NUMERIC(12,6),   -- PnL guadagnato/perso dopo la decisione
    outcome_win_rate_delta NUMERIC(5,2),  -- variazione win rate dopo la decisione
    outcome_label        TEXT             -- 'positive', 'negative', 'neutral'
);

CREATE INDEX idx_supervisor_memory_symbol ON supervisor_memory(symbol, decided_at DESC);
CREATE INDEX idx_supervisor_memory_session ON supervisor_memory(session_id);
CREATE INDEX idx_supervisor_memory_action ON supervisor_memory(action, was_applied);
```

---

### F2 — Persistenza decisioni in `supervisor_scheduler.py`

Ogni decisione del supervisor (anche quelle bloccate dal cooldown) deve essere salvata:

```python
async def _save_decision_to_memory(
    self,
    decision: SupervisorDecision,
    was_applied: bool,
    blocked_reason: str | None,
    market_context: dict,
    session_perf: dict,
    session_id: str,
):
    """Salva la decisione del supervisor nella memoria persistente."""
    try:
        db = get_supabase()
        db.table("supervisor_memory").insert({
            "session_id": session_id,
            "symbol": self.symbol,
            "action": decision.action,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "market_bias": decision.market_bias,
            "primary_signal": decision.primary_signal,
            "new_strategy": decision.new_strategy,
            "new_params": decision.new_params,
            "was_applied": was_applied,
            "blocked_reason": blocked_reason,
            "market_context": market_context,
            "session_perf": session_perf,
        }).execute()
    except Exception as e:
        logger.warning("supervisor_memory: errore salvataggio: %s", e)
```

---

### F3 — Caricamento memoria nel contesto

Aggiungere a `build_scalping_context()`:

```python
# NUOVO: ultime decisioni supervisor (per evitare loop)
supervisor_history = []
try:
    mem_res = db.table("supervisor_memory")\
        .select("action, reason, was_applied, blocked_reason, decided_at")\
        .eq("symbol", symbol)\
        .order("decided_at", desc=True)\
        .limit(10)\
        .execute()
    if mem_res.data:
        supervisor_history = [
            {
                "action": r["action"],
                "reason": r["reason"][:100],
                "applied": r["was_applied"],
                "blocked": r.get("blocked_reason"),
                "at": r["decided_at"],
            }
            for r in mem_res.data
        ]
except Exception as e:
    logger.warning("build_context: errore lettura memoria supervisor: %s", e)

return {
    "market": market_data,
    "session_performance": session_perf,
    "active_strategy": active_strategy_info,
    "supervisor_history": supervisor_history,   # NUOVO
}
```

---

### F4 — Verifica outcome (background job)

Aggiungere un job APScheduler che verifica l'outcome delle decisioni dopo 30 minuti:

```python
# In scheduler/jobs.py:

async def verify_supervisor_outcomes_job():
    """Verifica outcome delle decisioni supervisor dopo 30 minuti.
    
    Una decisione 'change_strategy' applicata 30 minuti fa:
    - Se il PnL è migliorato → outcome='positive'
    - Se è peggiorato → outcome='negative'
    - Se invariato → outcome='neutral'
    """
    from datetime import timedelta
    db = get_supabase()

    # Trova decisioni applicate 25-35 minuti fa senza outcome
    cutoff_from = (datetime.utcnow() - timedelta(minutes=35)).isoformat()
    cutoff_to   = (datetime.utcnow() - timedelta(minutes=25)).isoformat()

    pending = db.table("supervisor_memory")\
        .select("id, session_id, action, session_perf")\
        .eq("was_applied", True)\
        .is_("outcome_verified_at", "null")\
        .gte("decided_at", cutoff_from)\
        .lte("decided_at", cutoff_to)\
        .execute()

    for mem in (pending.data or []):
        try:
            # Leggi PnL corrente della sessione
            session_res = db.table("scalping_sessions")\
                .select("total_pnl")\
                .eq("id", mem["session_id"])\
                .single()\
                .execute()

            old_pnl = (mem.get("session_perf") or {}).get("pnl", 0)
            new_pnl = session_res.data.get("total_pnl", 0) if session_res.data else old_pnl
            pnl_delta = new_pnl - old_pnl

            outcome = "positive" if pnl_delta > 0.01 else "negative" if pnl_delta < -0.01 else "neutral"

            db.table("supervisor_memory").update({
                "outcome_verified_at": datetime.utcnow().isoformat(),
                "outcome_pnl_delta": round(pnl_delta, 6),
                "outcome_label": outcome,
            }).eq("id", mem["id"]).execute()

            logger.info("Outcome verificato per decisione %s: %s (pnl_delta=%.4f)", 
                       mem["id"], outcome, pnl_delta)
        except Exception as e:
            logger.warning("Errore verifica outcome %s: %s", mem["id"], e)

# Registrare nel setup_scheduler():
scheduler.add_job(verify_supervisor_outcomes_job, 'interval', minutes=5, id='verify_outcomes_job')
```

---

## 8. Sequenza di Deploy

```
GIORNO 1 (mattina):
  ├── Fase A: rimuovi force_execute, fix supervisor interval
  ├── Verifica: avvia sessione paper, controlla log
  └── Test: nessun trade parte senza segnale tecnico + intelligence

GIORNO 1 (pomeriggio):
  ├── Fase B: migration DB, config_loader, .env aggiornato
  ├── Verifica: GET /api/scalping/config restituisce valori corretti
  └── Test: modifica un valore via POST /api/scalping/config, verifica reload

GIORNO 2:
  ├── Fase C: sostituisci Fear & Greed, fix whale coverage
  ├── Verifica: nei log appare "FearGreed aggiornato: XX (Fear/Greed)"
  └── Test: Fear & Greed non è più fisso a 8

GIORNO 2 (tarda):
  ├── Fase D: log diagnostica score → analisi output collector
  ├── Fix normalizzazione (Scenario A o B in base a diagnosi)
  └── Verifica: score appare ora in range [-100, +100] nei log

GIORNO 3:
  ├── Fase E: context arricchito + system prompt aggiornato
  ├── Verifica: prompt utente contiene sezione PERFORMANCE SESSIONE
  └── Test: supervisor dice "no_action" se < 5 trade in sessione

GIORNO 3-4:
  ├── Fase F: tabella memoria, persistenza, job outcome
  ├── Verifica: supervisor_memory si popola a ogni decisione
  └── Test: dopo 30 min, outcome_label viene valorizzato
```

---

## 9. Test di Validazione

### Per ogni fase, verificare nei log:

**Fase A:**
```
# NON deve più apparire:
📋 LIVE MODE: ... (intelligence bypassed)    ← solo se collector ok

# DEVE apparire:
🔴 BLOCK: ... intelligence neutrale          ← con 4+ collector
🟢 SIGNAL: BUY ...                           ← quando score > soglia

# Supervisor ogni 10 min (non ogni 45s):
[ModelClient] Trying Tier 1: ...             ← ogni ~600 secondi
```

**Fase C:**
```
# DEVE apparire:
FearGreed aggiornato: 34 (Fear)              ← valore reale, non 8
```

**Fase D:**
```
# DEVE apparire (dopo aggiunta log diagnostica):
[ScoreEngine] breakdown raw: {'funding_rate': 0.0, 'cvd': 15.0, ...} | weighted_avg=6.11
```

**Fase E:**
```
# Il supervisor deve rispondere no_action quando:
# - trade sessione < 5
# - stessa azione proposta 3+ volte di fila
# Verificare nel log che la reason citi i dati reali ricevuti
```

**Fase F:**
```
# In Supabase dashboard, tabella supervisor_memory:
# - ogni decisione (anche bloccate) ha una riga
# - dopo 30 min, outcome_label è valorizzato
```

---

*Fine documento — versione 3.1*
