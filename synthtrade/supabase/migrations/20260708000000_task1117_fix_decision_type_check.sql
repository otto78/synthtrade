-- TASK-1117: Fix DB constraint `session_signal_log_decision_type_check`
--
-- Aggiunge i valori mancanti al CHECK constraint della tabella session_signal_log.
-- I log con decision_type='rejected_short_unsupported' violavano il constraint
-- e venivano persi silenziosamente (errore 23514).
--
-- Valori aggiunti:
--   - rejected_short_unsupported  (short selling non implementato)
--   - execution_error              (errore durante esecuzione trade)
--
-- Valori pre-esistenti (non modificati):
--   - execute, block_conflict, mean_reversion_override,
--     hold_existing_position, rejected_other
--
-- Applica con: psql o Supabase MCP apply_migration

-- ────────────────────────────────────────────────────────────────
-- 1. Drop vecchio constraint
-- ────────────────────────────────────────────────────────────────

ALTER TABLE session_signal_log
    DROP CONSTRAINT IF EXISTS session_signal_log_decision_type_check;

-- ────────────────────────────────────────────────────────────────
-- 2. Re-crea constraint con nuovi valori
-- ────────────────────────────────────────────────────────────────

ALTER TABLE session_signal_log
    ADD CONSTRAINT session_signal_log_decision_type_check
    CHECK (decision_type IN (
        'execute',
        'block_conflict',
        'mean_reversion_override',
        'hold_existing_position',
        'rejected_other',
        'rejected_short_unsupported',
        'execution_error'
    ));

-- ────────────────────────────────────────────────────────────────
-- 3. Verifica
-- ────────────────────────────────────────────────────────────────
-- Test: INSERT con 'rejected_short_unsupported' non deve più violare
-- INSERT INTO session_signal_log (session_id, symbol, decision_type)
-- VALUES ('00000000-0000-0000-0000-000000000000', 'TEST', 'rejected_short_unsupported');