# ⚡ SynthTrade — Specifica Completa v3

> *Synthetic intelligence. Real profits.*

---

## 🏷️ Proposta Nomi Progetto

| Nome | Tagline | Tono |
|---|---|---|
| StratOS | *The Operating System for Crypto Strategies* | Tecnico, professionale |
| NeuralEdge | *AI-powered alpha, human-approved* | IA + trading |
| **✅ SynthTrade** | ***Synthetic intelligence. Real profits.*** | **Futuristico, moderno — SCELTO** |
| SignalForge | *Forge your edge from raw market noise* | Potente, artigianale |
| ApexCore | *Where algorithms meet conviction* | Premium, assertivo |
| ZeroLag | *Zero latency. Zero guesswork.* | Performance, tecnico |
| PulseAI | *Read the market's heartbeat* | Dinamico, biologico |
| VaultOS | *Protect and grow every position* | Sicuro, affidabile |
| OracleX | *Predict. Validate. Execute.* | Misterioso, potente |
| CipherAlpha | *Decoding markets, one signal at a time* | Crypto-native, tech |

---

## 🎨 Design System — Frontend

### Concept Visivo

Direzione: **Dark Terminal Futurism** — come se Bloomberg Terminal incontrasse un sistema operativo militare del futuro. Ispirazione Binance per la densità informativa, ma con identità propria e più buio.

- Sfondo quasi nero, non grigio scuro
- Accenti dorati/teal, quasi neon ma contenuti
- Tipografia monospaced per tutti i dati numerici
- Animazioni fini al servizio dello stato: nulla è decorativo
- Ogni elemento "vive" — nulla è statico in presenza di dati live

---

### 🎨 Color Palette

```scss
// === BACKGROUND ===
--bg-base:        #07090C;              // Nero quasi totale (più scuro di Binance)
--bg-surface:     #0D1117;             // Card, sidebar
--bg-elevated:    #161B22;             // Dropdown, modal, tooltip
--bg-overlay:     #1C2128;             // Hover states, selected rows

// === BRAND — SynthTrade ===
--accent-primary:   #F0B90B;           // Gold — CTA, segnali attivi
--accent-glow:      rgba(240,185,11,0.15);  // Glow diffuso
--accent-secondary: #00D4AA;           // Teal — AI score, conferme

// === SEMANTIC ===
--color-buy:    #0ECB81;               // Verde — long, profit, ACTIVE
--color-sell:   #F6465D;               // Rosso — short, loss, REJECT
--color-warn:   #F0B90B;               // Giallo — PENDING, warning
--color-info:   #1890FF;               // Blu — info, neutro

// === TESTO ===
--text-primary:   #EAECEF;
--text-secondary: #848E9C;
--text-muted:     #474D57;

// === BORDI ===
--border-default: rgba(234,236,239,0.06);
--border-focus:   rgba(240,185,11,0.4);
--border-active:  var(--accent-primary);
```

---

### 🔤 Tipografia

```scss
// Display / Heading — look futuristico, tech
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&display=swap');

// Body / UI — leggibile, neutro
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&display=swap');

// Numeri / Dati / Timestamp / Code — monospaced, tecnico
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

$font-display: 'Chakra Petch', sans-serif;  // Logo, H1–H3, ticker labels
$font-body:    'DM Sans', sans-serif;       // Tutto il testo UI, bottoni, label
$font-mono:    'JetBrains Mono', monospace; // Prezzi, hash, timestamp, score
```

---

### 📐 Layout & Spacing

```
┌─────────────────────────────────────────────────────────────────┐
│  SIDEBAR (240px fixed)      │  MAIN CONTENT (flex-1)            │
│  bg: --bg-surface           │  bg: --bg-base                    │
│                             │                                    │
│  [⚡ SynthTrade]            │  [Topbar: live ticker + account]  │
│                             │  BTC 62,418 ▲  ETH 3,241 ▼       │
│  ● Dashboard                │                                    │
│  ○ Strategies               │  [Page Content Area]              │
│  ○ Active Trade             │                                    │
│  ○ Logs                     │                                    │
│                             │                                    │
│  ─────────────────          │                                    │
│  ENGINE  ● RUNNING          │                                    │
│  Last scan  2m ago          │                                    │
│  Next regen  21h            │                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Spacing scale (8px base):** `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64px`
**Border radius:** `4px` piccoli · `8px` card · `12px` modal

---

### 🖥️ Componenti UI Key

#### Stat Card
```
┌──────────────────────────────────────┐
│  CAPITAL BALANCE               ↗ 8h  │
│                                      │
│  €2,847.32                   +4.2%  │  ← JetBrains Mono 28px, --color-buy
│  ▲ €114.82 today                     │
│                                      │
│  ██████████████░░░░░  67% target    │  ← progress bar dorata
└──────────────────────────────────────┘
```

#### Strategy Row
```
┌────┬───────────────────┬────────┬──────┬──────────┬─────────────────┐
│ ●  │ TREND BTC v3      │ +6.2%  │ 3.1% │ ★ 0.81  │ [APPROVE] [✕]  │
│    │ BTC/USDT · 5m     │ PnL    │ DD   │ AI Score │                 │
└────┴───────────────────┴────────┴──────┴──────────┴─────────────────┘
```
Pallino ●: `--color-warn` PENDING · `--color-buy` ACTIVE · `--text-muted` EXPIRED

#### Live Ticker (topbar)
```
  BTC/USDT  62,418.50  ▲ +1.2%      ETH/USDT  3,241.80  ▼ -0.4%
```
Flash verde/rosso su ogni tick di aggiornamento prezzo.

#### Log Entry
```
┌────────────────────────────────────────────────────────────────┐
│ 14:32:07  ▲ BUY   BTC/USDT                                     │
│ price: 62,000  qty: 0.0003  strategy: trend_v3                 │
│ reason: EMA crossover confirmed  ·  ai_score: 0.81   [detail]  │
└────────────────────────────────────────────────────────────────┘
```

---

### ✨ Animazioni & Micro-interazioni

```scss
// Strategia attiva: glow pulsante sul border
.strategy-card.active {
  box-shadow: 0 0 0 1px var(--accent-primary),
              0 0 20px var(--accent-glow);
  animation: pulse-border 3s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { box-shadow: 0 0 0 1px var(--accent-primary), 0 0 12px var(--accent-glow); }
  50%       { box-shadow: 0 0 0 1px var(--accent-primary), 0 0 28px var(--accent-glow); }
}

// Prezzo aggiornato: flash colore
@keyframes price-up   { 0%,100%{color:var(--text-primary)} 40%{color:var(--color-buy)} }
@keyframes price-down { 0%,100%{color:var(--text-primary)} 40%{color:var(--color-sell)} }

.price.up   { animation: price-up   0.6s ease; }
.price.down { animation: price-down 0.6s ease; }

// Sidebar nav: hover con gradiente dorato
.nav-item:hover {
  background: linear-gradient(90deg, var(--accent-glow), transparent);
  border-left: 2px solid var(--accent-primary);
  transition: all 0.2s ease;
}

