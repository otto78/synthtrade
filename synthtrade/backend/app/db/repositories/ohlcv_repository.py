import pandas as pd
from typing import List

class OhlcvRepository:
    def __init__(self, db):
        self.db = db
        self.table_name = "ohlcv_cache"

    def get_cached(self, pair: str, timeframe: str) -> pd.DataFrame:
        res = self.db.table(self.table_name).select("*").eq("pair", pair).eq("timeframe", timeframe).order("ts", desc=False).execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        # Assicurati di rinominare o formattare le colonne se necessario
        return df

    def save(self, pair: str, timeframe: str, df: pd.DataFrame):
        records = df.to_dict(orient="records")
        for r in records:
            r["pair"] = pair
            r["timeframe"] = timeframe
        self.db.table(self.table_name).upsert(records).execute()
