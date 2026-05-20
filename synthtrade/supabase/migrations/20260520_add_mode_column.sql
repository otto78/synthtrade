-- TASK-431: Aggiungere colonna mode (test/live) alle tabelle esistenti
-- per separare i dati di TEST da quelli di LIVE

-- 1. strategies
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'test';
UPDATE strategies SET mode = 'test' WHERE mode IS NULL;

-- 2. trades
ALTER TABLE trades ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'test';
UPDATE trades SET mode = 'test' WHERE mode IS NULL;
-- Migrare dati esistenti: paper=true → mode='test', paper=false → mode='live'
UPDATE trades SET mode = 'live' WHERE paper = false AND mode = 'test';

-- 3. operation_logs
ALTER TABLE operation_logs ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'test';
UPDATE operation_logs SET mode = 'test' WHERE mode IS NULL;

-- Indici per filtrare per modalità (utile per performance su tabelle grandi)
CREATE INDEX IF NOT EXISTS idx_strategies_mode ON strategies(mode);
CREATE INDEX IF NOT EXISTS idx_trades_mode ON trades(mode);
CREATE INDEX IF NOT EXISTS idx_logs_mode ON operation_logs(mode);