// Scanline overlay — effetto terminale
.terminal-surface::after {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg, transparent 0px, transparent 2px,
    rgba(255,255,255,0.012) 2px, rgba(255,255,255,0.012) 4px
  );
  pointer-events: none;
  border-radius: inherit;
}
```

---

### 📄 Pagine Angular — Dettaglio

#### `/login`
- Fullscreen, sfondo `--bg-base`
- Logo SynthTrade centrato con tagline
- Input password, icona show/hide, submit on Enter
- Animazione: logo con `--accent-glow` al load, fade-in staggered

#### `/dashboard`
CSS Grid 12 colonne:
- **Row 1:** 3 stat card (Balance, PnL oggi, Strategia attiva)
- **Row 2:** Grafico equity (lightweight-charts, area chart dark, full width)
- **Row 3:** Engine status panel + ultimi 5 log

#### `/strategies`
- Tabella con tab filter: PENDING / ACTIVE / ALL
- Modal dettaglio: params + equity curve backtest + AI note
- Azioni inline: APPROVE (gold), REJECT (red), DETAILS
- Badge status colorati, empty state se nessuna strategia

#### `/active`
- Candlestick chart live (pair + timeframe strategia attiva)
- Overlay entry/exit points
- Progress bar verso target orizzontale
- KPI: success_score, drawdown corrente, PnL live
- Bottone emergency STOP in rosso con confirm modal

#### `/logs`
- Tabella CDK Virtual Scroll (performance su 10k+ righe)
- Filtri: range date, action BUY/SELL, strategy ID
- Export CSV via endpoint backend

---

## 📁 Struttura Progetto

```
synthtrade/                               ← root monorepo
│
├── supabase/                             ← Supabase CLI config
│   ├── config.toml                       ← config progetto Supabase
│   ├── seed.sql                          ← dati iniziali di test
│   └── migrations/
│       ├── 20240101000001_strategies.sql
│       ├── 20240101000002_trades.sql
│       ├── 20240101000003_logs.sql
│       └── 20240101000004_ohlcv_cache.sql
│
├── backend/                              ← FastAPI
│   ├── app/
│   │   ├── main.py                       ← entry point, lifespan, CORS
│   │   ├── config.py                     ← Settings via pydantic-settings
│   │   ├── dependencies.py               ← DI: supabase client, auth, engine
│   │   │
│   │   ├── api/                          ← routers HTTP
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                   ← POST /auth/login
│   │   │   ├── strategies.py             ← GET/POST /strategies
│   │   │   ├── dashboard.py              ← GET /dashboard, /dashboard/equity
│   │   │   ├── logs.py                   ← GET /logs, /logs/export
│   │   │   └── ws.py                     ← WS /ws (live feed)
│   │   │
│   │   ├── core/                         ← logica business
│   │   │   ├── strategy_generator.py     ← prodotto cartesiano parametri
│   │   │   ├── backtester.py             ← engine simulazione OHLCV
│   │   │   ├── ranker.py                 ← formula score + filtri
│   │   │   ├── ai_evaluator.py           ← LLM → score qualitativo
│   │   │   ├── execution_engine.py       ← loop 5min asincrono
│   │   │   ├── risk_manager.py           ← check pre-ordine
│   │   │   ├── market_data.py            ← fetch OHLCV Binance + cache Supabase
│   │   │   └── indicators.py             ← EMA, RSI, BB, segnali
│   │   │
│   │   ├── db/
│   │   │   └── supabase_client.py        ← singleton client supabase-py
│   │   │
│   │   ├── schemas/                      ← Pydantic request/response
│   │   │   ├── strategy.py
│   │   │   ├── trade.py
│   │   │   └── dashboard.py
│   │   │
│   │   └── scheduler/
│   │       ├── jobs.py                   ← APScheduler: daily regen, 5min loop
│   │       └── runner.py
│   │
│   ├── tests/
│   │   ├── conftest.py                   ← fixtures: mock supabase, sample OHLCV
│   │   ├── unit/
│   │   │   ├── test_indicators.py
│   │   │   ├── test_backtester.py
│   │   │   ├── test_generator.py
│   │   │   ├── test_ranker.py
│   │   │   └── test_risk_manager.py
│   │   ├── integration/
│   │   │   ├── test_api_strategies.py
│   │   │   ├── test_api_dashboard.py
│   │   │   ├── test_api_logs.py
│   │   │   └── test_pipeline.py
│   │   └── e2e/
│   │       └── test_execution_engine.py
│   │
│   ├── .env                              ← NON committare
│   ├── .env.example
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
│
├── frontend/                             ← Angular app
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/
│   │   │   │   ├── services/
│   │   │   │   │   ├── auth.service.ts
│   │   │   │   │   ├── api.service.ts
│   │   │   │   │   ├── strategy.service.ts
│   │   │   │   │   ├── dashboard.service.ts
│   │   │   │   │   ├── ws.service.ts
│   │   │   │   │   └── log.service.ts
│   │   │   │   ├── guards/
│   │   │   │   │   └── auth.guard.ts
│   │   │   │   ├── interceptors/
│   │   │   │   │   └── auth.interceptor.ts
│   │   │   │   └── models/
│   │   │   │       ├── strategy.model.ts
│   │   │   │       ├── trade.model.ts
│   │   │   │       └── dashboard.model.ts
│   │   │   │
│   │   │   ├── shared/
│   │   │   │   ├── components/
│   │   │   │   │   ├── stat-card/
│   │   │   │   │   ├── badge-status/
│   │   │   │   │   ├── price-ticker/
│   │   │   │   │   ├── confirm-modal/
│   │   │   │   │   └── chart-widget/
│   │   │   │   └── pipes/
│   │   │   │       ├── currency-format.pipe.ts
│   │   │   │       └── time-ago.pipe.ts
│   │   │   │
│   │   │   ├── layout/
│   │   │   │   ├── sidebar/
│   │   │   │   ├── topbar/
│   │   │   │   └── app-shell/
│   │   │   │
│   │   │   └── pages/
│   │   │       ├── login/
│   │   │       ├── dashboard/
│   │   │       ├── strategies/
│   │   │       │   └── strategy-detail-modal/
│   │   │       ├── active-trade/
│   │   │       └── logs/
│   │   │
│   │   ├── assets/
│   │   │   ├── icons/
│   │   │   │   ├── logo.svg
│   │   │   │   ├── icon-buy.svg
│   │   │   │   ├── icon-sell.svg
│   │   │   │   └── icon-bot.svg
│   │   │   └── images/
│   │   │
│   │   ├── environments/
│   │   │   ├── environment.ts            ← dev
│   │   │   └── environment.prod.ts       ← prod
│   │   │
│   │   └── styles/
│   │       ├── _variables.scss           ← tutti i design tokens
│   │       ├── _typography.scss
│   │       ├── _animations.scss
│   │       ├── _components.scss
│   │       └── global.scss
│   │
│   ├── angular.json
│   ├── tsconfig.json
│   ├── jest.config.ts                    ← test runner Angular (Jest)
│   └── package.json
│
├── docker-compose.yml                    ← backend + Supabase local
├── .gitignore
└── README.md
```

---

## 🗄️ Schema Supabase — Migrations SQL

```sql
-- migrations/20240101000001_strategies.sql
CREATE TABLE strategies (
  id            TEXT PRIMARY KEY,           -- es. "ema_02341"
  title         TEXT NOT NULL,
  template      TEXT NOT NULL,              -- 'trend_ema' | 'mean_reversion_rsi' | 'breakout_bb'
  pair          TEXT NOT NULL DEFAULT 'BTC/USDT',
  timeframe     TEXT NOT NULL DEFAULT '5m',
  params        JSONB NOT NULL,             -- parametri specifici del template
  rules         JSONB NOT NULL,             -- entry/exit/stop_loss/take_profit
  risk          JSONB NOT NULL,             -- max_position_eur, max_daily_loss, ecc.
  targets       JSONB NOT NULL,             -- horizon_days, expected_return_pct, ecc.
  backtest      JSONB,                      -- BacktestResult serializzato
  equity_curve  FLOAT[] DEFAULT '{}',       -- array float per grafico
  score         FLOAT,
  ai_score      FLOAT,
  ai_risk       TEXT,                       -- 'LOW' | 'MEDIUM' | 'HIGH'
  ai_note       TEXT,
  ai_strengths  TEXT[],
  ai_warnings   TEXT[],
  status        TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING|APPROVED|ACTIVE|REJECTED|EXPIRED
  version       INT  NOT NULL DEFAULT 1,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

-- migrations/20240101000002_trades.sql
CREATE TABLE trades (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id   TEXT REFERENCES strategies(id),
  action        TEXT NOT NULL,              -- 'BUY' | 'SELL'
  pair          TEXT NOT NULL,
  price         FLOAT NOT NULL,
  quantity      FLOAT NOT NULL,
  cost_eur      FLOAT,
  fee_eur       FLOAT,
  pnl_pct       FLOAT,                      -- popolato alla chiusura
  paper         BOOLEAN DEFAULT TRUE,
  executed_at   TIMESTAMPTZ DEFAULT now()
);

-- migrations/20240101000003_logs.sql
CREATE TABLE operation_logs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id   TEXT,
  action        TEXT NOT NULL,              -- 'BUY'|'SELL'|'SKIP'|'BLOCK'|'ERROR'
  price         FLOAT,
  quantity      FLOAT,
  reason        TEXT,
  ai_score      FLOAT,
  metadata      JSONB DEFAULT '{}',
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_logs_created_at   ON operation_logs(created_at DESC);
CREATE INDEX idx_logs_strategy_id  ON operation_logs(strategy_id);
CREATE INDEX idx_logs_action       ON operation_logs(action);

-- migrations/20240101000004_ohlcv_cache.sql
CREATE TABLE ohlcv_cache (
  pair        TEXT NOT NULL,
  timeframe   TEXT NOT NULL,
  ts          TIMESTAMPTZ NOT NULL,
  open        FLOAT NOT NULL,
  high        FLOAT NOT NULL,
  low         FLOAT NOT NULL,
  close       FLOAT NOT NULL,
  volume      FLOAT NOT NULL,
  PRIMARY KEY (pair, timeframe, ts)
);

CREATE INDEX idx_ohlcv_pair_tf_ts ON ohlcv_cache(pair, timeframe, ts DESC);
```

---

## 🔑 Variabili d'Ambiente (`.env`)

```bash
# =============================================
# SUPABASE
# =============================================
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...                # chiave pubblica (frontend safe)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...        # chiave privata (solo backend)
# Per query SQL dirette (opzionale, con pooler Supabase)
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

# =============================================
# EXCHANGE — Binance
# =============================================
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
BINANCE_TESTNET=true                         # false solo in produzione

# =============================================
# AUTH (singolo utente, password via env)
# =============================================
APP_PASSWORD=changeme_strong_password
JWT_SECRET=genera_con_openssl_rand_hex_32
JWT_EXPIRE_MINUTES=1440                      # 24h

# =============================================
# AI EVALUATOR — OpenRouter cascade
# =============================================
OPENROUTER_API_KEY=sk-or-...

# Cascade ordinato: il sistema tenta i modelli in sequenza.
# I primi 4 sono free (rate limit 20 req/min, 200 req/day su OpenRouter).
# Il fallback finale è a pagamento ma garantito.
#
# Tier 1 — free, reasoning forte
AI_MODEL_1=deepseek/deepseek-r1:free
# Tier 2 — free, 70B molto affidabile
AI_MODEL_2=meta-llama/llama-3.3-70b-instruct:free
# Tier 3 — free, 120B NVIDIA ibrido Mamba-Transformer, 262K context
AI_MODEL_3=nvidia/nemotron-3-super:free
# Tier 4 — free, Mistral compatto e veloce
AI_MODEL_4=mistralai/mistral-small-3.1:free
# Tier 5 — FALLBACK PAGANTE garantito (Haiku)
AI_MODEL_FALLBACK=anthropic/claude-haiku-4-5

# Timeout per tentativo (secondi). Se scade → tier successivo.
AI_CASCADE_TIMEOUT=12
# Max retry per tier prima di scendere al successivo
AI_CASCADE_MAX_RETRIES=2

# =============================================
# ENGINE
# =============================================
EXECUTION_INTERVAL_SECONDS=300              # 5 min
DAILY_REGEN_HOUR=3                          # ora UTC rigenerazione giornaliera
MAX_OPEN_TRADES=1
MAX_DAILY_LOSS_EUR=15
PAPER_TRADING=true                          # SEMPRE true finché non in prod

# =============================================
# BACKEND
# =============================================
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:4200,https://synthtrade.yourdomain.com
LOG_LEVEL=INFO

# =============================================
# FRONTEND — environments/environment.ts
# =============================================
# apiBaseUrl: 'http://localhost:8000'
# wsUrl: 'ws://localhost:8000/ws'
```

---

## 🧮 Algoritmi Core — Prima Stesura

### Setup Supabase Client (`db/supabase_client.py`)

```python
from supabase import create_client, Client
from functools import lru_cache
from app.config import settings

@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Singleton Supabase client (usa service_role per operazioni backend)."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
```

---

### 1. `strategy_generator.py`

```python
from itertools import product
from dataclasses import dataclass
from typing import Generator

@dataclass
class StrategyParams:
    template: str
    pair: str
    timeframe: str
    params: dict

TEMPLATES: dict[str, dict] = {
    "trend_ema": {
        "ema_fast":    [10, 20, 30],
        "ema_slow":    [50, 100, 200],
        "stop_loss":   [0.02, 0.03, 0.05],
        "take_profit": [0.04, 0.06, 0.09],
    },
    "mean_reversion_rsi": {
        "rsi_period":    [14, 21],
        "rsi_oversold":  [25, 30, 35],
        "rsi_overbought":[65, 70, 75],
        "stop_loss":     [0.02, 0.03],
        "take_profit":   [0.04, 0.06],
    },
    "breakout_bb": {
        "bb_period":   [20, 30],
        "bb_std":      [2.0, 2.5],
        "stop_loss":   [0.02, 0.03],
        "take_profit": [0.05, 0.08],
    },
}

def generate_all_variants(
    pairs: list[str] = ["BTC/USDT"],
    timeframes: list[str] = ["5m", "15m"],
) -> Generator[StrategyParams, None, None]:
    """Prodotto cartesiano: tipicamente 200–800 strategie candidate."""
    for template_name, param_grid in TEMPLATES.items():
        keys = list(param_grid.keys())
        for pair, timeframe, combo in product(pairs, timeframes, product(*param_grid.values())):
            yield StrategyParams(
                template=template_name,
                pair=pair,
                timeframe=timeframe,
                params=dict(zip(keys, combo)),
            )

def build_strategy_id(s: StrategyParams) -> str:
    """ID deterministico dai parametri — evita duplicati nel DB."""
    key = f"{s.template}_{s.pair}_{s.timeframe}_{sorted(s.params.items())}"
    return f"{s.template[:4]}_{abs(hash(key)) % 100000:05d}"
```

---

### 2. `indicators.py`

```python
import pandas as pd

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))

