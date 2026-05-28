-- Add risk_config JSONB column to scalping_sessions
ALTER TABLE scalping_sessions ADD COLUMN IF NOT EXISTS risk_config JSONB;
