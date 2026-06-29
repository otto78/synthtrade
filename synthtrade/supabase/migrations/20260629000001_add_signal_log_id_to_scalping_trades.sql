-- TASK-895: Aggiunge signal_log_id su scalping_trades per collegare trade alla decisione
ALTER TABLE scalping_trades
    ADD COLUMN IF NOT EXISTS signal_log_id UUID REFERENCES session_signal_log(id);

CREATE INDEX IF NOT EXISTS idx_trades_signal_log_id ON scalping_trades(signal_log_id);
