-- Migration 008: Add custom_name field for user-friendly strategy naming
-- TASK-NOME-STRATEGIA

ALTER TABLE strategies
ADD COLUMN IF NOT EXISTS custom_name TEXT;