-- TASK-431: Aggiungere colonna mode (test/live) alle tabelle esistenti
-- per separare i dati di TEST da quelli di LIVE

-- 1. strategies
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS trading_mode TEXT DEFAULT 'test';
UPDATE strategies SET trading_mode = 'test' WHERE trading_mode IS NULL;

-- 2. trades
ALTER TABLE trades ADD COLUMN IF NOT EXISTS trading_mode TEXT DEFAULT 'test';
UPDATE trades SET trading_mode = 'test' WHERE trading_mode IS NULL;
-- Migrare dati esistenti: paper=true → mode='test', paper=false → mode='live'
UPDATE trades SET trading_mode = 'live' WHERE paper = false AND trading_mode = 'test';

-- 3. operation_logs
ALTER TABLE operation_logs ADD COLUMN IF NOT EXISTS trading_mode TEXT DEFAULT 'test';
UPDATE operation_logs SET trading_mode = 'test' WHERE trading_mode IS NULL;

-- Indici per filtrare per modalità (utile per performance su tabelle grandi)
CREATE INDEX IF NOT EXISTS idx_strategies_trading_mode ON strategies(trading_mode);
CREATE INDEX IF NOT EXISTS idx_trades_trading_mode ON trades(trading_mode);
CREATE INDEX IF NOT EXISTS idx_logs_trading_mode ON operation_logs(trading_mode);