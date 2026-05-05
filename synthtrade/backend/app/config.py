from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Binance
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    BINANCE_TESTNET: bool = True

    # Auth
    APP_PASSWORD: str = "changeme"
    JWT_SECRET: str = "dev-secret-change-in-prod"
    JWT_EXPIRE_MINUTES: int = 1440

    # AI cascade
    OPENROUTER_API_KEY: str = ""
    AI_CASCADE_TIMEOUT: float = 12.0
    AI_CASCADE_MAX_RETRIES: int = 2

    # AI Evaluator (Fase 5)
    AI_API_KEY: str = ""
    AI_API_BASE_URL: str = "https://openrouter.ai/api/v1"
    AI_CASCADE_MODELS: str = "google/gemini-2.0-flash-exp:free,meta-llama/llama-3.1-8b-instruct:free,mistralai/mistral-7b-instruct:free"
    AI_FALLBACK_MODEL: str = "anthropic/claude-haiku-4"
    AI_MAX_TOKENS: int = 1024
    AI_TEMPERATURE: float = 0.2
    AI_TIMEOUT_SECONDS: float = 30.0
    AI_MAX_RETRIES: int = 3
    AI_BACKOFF_BASE: float = 2.0
    AI_EVAL_CACHE_TTL_MINUTES: int = 60
    PIPELINE_AI_EVAL_TOP_N: int = 10
    MAX_CONCURRENT_EVALS: int = 3

    @property
    def ai_cascade_models_list(self) -> list[str]:
        return [m.strip() for m in self.AI_CASCADE_MODELS.split(",") if m.strip()]

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
    SCHEDULER_PIPELINE_INTERVAL_MIN: int = 60

    # Backend
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:4200"
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
