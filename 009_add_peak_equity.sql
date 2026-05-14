-- Migration 009: Add peak_equity_usdt to strategies
-- tracks the highest equity (initial capital + PnL) reached by a strategy

ALTER TABLE strategies ADD COLUMN peak_equity_usdt FLOAT DEFAULT NULL;
COMMENT ON COLUMN strategies.peak_equity_usdt IS 'Highest equity value (USDT) reached by the strategy since activation';