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

    # Engine
    EXECUTION_INTERVAL_SECONDS: int = 300
    DAILY_REGEN_HOUR: int = 3
    MAX_OPEN_TRADES: int = 1
    MAX_DAILY_LOSS_EUR: float = 15.0
    PAPER_TRADING: bool = True

    # Backend
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:4200"
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