def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0):
    mid   = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    return mid - std * sigma, mid, mid + std * sigma

# === Funzioni segnale per template ===

def signal_ema_crossover(df: pd.DataFrame, fast: int, slow: int) -> pd.Series:
    ema_f = ema(df["close"], fast)
    ema_s = ema(df["close"], slow)
    # shift(1) → evita look-ahead bias
    sig = pd.Series(0, index=df.index)
    sig[ema_f.shift(1) > ema_s.shift(1)] = 1
    sig[ema_f.shift(1) < ema_s.shift(1)] = -1
    return sig

def signal_rsi_reversion(df: pd.DataFrame, period: int, oversold: int, overbought: int) -> pd.Series:
    r = rsi(df["close"], period).shift(1)
    sig = pd.Series(0, index=df.index)
    sig[r < oversold]  = 1
    sig[r > overbought] = -1
    return sig

def signal_breakout_bb(df: pd.DataFrame, period: int, std: float) -> pd.Series:
    lower, _, upper = bollinger_bands(df["close"], period, std)
    prev_close = df["close"].shift(1)
    sig = pd.Series(0, index=df.index)
    sig[prev_close > upper.shift(1)] = 1
    sig[prev_close < lower.shift(1)] = -1
    return sig
```

---

### 3. `backtester.py`

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

FEE_PCT  = 0.001   # 0.1% Binance taker
SLIPPAGE = 0.0007  # 0.07% slippage medio

@dataclass
class BacktestResult:
    pnl_pct:         float
    win_rate:        float
    sharpe:          float
    max_drawdown_pct: float
    num_trades:      int
    equity_curve:    list[float] = field(default_factory=list)

def run_backtest(
    ohlcv: pd.DataFrame,
    signal_fn: callable,
    initial_capital: float = 1000.0,
) -> BacktestResult:
    signals = signal_fn(ohlcv)
    capital, position, entry_price = initial_capital, 0.0, 0.0
    equity_curve = [capital]
    trades: list[float] = []

    for i in range(1, len(ohlcv)):
        price  = ohlcv["close"].iloc[i]
        signal = signals.iloc[i]

        if signal == 1 and position == 0:
            exec_price = price * (1 + SLIPPAGE)
            position   = capital * (1 - FEE_PCT) / exec_price
            capital    = 0.0
            entry_price = exec_price

        elif signal == -1 and position > 0:
            exec_price = price * (1 - SLIPPAGE)
            proceeds   = position * exec_price * (1 - FEE_PCT)
            trades.append((exec_price - entry_price) / entry_price)
            capital, position = proceeds, 0.0

        current = capital + position * price
        equity_curve.append(current)

    if position > 0:
        final = ohlcv["close"].iloc[-1] * (1 - SLIPPAGE) * (1 - FEE_PCT)
        equity_curve[-1] = position * final

    final_equity = equity_curve[-1]
    pnl_pct      = (final_equity - initial_capital) / initial_capital * 100
    win_rate     = sum(1 for t in trades if t > 0) / len(trades) if trades else 0.0

    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe  = (returns.mean() / returns.std() * np.sqrt(252 * 288)
               if returns.std() > 0 else 0.0)

    eq      = pd.Series(equity_curve)
    dd      = (eq - eq.cummax()) / eq.cummax()
    max_dd  = abs(dd.min()) * 100

    return BacktestResult(
        pnl_pct=round(pnl_pct, 4),
        win_rate=round(win_rate, 4),
        sharpe=round(float(sharpe), 4),
        max_drawdown_pct=round(max_dd, 4),
        num_trades=len(trades),
        equity_curve=equity_curve,
    )
```

