-- Migration 007: Add estimated_profit columns for strategy evaluation display
-- TASK-FIX-EVAL

ALTER TABLE strategies
ADD COLUMN IF NOT EXISTS estimated_profit_pct FLOAT,
ADD COLUMN IF NOT EXISTS estimated_profit_eur FLOAT;