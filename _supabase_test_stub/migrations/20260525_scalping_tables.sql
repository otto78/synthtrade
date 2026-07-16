-- Migration: Scalping Module v2.0 Tables
-- Descrizione: Tabelle dedicate per il modulo scalping (EPIC-SCALP-800)
-- Task: TASK-802

-- 1. Sessioni di trading scalping
CREATE TABLE IF NOT EXISTS scalping_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode TEXT CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST')),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    status TEXT CHECK (status IN ('running', 'paused', 'stopped')),
    started_at TIMESTAMPTZ NOT NULL,
    stopped_at TIMESTAMPTZ,
    total_pnl NUMERIC(12,6) DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Trade eseguiti (con contesto intelligenza)
CREATE TABLE IF NOT EXISTS scalping_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    symbol TEXT NOT NULL,
    side TEXT CHECK (side IN ('BUY', 'SELL')),
    entry_price NUMERIC(12,6) NOT NULL,
    exit_price NUMERIC(12,6),
    quantity NUMERIC(12,8) NOT NULL,
    pnl NUMERIC(12,6),
    pnl_pct NUMERIC(8,4),
    strategy_type TEXT NOT NULL,
    signal_reason TEXT,
    signal_score NUMERIC(6,2),
    funding_rate_at_entry NUMERIC(10,6),
    fear_greed_at_entry INTEGER,
    cvd_trend_at_entry TEXT,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    status TEXT CHECK (status IN ('open', 'closed', 'cancelled')),
    binance_order_id TEXT
);

-- 3. Decisioni del supervisore AI
CREATE TABLE IF NOT EXISTS supervisor_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    confidence NUMERIC(4,3),
    market_bias TEXT,
    primary_signal TEXT,
    previous_params JSONB,
    new_params JSONB,
    previous_strategy TEXT,
    new_strategy TEXT,
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Snapshot intelligenza di mercato (storico)
CREATE TABLE IF NOT EXISTS market_intel_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    funding_rate NUMERIC(10,6),
    open_interest NUMERIC(20,2),
    long_pct NUMERIC(5,2),
    short_pct NUMERIC(5,2),
    cvd_trend TEXT,
    fear_greed_value INTEGER,
    fear_greed_label TEXT,
    signal_score NUMERIC(6,2),
    signal_bias TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_intel_symbol_time ON market_intel_snapshots(symbol, recorded_at DESC);

-- 5. Opportunità rilevate
CREATE TABLE IF NOT EXISTS opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    urgency TEXT NOT NULL,
    scalping_opportunity BOOLEAN DEFAULT FALSE,
    title TEXT NOT NULL,
    action TEXT,
    symbol TEXT,
    expected_volatility TEXT,
    time_sensitive BOOLEAN DEFAULT FALSE,
    url TEXT,
    raw_content TEXT,
    content_hash TEXT UNIQUE,
    classified_by_ai BOOLEAN DEFAULT FALSE,
    user_action TEXT CHECK (user_action IN ('watched', 'ignored', 'acted')),
    detected_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_opp_urgency_time ON opportunities(urgency, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_opp_symbol ON opportunities(symbol) WHERE symbol IS NOT NULL;