---

### 4. `ranker.py`

```python
from dataclasses import dataclass
from typing import Optional
from app.core.backtester import BacktestResult

@dataclass
class RankConfig:
    min_trades:   int   = 30
    min_sharpe:   float = 0.5
    max_drawdown: float = 15.0    # %
    min_pnl:      float = 2.0     # %
    w_pnl:        float = 0.40
    w_sharpe:     float = 0.30
    w_winrate:    float = 0.20
    w_drawdown:   float = 0.30

def compute_score(result: BacktestResult, cfg: RankConfig = RankConfig()) -> Optional[float]:
    """None = strategia scartata dai filtri hard."""
    if (result.num_trades < cfg.min_trades or
        result.max_drawdown_pct > cfg.max_drawdown or
        result.sharpe < cfg.min_sharpe or
        result.pnl_pct < cfg.min_pnl):
        return None

    pnl_n   = min(result.pnl_pct / 20.0, 1.0)
    sha_n   = min(result.sharpe / 3.0, 1.0)
    wr_n    = result.win_rate
    dd_pen  = result.max_drawdown_pct / 100.0

    score = (cfg.w_pnl * pnl_n + cfg.w_sharpe * sha_n +
             cfg.w_winrate * wr_n - cfg.w_drawdown * dd_pen)
    return round(max(score, 0.0), 4)

def rank_strategies(strategies: list[dict]) -> list[dict]:
    return sorted(
        [s for s in strategies if s.get("score") is not None],
        key=lambda s: s["score"], reverse=True
    )
```

---

### 5. `market_data.py` — Con cache Supabase

```python
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from app.db.supabase_client import get_supabase

exchange = ccxt.binance({"enableRateLimit": True})

def fetch_ohlcv(pair: str, timeframe: str, days: int = 180) -> pd.DataFrame:
    """Scarica OHLCV da Supabase cache; integra da Binance solo il delta mancante."""
    db = get_supabase()
    since = datetime.utcnow() - timedelta(days=days)

    # 1. Leggi cache esistente
    cached = (db.table("ohlcv_cache")
               .select("*")
               .eq("pair", pair).eq("timeframe", timeframe)
               .gte("ts", since.isoformat())
               .order("ts")
               .execute())

    cached_df = _to_df(cached.data) if cached.data else pd.DataFrame()

    # 2. Calcola gap da colmare
    if not cached_df.empty:
        last_ts = cached_df.index[-1]
        fetch_since = int(last_ts.timestamp() * 1000) + 1
    else:
        fetch_since = int(since.timestamp() * 1000)

    # 3. Fetch Binance (paginato)
    new_candles = _fetch_binance_paginated(pair, timeframe, fetch_since)

    # 4. Upsert nuovi dati in cache
    if new_candles:
        rows = [{"pair": pair, "timeframe": timeframe, "ts": c[0], "open": c[1],
                 "high": c[2], "low": c[3], "close": c[4], "volume": c[5]}
                for c in new_candles]
        db.table("ohlcv_cache").upsert(rows).execute()

    new_df = _candles_to_df(new_candles) if new_candles else pd.DataFrame()
    return pd.concat([cached_df, new_df]).drop_duplicates()

def _fetch_binance_paginated(pair: str, timeframe: str, since_ms: int) -> list:
    all_candles = []
    while True:
        batch = exchange.fetch_ohlcv(pair, timeframe, since=since_ms, limit=1000)
        if not batch:
            break
        all_candles.extend(batch)
        since_ms = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    return all_candles

def _to_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["ts"])
    return df.set_index("timestamp")[["open","high","low","close","volume"]].astype(float)

def _candles_to_df(candles: list) -> pd.DataFrame:
    df = pd.DataFrame(candles, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df.set_index("timestamp")[["open","high","low","close","volume"]].astype(float)

def get_current_price(pair: str) -> float:
    return float(exchange.fetch_ticker(pair)["last"])
```

---

### 6. `risk_manager.py`

```python
from datetime import date
from app.db.supabase_client import get_supabase

class RiskManager:
    def __init__(self, max_position_eur: float, max_daily_loss: float, max_open_trades: int):
        self.max_position_eur = max_position_eur
        self.max_daily_loss   = max_daily_loss
        self.max_open_trades  = max_open_trades

    def check(self, signal: int, strategy: dict, account: dict) -> tuple[bool, str]:
        balance = account["free"].get("USDT", 0)

        if signal == 1 and balance < 10:
            return False, "Insufficient balance"

        open_count = self._count_open_trades()
        if signal == 1 and open_count >= self.max_open_trades:
            return False, f"Max open trades reached ({self.max_open_trades})"

        daily_pnl = self._daily_pnl()
        if daily_pnl < -self.max_daily_loss:
            return False, f"Daily loss limit hit: {daily_pnl:.2f}€"

        return True, "OK"

    def compute_size(self, strategy: dict, account: dict) -> float:
        from app.core.market_data import get_current_price
        available = account["free"].get("USDT", 0)
        position_eur = min(strategy["risk"]["max_position_eur"], available * 0.95)
        price = get_current_price(strategy["pair"])
        return round(position_eur / price, 6)

    def _daily_pnl(self) -> float:
        db = get_supabase()
        today = date.today().isoformat()
        res = (db.table("trades")
                 .select("pnl_pct, cost_eur")
                 .gte("executed_at", today)
                 .execute())
        return sum((r["pnl_pct"] or 0) * (r["cost_eur"] or 0) for r in res.data)

    def _count_open_trades(self) -> int:
        db = get_supabase()
        res = db.table("trades").select("id", count="exact").is_("pnl_pct", "null").execute()
        return res.count or 0
```

