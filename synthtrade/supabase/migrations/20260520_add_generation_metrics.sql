-- Migration: add generation_metrics table
-- Stores timing and phase metrics for pipeline generation runs
CREATE TABLE IF NOT EXISTS generation_metrics (
    generation_id UUID PRIMARY KEY,
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ,
    phases JSONB -- e.g., {"fetching_market_data": "2026-05-15T12:00:00Z", "saving": "2026-05-15T12:00:30Z"}
);
