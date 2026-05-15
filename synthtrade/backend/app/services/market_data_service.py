import pandas as pd
import logging
from datetime import datetime, timezone, timedelta
from app.db.repositories.ohlcv_repository import OhlcvRepository
from app.execution.exchange import BinanceExchangeAdapter

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self, repo: OhlcvRepository, exchange: BinanceExchangeAdapter):
        self.repo = repo
        self.exchange = exchange

    def get_ohlcv(self, pair: str, timeframe: str, days: int = 180) -> pd.DataFrame:
        """Fetch OHLCV from cache; fetch missing delta from Binance."""
        cached_df = self.repo.get_cached(pair, timeframe)
        
        # 1. Recupera dati mancanti (semplificato: se vuoto, scarica tutto)
        # In futuro: confrontare timestamp ultimo dato in cache vs ora
        if cached_df.empty:
            since = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000
            candles = self.exchange.fetch_ohlcv(pair, timeframe, since=int(since), limit=1000)
            
            df = pd.DataFrame(candles, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms")
            
            self.repo.save(pair, timeframe, df)
            return df
            
        return cached_df