---

### 7. `execution_engine.py`

```python
import asyncio
import logging
from datetime import datetime
from app.core.market_data import fetch_ohlcv, get_current_price
from app.core.indicators import signal_ema_crossover
from app.db.supabase_client import get_supabase
from app.config import settings

logger = logging.getLogger("synthtrade.engine")

class ExecutionEngine:
    def __init__(self, exchange, risk_manager):
        self.exchange     = exchange
        self.risk_manager = risk_manager
        self.running      = False

    async def start(self):
        self.running = True
        logger.info("⚡ SynthTrade engine started")
        while self.running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Engine error: {e}", exc_info=True)
            await asyncio.sleep(settings.EXECUTION_INTERVAL_SECONDS)

    async def stop(self):
        self.running = False
        logger.info("Engine stopped")

    async def _tick(self):
        db = get_supabase()
        res = db.table("strategies").select("*").eq("status", "ACTIVE").limit(1).execute()
        if not res.data:
            return

        strategy = res.data[0]
        ohlcv    = fetch_ohlcv(strategy["pair"], strategy["timeframe"], days=2)
        signal   = self._compute_signal(ohlcv, strategy)

        if signal == 0:
            return

        account = self.exchange.fetch_balance()
        ok, reason = self.risk_manager.check(signal, strategy, account)

        if not ok:
            logger.warning(f"Risk block [{strategy['id']}]: {reason}")
            self._log_op(strategy["id"], "BLOCK", reason=reason)
            return

        price = await self._execute(signal, strategy, account)
        self._log_op(
            strategy["id"],
            "BUY" if signal == 1 else "SELL",
            price=price,
            quantity=self.risk_manager.compute_size(strategy, account),
            reason=f"signal={signal}",
            ai_score=strategy.get("ai_score"),
        )

    def _compute_signal(self, ohlcv, strategy: dict) -> int:
        p = strategy["params"]
        match strategy["template"]:
            case "trend_ema":
                sig = signal_ema_crossover(ohlcv, p["ema_fast"], p["ema_slow"])
            case _:
                sig = signal_ema_crossover(ohlcv, 20, 50)
        return int(sig.iloc[-1])

    async def _execute(self, signal: int, strategy: dict, account: dict) -> float:
        side = "buy" if signal == 1 else "sell"
        size = self.risk_manager.compute_size(strategy, account)
        price = get_current_price(strategy["pair"])

        if settings.PAPER_TRADING:
            logger.info(f"[PAPER] {side.upper()} {size} {strategy['pair']} @ {price}")
            return price

        order = self.exchange.create_market_order(strategy["pair"], side, size)
        return float(order["price"])

    def _log_op(self, strategy_id: str, action: str, **kwargs):
        db = get_supabase()
        db.table("operation_logs").insert({
            "strategy_id": strategy_id,
            "action": action,
            "created_at": datetime.utcnow().isoformat(),
            **kwargs,
        }).execute()
```

---

### 8. `ai_evaluator.py` — Cascade OpenRouter

Il modulo tenta i modelli in sequenza: i primi 4 sono **free**, il quinto è il fallback pagante garantito (Haiku). Ogni tier ha timeout e retry indipendenti. Il risultato è sempre validato con Pydantic prima di essere restituito.

```
┌──────────────────────────────────────────────────────────────────────┐
│                     CASCADE AI EVALUATOR                             │
│                                                                      │
│  Tier 1  deepseek/deepseek-r1:free         ← reasoning forte, free  │
│     ↓ timeout / rate limit / error                                   │
│  Tier 2  meta-llama/llama-3.3-70b:free     ← solido, affidabile     │
│     ↓                                                                │
│  Tier 3  nvidia/nemotron-3-super:free      ← 120B, 262K ctx         │
│     ↓                                                                │
│  Tier 4  mistralai/mistral-small-3.1:free  ← compatto, veloce       │
│     ↓                                                                │
│  Tier 5  anthropic/claude-haiku-4-5        ← PAID fallback garantito│
└──────────────────────────────────────────────────────────────────────┘
```

```python
# app/core/ai_evaluator.py
import httpx
import json
import logging
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.config import settings

logger = logging.getLogger("synthtrade.ai")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Modelli in ordine di preferenza ───────────────────────────────────
CASCADE_MODELS: list[str] = [
    "deepseek/deepseek-r1:free",          # Tier 1 — reasoning forte
    "meta-llama/llama-3.3-70b-instruct:free",  # Tier 2 — 70B affidabile
    "nvidia/nemotron-3-super:free",        # Tier 3 — 120B, 262K ctx
    "mistralai/mistral-small-3.1:free",    # Tier 4 — veloce, leggero
    "anthropic/claude-haiku-4-5",          # Tier 5 — fallback PAID
]

SYSTEM_PROMPT = """
Sei un analista quantitativo specializzato in crypto trading algoritmico.
Ricevi una strategia con i risultati di backtest e il contesto di mercato attuale.
Rispondi SOLO con un oggetto JSON valido, senza markdown né testo extra:
{
  "score": <float 0.0–1.0>,
  "risk": <"LOW"|"MEDIUM"|"HIGH">,
  "note": <string max 200 char, in italiano>,
  "strengths": [<string>, ...],
  "warnings": [<string>, ...]
}
"""

# ── Schema di validazione output ──────────────────────────────────────
class EvalResult(BaseModel):
    score:     float     = Field(ge=0.0, le=1.0)
    risk:      str       = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    note:      str       = Field(max_length=200)
    strengths: list[str] = Field(default_factory=list)
    warnings:  list[str] = Field(default_factory=list)
    model_used: Optional[str] = None   # tracciabilità del tier usato

    @field_validator("score")
    @classmethod
    def round_score(cls, v: float) -> float:
        return round(v, 4)

# ── Chiamata singola a OpenRouter ─────────────────────────────────────
async def _call_model(
    model: str,
    user_msg: str,
    timeout: float,
) -> Optional[EvalResult]:
    """
    Tenta una chiamata a `model` su OpenRouter.
    Restituisce EvalResult se successo, None se qualsiasi errore.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization":  f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type":   "application/json",
                    "HTTP-Referer":   "https://synthtrade.app",
                    "X-Title":        "SynthTrade AI Evaluator",
                },
                json={
                    "model":       model,
                    "max_tokens":  512,
                    "temperature": 0.1,   # output deterministico per JSON
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": user_msg},
                    ],
                },
            )

        if r.status_code == 429:
            logger.warning(f"[cascade] Rate limit on {model}")
            return None
        if r.status_code >= 500:
            logger.warning(f"[cascade] Server error {r.status_code} on {model}")
            return None

        r.raise_for_status()

        raw_text = r.json()["choices"][0]["message"]["content"]
        # Strip eventuale ```json ... ``` che alcuni modelli aggiungono
        clean = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
        data  = json.loads(clean)
        result = EvalResult(**data, model_used=model)
        logger.info(f"[cascade] ✓ {model} → score={result.score} risk={result.risk}")
        return result

    except (httpx.TimeoutException, httpx.ConnectError):
        logger.warning(f"[cascade] Timeout/connection error on {model}")
        return None
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[cascade] Invalid JSON from {model}: {e}")
        return None
    except Exception as e:
        logger.error(f"[cascade] Unexpected error on {model}: {e}")
        return None

# ── Entry point pubblico ──────────────────────────────────────────────
async def evaluate_strategy(
    strategy: dict,
    market_context: dict,
    models: list[str] = CASCADE_MODELS,
) -> EvalResult:
    """
    Esegue la valutazione AI con cascade di modelli.
    Tenta ogni modello in ordine; se tutti falliscono, lancia RuntimeError.

    Args:
        strategy:       dizionario strategia con backtest incluso
        market_context: dati di contesto mercato (trend, volatilità, ecc.)
        models:         lista ordinata di modelli (override per test)

    Returns:
        EvalResult con score, risk, note, strengths, warnings e model_used
    """
    payload = json.dumps(
        {"strategy": strategy, "market_context": market_context},
        ensure_ascii=False,
    )

    for i, model in enumerate(models):
        is_fallback = (i == len(models) - 1)
        timeout = 30.0 if is_fallback else settings.AI_CASCADE_TIMEOUT

        logger.info(f"[cascade] Trying tier {i+1}/{len(models)}: {model}")

        for attempt in range(settings.AI_CASCADE_MAX_RETRIES):
            result = await _call_model(model, payload, timeout)
            if result:
                return result
            if attempt < settings.AI_CASCADE_MAX_RETRIES - 1:
                logger.debug(f"[cascade] Retry {attempt+1} on {model}")

    raise RuntimeError(
        f"AI cascade exhausted all {len(models)} models without a valid response. "
        "Check OpenRouter API key and rate limits."
    )

# ── Contesto mercato helper ───────────────────────────────────────────
def build_market_context(ohlcv_df) -> dict:
    """Costruisce il contesto di mercato da passare all'AI."""
    import numpy as np
    close  = ohlcv_df["close"]
    return {
        "pair":              "BTC/USDT",
        "last_price":        float(close.iloc[-1]),
        "change_7d_pct":     float((close.iloc[-1] / close.iloc[-288*7] - 1) * 100),
        "volatility_30d":    float(close.pct_change().rolling(288*30).std().iloc[-1] * 100),
        "trend":             "UP" if close.iloc[-1] > close.iloc[-288] else "DOWN",
    }
```

