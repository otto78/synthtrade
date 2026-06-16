-- Migration: supervisor_memory table
-- TASK-846: FASE F1 — Tabella memoria decisioni Supervisor
-- 
-- Crea la tabella per persistire le decisioni del supervisor AI,
-- permettere il caricamento dello storico nel context e verificare
-- l'outcome delle decisioni passate.

CREATE TABLE IF NOT EXISTS supervisor_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Decisione
    action TEXT NOT NULL,                     -- 'change_strategy' | 'update_params' | 'update_threshold' | 'pause_trading' | 'resume_trading' | 'no_action'
    reason TEXT,
    confidence REAL DEFAULT 0.0,

    -- Contesto al momento della decisione
    market_bias TEXT,                         -- 'bullish' | 'bearish' | 'neutral'
    primary_signal TEXT,                      -- quale segnale ha guidato
    new_strategy TEXT,                        -- se change_strategy
    new_params JSONB,                          -- se update_params/update_threshold

    -- Flag applicazione
    was_applied BOOLEAN DEFAULT FALSE,
    blocked_reason TEXT,                       -- se non applicata (cooldown/regime mismatch/etc.)

    -- Snapshot del contesto
    market_context JSONB,                      -- regime, funding_rate, score, collector info
    session_perf JSONB,                        -- trade count, wins, losses, pnl, win_rate

    -- Outcome verificato (popolato da TASK-848)
    outcome_verified_at TIMESTAMPTZ,
    outcome_pnl_delta REAL,                    -- variazione PnL dopo la decisione
    outcome_label TEXT                         -- 'positive' | 'negative' | 'neutral'

);

-- Indici per query rapide
CREATE INDEX IF NOT EXISTS idx_supervisor_memory_symbol_decided
    ON supervisor_memory (symbol, decided_at DESC);

CREATE INDEX IF NOT EXISTS idx_supervisor_memory_session
    ON supervisor_memory (session_id);

CREATE INDEX IF NOT EXISTS idx_supervisor_memory_action_applied
    ON supervisor_memory (action, was_applied);

CREATE INDEX IF NOT EXISTS idx_supervisor_memory_outcome_pending
    ON supervisor_memory (was_applied, outcome_verified_at)
    WHERE was_applied = TRUE AND outcome_verified_at IS NULL;