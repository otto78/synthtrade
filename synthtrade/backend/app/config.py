from functools import cached_property
from pathlib import Path
from typing import List
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the directory where this file is located (synthtrade/backend/app)
# Then go up one level to find the .env file in synthtrade/backend/
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'


class ScalpingSettings(BaseSettings):
    """Configurazioni specifiche per il modulo Scalping (Epic-800)."""
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    # ── Scalping — Execution ─────────────────────────────────────
    SCALPING_TRADE_VALUE: float = 10.0
    SCALPING_MAX_DAILY_LOSS: float = 50.0
    SCALPING_MAX_DRAWDOWN_PCT: float = 10.0
    SCALPING_STOP_LOSS_PCT: float = 0.3
    SCALPING_TAKE_PROFIT_PCT: float = 0.5
    SCALPING_FORCE_PAPER: bool = True
    SCALPING_FORCE_EXECUTE: bool = False

    # Old execution settings kept for compatibility
    SCALPING_EXECUTION_INTERVAL_MS: int = 500
    SCALPING_CANDLE_BUFFER_SIZE: int = 100
    SCALPING_TIMEFRAME: str = '1m'
    SCALPING_MAX_CONSECUTIVE_LOSSES: int = 5
    SCALPING_MAX_POSITION_SIZE: float = 0.01

    # ── Scalping — Signal Intelligence ──────────────────────────
    SCALPING_SIGNAL_STRENGTH_THRESHOLD: float = 15.0
    SCALPING_MIN_CONFIDENCE: float = 0.3
    SCALPING_MIN_COLLECTORS: int = 4
    SCALPING_INTEL_UPDATE_INTERVAL_SEC: int = 60

    # ── Scalping — Supervisor AI ─────────────────────────────────
    SCALPING_SUPERVISOR_INTERVAL_SEC: int = 600
    SCALPING_STRATEGY_COOLDOWN_SEC: int = 1200
    SCALPING_PARAM_UPDATE_COOLDOWN_SEC: int = 600
    SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE: int = 5
    SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS: int = 3
    
    # Old Supervisor settings kept for compatibility
    SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_DECISION: int = 3

    # ── Scalping — Collector specifici ──────────────────────────
    SCALPING_FEAR_GREED_SOURCE: str = "alternative_me"
    SCALPING_WHALE_ENABLED: bool = False
    WHALE_ALERT_API_KEY: str = ""

    # ── Scalping — Regime Detector ───────────────────────────────
    SCALPING_REGIME_TREND_THRESHOLD_PCT: float = 3.0
    SCALPING_REGIME_VOLATILE_THRESHOLD: float = 0.02

    # Opportunity Monitor
    SCALPING_OPPORTUNITY_POLL_INTERVAL_MIN: int = 5

    # Scheduler enable flags (TASK-807)
    SCALPING_SCHEDULER_INTEL_SNAPSHOT_ENABLED: bool = True
    SCALPING_SCHEDULER_FUNDING_RATE_ENABLED: bool = True
    SCALPING_SCHEDULER_SUPERVISOR_ENABLED: bool = True
    SCALPING_SCHEDULER_HEALTH_ENABLED: bool = True
    SCALPING_SCHEDULER_OPPORTUNITY_ENABLED: bool = True

    # Modalità default
    SCALPING_DEFAULT_MODE: str = 'PAPER'

    # Intelligence API Keys
    NEWSAPI_API_KEY: str = ''
    CRYPTOCOMPARE_API_KEY: str = ''
    DUNE_API_KEY: str = ''
    
    # Dune Query IDs (Public or User-owned)
    DUNE_QUERY_ID_BTC: str = '35053'   # BTC CEX Netflow (Daily)
    DUNE_QUERY_ID_ETH: str = '35055'   # ETH CEX Netflow (Daily) - Placeholder probabile


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    # Supabase
    SUPABASE_URL: str = ''
    SUPABASE_ANON_KEY: str = ''
    SUPABASE_SERVICE_ROLE_KEY: str = ''

    # Binance — Key per Testnet
    BINANCE_API_KEY: str = ''
    BINANCE_SECRET_KEY: str = ''

    # Binance — Key per LIVE (produzione)
    BINANCE_API_KEY_LIVE: str = ''
    BINANCE_SECRET_KEY_LIVE: str = ''

    # Modalità trading
    TRADING_MODE: str = 'test'       # 'test' | 'live'
    ALLOW_LIVE_MODE: bool = False    # Flag sicurezza

    @computed_field
    @property
    def BINANCE_TESTNET(self) -> bool:
        return self.TRADING_MODE == 'test'

    @computed_field
    @property
    def binance_api_key(self) -> str:
        return self.BINANCE_API_KEY if self.TRADING_MODE == 'test' else self.BINANCE_API_KEY_LIVE

    @computed_field
    @property
    def binance_secret_key(self) -> str:
        return self.BINANCE_SECRET_KEY if self.TRADING_MODE == 'test' else self.BINANCE_SECRET_KEY_LIVE

    @computed_field
    @property
    def binance_base_url(self) -> str:
        return 'https://testnet.binance.vision' if self.TRADING_MODE == 'test' else 'https://api.binance.com'

    @computed_field
    @property
    def binance_ws_base_url(self) -> str:
        return 'wss://stream.testnet.binance.vision/ws' if self.TRADING_MODE == 'test' else 'wss://stream.binance.com:9443/ws'

    # Auth
    APP_PASSWORD: str = 'changeme'
    JWT_SECRET: str = 'dev-secret-change-in-prod'
    JWT_EXPIRE_MINUTES: int = 1440

    # AI cascade
    OPENROUTER_API_KEY: str = ''
    AI_CASCADE_TIMEOUT: float = 12.0
    AI_CASCADE_MAX_RETRIES: int = 2

    # AI Evaluator (Fase 5)
    AI_API_BASE_URL: str = 'https://openrouter.ai/api/v1'
    AI_CASCADE_MODELS: str = 'google/gemini-2.0-flash-exp:free,meta-llama/llama-3.1-8b-instruct:free,mistralai/mistral-7b-instruct:free'
    AI_FALLBACK_MODEL: str = 'anthropic/claude-haiku-4.5'
    AI_MAX_TOKENS: int = 1024
    AI_TEMPERATURE: float = 0.2
    AI_TIMEOUT_SECONDS: float = 30.0
    AI_MAX_RETRIES: int = 3
    AI_BACKOFF_BASE: float = 2.0
    AI_EVAL_CACHE_TTL_MINUTES: int = 60
    PIPELINE_AI_EVAL_TOP_N: int = 10
    MAX_CONCURRENT_EVALS: int = 3

    @computed_field
    @property
    def ai_api_key(self) -> str:
        """Alias for OPENROUTER_API_KEY to maintain compatibility across modules."""
        return self.OPENROUTER_API_KEY

    @computed_field
    @property
    def ai_cascade_models_list(self) -> List[str]:
        return [m.strip() for m in self.AI_CASCADE_MODELS.split(',') if m.strip()]

    # Engine
    EXECUTION_INTERVAL_SECONDS: int = 300
    DAILY_REGEN_HOUR: int = 3
    MAX_OPEN_TRADES: int = 1
    MAX_DAILY_LOSS_EUR: float = 15.0
    PAPER_TRADING: bool = True

    # Execution Engine (Fase 4)
    MAX_CONCURRENT_POSITIONS: int = 1
    MAX_EXPOSURE_PER_SYMBOL_PCT: float = 0.10
    MAX_DRAWDOWN_PCT: float = 15.0
    DEFAULT_POSITION_SIZE_PCT: float = 0.05
    DEFAULT_STOP_LOSS_PCT: float = 0.02
    DEFAULT_TAKE_PROFIT_PCT: float = 0.04
    SIGNAL_STRENGTH_THRESHOLD: float = 0.6
    MARKET_REGIME_VOLATILE_THRESHOLD: float = 0.025
    MARKET_REGIME_TRENDING_THRESHOLD: float = 0.15
    SCHEDULER_PIPELINE_INTERVAL_MIN: int = 60
    SCHEDULER_SIGNAL_INTERVAL_MIN: int = 5   # Frequenza tick per strategie ACTIVE
    SCHEDULER_MONITOR_POSITIONS_INTERVAL_SECONDS: int = 30
    SCHEDULER_HEARTBEAT_INTERVAL_SECONDS: int = 10
    SCHEDULER_MONITOR_PNL_INTERVAL_SECONDS: int = 30

    # Pluggability (TASK-214)
    STRATEGY_PLUGINS: str = ""  # Comma-separated module paths

    @computed_field
    @property
    def strategy_plugins_list(self) -> List[str]:
        return [p.strip() for p in self.STRATEGY_PLUGINS.split(',') if p.strip()]

    # Backend
    BACKEND_HOST: str = '0.0.0.0'
    BACKEND_PORT: int = 8888
    CORS_ORIGINS: str = 'http://localhost:4208'
    LOG_LEVEL: str = 'INFO'

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(',')]

    # Scalping
    @property
    def scalping(self) -> ScalpingSettings:
        return ScalpingSettings()


settings = Settings()