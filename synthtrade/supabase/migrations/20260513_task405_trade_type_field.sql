-- TASK-405: Aggiunge campo trade_type e campi mancanti alla tabella trades
-- trade_type distingue: SIGNAL (default), INITIAL_ALLOCATION, STOP_CLOSE
-- Aggiunge anche: status, exit_price, closed_at che mancano nello schema attuale

ALTER TABLE trades
  ADD COLUMN IF NOT EXISTS trade_type  TEXT NOT NULL DEFAULT 'SIGNAL',
  ADD COLUMN IF NOT EXISTS status      TEXT NOT NULL DEFAULT 'OPEN',
  ADD COLUMN IF NOT EXISTS exit_price  FLOAT,
  ADD COLUMN IF NOT EXISTS closed_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS stop_loss   FLOAT,
  ADD COLUMN IF NOT EXISTS take_profit FLOAT;

-- Indice per query sui trade aperti (usato da monitor job e GET /trades/active)
CREATE INDEX IF NOT EXISTS idx_trades_status_open
  ON trades (status)
  WHERE status = 'OPEN';

-- Indice per query per strategia (usato da POST /stop e monitor)
CREATE INDEX IF NOT EXISTS idx_trades_strategy_id
  ON trades (strategy_id);

COMMENT ON COLUMN trades.trade_type IS 'SIGNAL: segnale tecnico | INITIAL_ALLOCATION: acquisto iniziale | STOP_CLOSE: chiusura forzata';
COMMENT ON COLUMN trades.status IS 'OPEN: posizione aperta | CLOSED: posizione chiusa';
COMMENT ON COLUMN trades.exit_price IS 'Prezzo di uscita (NULL se ancora aperta)';
COMMENT ON COLUMN trades.closed_at IS 'Timestamp di chiusura della posizione';
COMMENT ON COLUMN trades.stop_loss IS 'Prezzo di stop loss impostato all''apertura';
COMMENT ON COLUMN trades.take_profit IS 'Prezzo di take profit impostato all''apertura';
