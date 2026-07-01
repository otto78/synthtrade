-- TASK-913: Aggiunge 'rejected_short_unsupported' al CHECK constraint decision_type
-- Nuovo decision_type per segnali SELL scartati (short non implementato)

-- Rimuovi il vecchio constraint
ALTER TABLE session_signal_log DROP CONSTRAINT IF EXISTS session_signal_log_decision_type_check;

-- Ricrea il constraint con il nuovo valore
ALTER TABLE session_signal_log ADD CONSTRAINT session_signal_log_decision_type_check
  CHECK (decision_type IN (
    'execute', 'block_conflict', 'mean_reversion_override',
    'hold_existing_position', 'rejected_other', 'execution_error',
    'rejected_short_unsupported'
  ));