---

## ✅ Task List TDD — Implementazione Completa

> **Metodologia:** ogni feature segue il ciclo 🔴 **Red** → 🟢 **Green** → 🔵 **Refactor**.
> I task sono ordinati: prima scrivi il test (che fallisce), poi implementa, poi pulisci.
> Backend: **pytest + pytest-asyncio**. Frontend: **Jest + Angular Testing Library**.

---

### 🔵 Fase 0 — Setup & Infrastruttura (1–2 giorni)

#### Monorepo & Tooling
- [ ] Creare struttura cartelle `synthtrade/` con `backend/`, `frontend/`, `supabase/`
- [ ] Inizializzare Git con `.gitignore` (escludere `.env`, `__pycache__`, `node_modules`, `dist`)
- [ ] Creare `README.md` con istruzioni setup locale

#### Backend Bootstrap
- [ ] Installare dipendenze: `fastapi uvicorn supabase-py pydantic-settings ccxt pandas numpy httpx pytest pytest-asyncio`
- [ ] Creare `config.py` con `Settings` via `pydantic-settings`
- [ ] Creare `main.py` con lifespan, CORS, router placeholder
- [ ] 🔴 **Test:** `test_main.py` → `GET /health` restituisce `{"status": "ok"}`
- [ ] 🟢 Implementare route `/health`
- [ ] Creare `pytest.ini` con `asyncio_mode = auto`
- [ ] Creare `conftest.py` con fixture `mock_supabase` (mock del client)

#### Supabase Setup
- [ ] Installare Supabase CLI: `npm install -g supabase`
- [ ] `supabase init` nella root
- [ ] Creare le 4 migration SQL (strategies, trades, logs, ohlcv_cache)
- [ ] `supabase start` per istanza locale
- [ ] Testare connessione con `supabase_client.py`
- [ ] Creare `seed.sql` con 3 strategie di esempio in stato PENDING

#### Frontend Bootstrap
- [ ] `ng new synthtrade-ui --standalone --routing --style=scss`
- [ ] Installare: `lightweight-charts jest @angular/cdk`
- [ ] Configurare Jest al posto di Karma: `jest.config.ts`
- [ ] Creare `_variables.scss` con design tokens completi
- [ ] Importare font Google (Chakra Petch, DM Sans, JetBrains Mono) in `global.scss`
- [ ] 🔴 **Test:** `app.component.spec.ts` → il componente root esiste e ha titolo 'SynthTrade'
- [ ] 🟢 Aggiornare `AppComponent` con titolo corretto

#### Docker
- [ ] `docker-compose.yml` per backend (porta 8000)
- [ ] Verificare `supabase start` + backend up insieme

---

### 🟡 Fase 1 — Core Engine (6–9 giorni)

#### Indicatori tecnici
- [ ] 🔴 **Test `test_indicators.py`:**
  - `ema(series, 20)` su serie nota restituisce valori corretti agli ultimi 3 indici
  - `rsi(series, 14)` è sempre in range [0, 100]
  - `bollinger_bands` → lower < mid < upper per ogni candela
  - `signal_ema_crossover` non produce look-ahead (shift verificato)
- [ ] 🟢 Implementare `indicators.py` (ema, rsi, bollinger_bands + 3 signal fn)
- [ ] 🔵 Refactor: estrarre costante `LOOKBACK_PERIODS` per warm-up minimo

#### Strategy Generator
- [ ] 🔴 **Test `test_generator.py`:**
  - `generate_all_variants()` produce almeno 200 strategie
  - Ogni `StrategyParams` ha `template`, `pair`, `timeframe`, `params` non vuoti
  - `build_strategy_id` è deterministico: stesso input → stesso ID
  - Nessun duplicato di ID su 500 varianti generate
- [ ] 🟢 Implementare `strategy_generator.py`
- [ ] 🔵 Refactor: rendere `TEMPLATES` configurabile via JSON file

#### Backtester
- [ ] 🔴 **Test `test_backtester.py`:**
  - Con `signal_fn` sempre-buy su dati crescenti → PnL > 0
  - Con `signal_fn` sempre-buy su dati decrescenti → PnL < 0
  - Fee applicate: `num_trades * 2 * FEE_PCT` riduce il PnL atteso
  - `equity_curve` ha stessa lunghezza di `ohlcv`
  - `max_drawdown_pct` ≥ 0
  - `win_rate` ∈ [0.0, 1.0]
  - Nessun look-ahead: rimuovere l'ultima candela non cambia i trade precedenti
- [ ] 🟢 Implementare `backtester.py` con `run_backtest()`
- [ ] 🔵 Refactor: aggiungere `StopLossManager` separato

#### Ranker
- [ ] 🔴 **Test `test_ranker.py`:**
  - Strategia con `num_trades < 30` → `score = None`
  - Strategia con `max_drawdown > 15%` → `score = None`
  - Strategia con `sharpe < 0.5` → `score = None`
  - Strategia valida → score ∈ [0.0, 1.0]
  - `rank_strategies([...])` è ordinato decrescente per score
  - Strategie con `score = None` non compaiono nel risultato
- [ ] 🟢 Implementare `ranker.py`
- [ ] 🔵 Refactor: `RankConfig` leggibile da `.env`

#### Market Data + Cache Supabase
- [ ] 🔴 **Test `test_market_data.py`:**
  - Con Supabase mock vuoto: fa fetch Binance e ritorna DataFrame
  - Con cache parziale: fa fetch solo del delta mancante (mock Binance chiamato 1 volta)
  - DataFrame output ha colonne `open, high, low, close, volume`
  - Nessun duplicato di timestamp nell'output
- [ ] 🟢 Implementare `market_data.py` con cache Supabase
- [ ] 🔵 Refactor: separare `_fetch_binance_paginated` in modulo `exchange.py`

#### Pipeline Batch
- [ ] 🔴 **Test `test_pipeline.py` (integration):**
  - Su 10 strategie mock: il pipeline salva in Supabase solo quelle con score > 0
  - Nessun errore su batch di 50 strategie reali
