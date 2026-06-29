-- TASK-893: Crea tabella session_signal_log per persistenza decisioni sistema
-- Ogni riga rappresenta una decisione presa dal sistema (execute, block, hold, etc.)

CREATE TABLE IF NOT EXISTS session_signal_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    symbol TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- snapshot contesto al momento della decisione
    regime TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    tech_signal TEXT,                   -- BUY/SELL/HOLD/CLOSE
    tech_confidence NUMERIC(5,3),
    intel_score NUMERIC(6,2),
    intel_bias TEXT,                    -- bullish/bearish/neutral
    trend_direction TEXT,               -- converging/diverging/stable
    trend_value NUMERIC(6,2),

    -- esito della decisione
    decision_type TEXT NOT NULL CHECK (decision_type IN (
        'execute', 'block_conflict', 'mean_reversion_override',
        'hold_existing_position', 'rejected_other', 'execution_error'
    )),
    decision_reason TEXT,               -- testo libero, es. "conflitto intelligence-tecnico"

    -- collegamento al trade (Fase 3 - TASK-895)
    trade_id UUID REFERENCES scalping_trades(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_log_session ON session_signal_log(session_id, decided_at);
CREATE INDEX IF NOT EXISTS idx_signal_log_strategy_regime ON session_signal_log(strategy_type, regime);
CREATE INDEX IF NOT EXISTS idx_signal_log_decision_type ON session_signal_log(decision_type);
