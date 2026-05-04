CREATE TABLE trades (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id   TEXT REFERENCES strategies(id),
  action        TEXT NOT NULL,
  pair          TEXT NOT NULL,
  price         FLOAT NOT NULL,
  quantity      FLOAT NOT NULL,
  cost_eur      FLOAT,
  fee_eur       FLOAT,
  pnl_pct       FLOAT,
  paper         BOOLEAN DEFAULT TRUE,
  executed_at   TIMESTAMPTZ DEFAULT now()
);
