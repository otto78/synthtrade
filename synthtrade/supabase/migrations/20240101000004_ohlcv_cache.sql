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
