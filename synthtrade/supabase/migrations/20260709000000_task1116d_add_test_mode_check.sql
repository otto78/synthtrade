-- TASK-1116.D: Add 'TEST' mode to scalping_sessions CHECK constraint
-- Allows OKX Demo Trading sessions (mode='test') to be saved to DB

-- Check current constraint (for reference)
-- SELECT conname, consrc FROM pg_constraint WHERE conname = 'scalping_sessions_mode_check';

ALTER TABLE scalping_sessions DROP CONSTRAINT IF EXISTS scalping_sessions_mode_check;

ALTER TABLE scalping_sessions ADD CONSTRAINT scalping_sessions_mode_check
  CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST', 'TEST'));

-- Verify the change
-- SELECT conname, consrc FROM pg_constraint WHERE conname = 'scalping_sessions_mode_check';