CREATE TABLE operation_logs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id   TEXT,
  action        TEXT NOT NULL,
  price         FLOAT,
  quantity      FLOAT,
  reason        TEXT,
  ai_score      FLOAT,
  metadata      JSONB DEFAULT '{}',
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_logs_created_at  ON operation_logs(created_at DESC);
CREATE INDEX idx_logs_strategy_id ON operation_logs(strategy_id);
CREATE INDEX idx_logs_action      ON operation_logs(action);