- [ ] 🟢 Implementare `run_pipeline.py`: genera → backtest → rank → upsert Supabase
- [ ] 🔵 Refactor: aggiungere progress logging, gestione eccezioni per strategia

---

### 🟠 Fase 2 — Backend API (4–6 giorni)

#### Auth
- [ ] 🔴 **Test `test_api_auth.py`:**
  - `POST /auth/login` con password corretta → `200` + JWT token
  - `POST /auth/login` con password errata → `401`
  - `GET /strategies` senza token → `401`
  - Token scaduto → `401`
- [ ] 🟢 Implementare `api/auth.py` con JWT (python-jose)
- [ ] 🟢 Implementare `dependencies.py` → `get_current_user`
- [ ] 🔵 Refactor: estrarre `create_access_token()` in `core/auth_utils.py`

#### Strategies API
- [ ] 🔴 **Test `test_api_strategies.py`:**
  - `GET /strategies` → lista con `id, title, score, status`
  - `GET /strategies?status=PENDING` → solo PENDING
  - `GET /strategies/{id}` → include `equity_curve`, `params`, `ai_note`
  - `GET /strategies/{id_inesistente}` → `404`
  - `POST /strategies/{id}/approve` → status diventa `APPROVED`
  - `POST /strategies/{id}/approve` su strategia non PENDING → `409`
  - `POST /strategies/{id}/reject` → status diventa `REJECTED`
- [ ] 🟢 Implementare `api/strategies.py` con tutte le route
- [ ] 🔵 Refactor: estrarre `StrategyRepository` in `db/repositories/strategy_repo.py`

#### Dashboard API
- [ ] 🔴 **Test `test_api_dashboard.py`:**
  - `GET /dashboard` → risposta include `balance, pnl_today, active_strategy, engine_status`
  - `GET /dashboard/equity-history` → lista di `{ts, value}` ordinata crescente
  - Con nessuna trade oggi → `pnl_today = 0`
- [ ] 🟢 Implementare `api/dashboard.py`
- [ ] 🔵 Refactor: cacheare `balance` per 30s (evita chiamate Binance ridondanti)

#### Logs API
- [ ] 🔴 **Test `test_api_logs.py`:**
  - `GET /logs` → risposta paginata, `limit` e `offset` funzionano
  - `GET /logs?action=BUY` → solo log BUY
  - `GET /logs/export` → `Content-Type: text/csv`, header corretto
  - Ordinamento: più recente prima
- [ ] 🟢 Implementare `api/logs.py`
- [ ] 🔵 Refactor: aggiungere filtro `strategy_id` e `date_from`

#### WebSocket
- [ ] 🔴 **Test `test_ws.py`:**
  - Connessione WS senza token → chiude con code 1008
  - Connessione valida → riceve messaggio `{"type":"ping"}` entro 5s
  - Broadcast di un prezzo aggiornato → client riceve `{"type":"price","pair":"BTC/USDT","price":...}`
- [ ] 🟢 Implementare `api/ws.py` con `ConnectionManager`
- [ ] 🔵 Refactor: separare broadcast per tipo (`price`, `order`, `engine_status`)

---

### 🟢 Fase 3 — Frontend Angular (6–8 giorni)

#### Core Services
- [ ] 🔴 **Test `auth.service.spec.ts`:**
  - `login()` chiama `POST /auth/login` e salva token in localStorage
  - `logout()` rimuove il token
  - `isAuthenticated()` restituisce `true` se token valido
- [ ] 🟢 Implementare `AuthService`
- [ ] 🔴 **Test `auth.guard.spec.ts`:** route protetta redirige a `/login` se non autenticato
- [ ] 🟢 Implementare `AuthGuard`
- [ ] 🔴 **Test `auth.interceptor.spec.ts`:** ogni request include header `Authorization: Bearer <token>`
- [ ] 🟢 Implementare `AuthInterceptor`
- [ ] 🔴 **Test `strategy.service.spec.ts`:**
  - `getStrategies()` chiama `GET /strategies`
  - `approve(id)` chiama `POST /strategies/{id}/approve`
- [ ] 🟢 Implementare `StrategyService`, `DashboardService`, `LogService`
- [ ] 🔴 **Test `ws.service.spec.ts`:** `connect()` apre WebSocket, `messages$` emette messaggi ricevuti
- [ ] 🟢 Implementare `WsService` con Observable + reconnect automatico

#### Componenti Shared
- [ ] 🔴 **Test `stat-card.spec.ts`:** renderizza `label`, `value`, `delta` passati come Input
- [ ] 🟢 Implementare `StatCardComponent`
- [ ] 🔴 **Test `badge-status.spec.ts`:** classe CSS varia in base allo status (PENDING/ACTIVE/REJECTED)
- [ ] 🟢 Implementare `BadgeStatusComponent`
- [ ] 🔴 **Test `price-ticker.spec.ts`:** applica classe `up`/`down` al cambio valore
- [ ] 🟢 Implementare `PriceTickerComponent` con `ngClass` reattivo
- [ ] 🔴 **Test `currency-format.pipe.spec.ts`:** `2847.3` → `€2,847.30`
- [ ] 🟢 Implementare `CurrencyFormatPipe`
- [ ] 🔴 **Test `time-ago.pipe.spec.ts`:** timestamp 65s fa → `"1m ago"`
- [ ] 🟢 Implementare `TimeAgoPipe`

#### Layout
- [ ] 🔴 **Test `sidebar.spec.ts`:** mostra tutti e 4 i link di navigazione
- [ ] 🟢 Implementare `SidebarComponent`
- [ ] 🟢 Implementare `TopbarComponent` (live ticker via WsService)
- [ ] 🟢 Implementare `AppShellComponent` (layout principale autenticato)

#### Pagine
- [ ] 🔴 **Test `login.spec.ts`:** submit con password vuota non chiama AuthService
- [ ] 🟢 Implementare `/login`
- [ ] 🔴 **Test `dashboard.spec.ts`:** mostra loading skeleton, poi dati da DashboardService
- [ ] 🟢 Implementare `/dashboard` (stat cards + grafico lightweight-charts + ultimi log)
- [ ] 🔴 **Test `strategies.spec.ts`:**
  - Renderizza tabella con strategie da StrategyService
  - Click APPROVE chiama `strategy.approve(id)` e aggiorna lista
  - Filtro PENDING mostra solo status PENDING
- [ ] 🟢 Implementare `/strategies` con modal dettaglio
- [ ] 🔴 **Test `active-trade.spec.ts`:** bottone STOP mostra confirm modal prima di agire
- [ ] 🟢 Implementare `/active` con chart live + progress bar + emergency STOP
- [ ] 🔴 **Test `logs.spec.ts`:** CDK VirtualScroll renderizza le righe, filtro per action funziona
- [ ] 🟢 Implementare `/logs` con export CSV

#### UX & Styling
- [ ] Dark theme globale: `body { background: var(--bg-base); }`
- [ ] Animazioni SCSS: nav hover glow, price flash, strategy card active pulse
- [ ] Empty states per ogni pagina (nessuna strategia, nessun log)
- [ ] Loading skeleton per tutte le chiamate HTTP
- [ ] Test: Lighthouse score accessibilità ≥ 80 (contrasto colori)

---

### 🔴 Fase 4 — Execution Engine (3–4 giorni)

- [ ] 🔴 **Test `test_risk_manager.py`:**
  - `check()` → `False` se balance < 10
  - `check()` → `False` se daily_pnl < -max_daily_loss (mock Supabase)
  - `check()` → `False` se open_trades >= max (mock Supabase)
  - `check()` → `True` in condizioni normali
  - `compute_size()` → non supera `max_position_eur`
- [ ] 🟢 Implementare `risk_manager.py`
- [ ] 🔴 **Test `test_execution_engine.py`:**
  - Con `PAPER_TRADING=true`: nessun ordine Binance, log creato in Supabase
  - Segnale `0`: nessun ordine, nessun log
  - Risk check fallisce: log `BLOCK` creato, nessun ordine
  - Nessuna strategia ACTIVE: tick skippato silenziosamente
