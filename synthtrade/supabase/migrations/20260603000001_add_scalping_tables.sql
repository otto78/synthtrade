CREATE TABLE scalping_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    mode TEXT NOT NULL,
    timeframe TEXT DEFAULT '1m',
    strategy TEXT,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ
);

CREATE TABLE scalping_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_price FLOAT NOT NULL,
    exit_price FLOAT,
    quantity FLOAT,
    pnl FLOAT,
    pnl_pct FLOAT,
    strategy_type TEXT,
    signal_reason TEXT,
    status TEXT NOT NULL,
    entry_time TIMESTAMPTZ,
    exit_time TIMESTAMPTZ
);