- [ ] 🟢 Implementare `execution_engine.py`
- [ ] 🟢 Integrare APScheduler in `scheduler/jobs.py` (5min + daily 3:00 UTC)
- [ ] 🔵 Refactor: estrarre `_compute_signal` in `SignalResolver` pluggabile

---

### 🟣 Fase 5 — AI Evaluator con Cascade OpenRouter (3–4 giorni)

#### Config & modello dati
- [ ] Aggiornare `config.py`: aggiungere `OPENROUTER_API_KEY`, `AI_CASCADE_TIMEOUT`, `AI_CASCADE_MAX_RETRIES`, lista `CASCADE_MODELS` da `.env`
- [ ] Creare schema Pydantic `EvalResult` con validatori su `score` (range 0–1) e `risk` (enum)

#### TDD — `_call_model` (unit, singolo tier)
- [ ] 🔴 **Test `test_ai_evaluator.py::test_call_model_success`:**
  mock `httpx` → risposta `200` con JSON valido → restituisce `EvalResult` con `model_used` corretto
- [ ] 🔴 **Test `test_call_model_rate_limit`:**
  mock risposta `429` → restituisce `None` (non lancia eccezione)
- [ ] 🔴 **Test `test_call_model_timeout`:**
  mock `httpx.TimeoutException` → restituisce `None`
- [ ] 🔴 **Test `test_call_model_invalid_json`:**
  mock risposta `200` con body non-JSON → restituisce `None`
- [ ] 🔴 **Test `test_call_model_json_with_markdown_fence`:**
  risposta con ` ```json ... ``` ` → viene strippata e parsata correttamente
- [ ] 🔴 **Test `test_call_model_server_error`:**
  mock risposta `503` → restituisce `None`
- [ ] 🟢 Implementare `_call_model()` con tutti i guard

#### TDD — `evaluate_strategy` (cascade orchestration)
- [ ] 🔴 **Test `test_cascade_first_tier_succeeds`:**
  tier 1 risponde → `evaluate_strategy` non chiama i tier successivi, `model_used = tier1`
- [ ] 🔴 **Test `test_cascade_fallback_after_failures`:**
  tier 1–3 restituiscono `None` → tier 4 risponde → `model_used = tier4`
- [ ] 🔴 **Test `test_cascade_retry_before_next_tier`:**
  tier 1 fallisce 2 volte → solo dopo `MAX_RETRIES` tentativi si passa al tier 2
- [ ] 🔴 **Test `test_cascade_all_fail_raises`:**
  tutti i modelli restituiscono `None` → `RuntimeError` con messaggio chiaro
- [ ] 🔴 **Test `test_cascade_paid_fallback_longer_timeout`:**
  il fallback (ultimo tier) riceve `timeout=30.0` invece di `AI_CASCADE_TIMEOUT`
- [ ] 🟢 Implementare `evaluate_strategy()` con loop cascade
- [ ] 🔵 Refactor: estrarre `_build_headers()` e `_strip_markdown_fence()` in utils

#### TDD — `EvalResult` validation
- [ ] 🔴 **Test `test_eval_result_score_out_of_range`:**
  `EvalResult(score=1.5, ...)` → `ValidationError`
- [ ] 🔴 **Test `test_eval_result_invalid_risk`:**
  `EvalResult(risk="EXTREME", ...)` → `ValidationError`
- [ ] 🔴 **Test `test_eval_result_score_rounded`:**
  `score=0.612345` → arrotondato a `0.6123`
- [ ] 🟢 Validatori già coperti da Pydantic — verificare che i test passino

#### TDD — `build_market_context`
- [ ] 🔴 **Test `test_build_market_context`:**
  DataFrame OHLCV mock → dict con chiavi `pair, last_price, change_7d_pct, volatility_30d, trend`
  e `trend = "UP"` se `close[-1] > close[-288]`
- [ ] 🟢 Implementare `build_market_context()`

#### Integrazione pipeline
- [ ] 🔴 **Test `test_pipeline_ai_integration`:**
  mock cascade che risponde sempre al tier 2 → pipeline salva `ai_score`, `ai_risk`, `model_used` in Supabase per le top 10 strategie
- [ ] 🟢 Integrare `evaluate_strategy` + `build_market_context` in `run_pipeline.py`
- [ ] 🔵 Refactor: aggiungere backoff esponenziale tra retry (`0.5s`, `1s`) senza rallentare i test (iniettare `sleep` come dipendenza)

#### Osservabilità
- [ ] Log strutturato per ogni tentativo: `tier`, `model`, `attempt`, `outcome` (`success`/`timeout`/`rate_limit`/`invalid_json`)
- [ ] Aggiungere campo `model_used` nelle strategie salvate in Supabase → visibile nel modal frontend
- [ ] Costo stimato: tier 1–4 = $0/pipeline · tier 5 Haiku = ~$0.001/chiamata → worst case $0.01/pipeline

---

### ⚫ Fase 6 — Hardening & Deploy (2–3 giorni)

- [ ] 🔴 **Test `test_rate_limiting.py`:** 1200+ chiamate Binance → exchange rispetta `enableRateLimit`
- [ ] Error handling globale su tutti i moduli core: nessuna eccezione non gestita
- [ ] Logging strutturato JSON (`python-json-logger`) con rotation giornaliera
- [ ] 🔴 **Test smoke deploy:** pipeline su testnet, verifica log in Supabase dashboard
- [ ] `Dockerfile` backend multi-stage ottimizzato (< 200MB)
- [ ] Nginx reverse proxy con HTTPS (Let's Encrypt) su VPS
- [ ] Variabili `.env` in prod via file segreto (no commit, scp o Supabase Vault)
- [ ] Configurare Supabase Row Level Security (RLS) su tutte le tabelle
- [ ] Abilitare Supabase Realtime su `operation_logs` per feed live frontend
- [ ] Smoke test post-deploy: login → approve strategia → verifica engine tick → log creato

---

## ⚠️ Note Tecniche Importanti

- **Look-ahead bias:** tutti i signal usano `.shift(1)` — i segnali di candela N usano solo dati ≤ N-1
- **Rate limit Binance:** max 1200 weight/min; ogni `fetch_ohlcv` pesa ~10 — mai fare batch parallelo senza throttle
- **Paper trading obbligatorio** per tutte le fasi 0–5; solo in Fase 6 si valuta il live
- **JWT secret:** `openssl rand -hex 32` — mai hardcoded, mai in Git
- **Supabase Service Role Key** va usata SOLO nel backend — mai esporta al frontend
- **Supabase RLS:** abilitare policy su ogni tabella per prevenire accessi non autorizzati
- **asyncio nel FastAPI:** usare `BackgroundTasks` o thread pool separato per il loop engine — non bloccare il thread ASGI
- **Supabase Realtime** può sostituire il WebSocket custom per `operation_logs` live → valutare in Fase 6
- **AI cascade — rate limit free:** OpenRouter free tier = 200 req/day per modello; con 10 eval/pipeline si è ampiamente dentro; se il batch cresce oltre 150 strategie, il tier 1 potrebbe esaurirsi — la cascade lo gestisce trasparentemente
- **AI cascade — `model_used` tracciato in Supabase:** permette di monitorare nel tempo quale tier viene effettivamente usato e di riordinare la cascade se un modello diventa inaffidabile
- **AI cascade — test isolation:** nei test, iniettare `models=["mock-model"]` in `evaluate_strategy()` per evitare chiamate HTTP reali; il parametro `models` è stato reso override proprio per questo

---

> **Prossimo step:** Fase 0 — setup monorepo + migration Supabase + `GET /health` verde. Tutto il resto si costruisce su questi mattoni.
