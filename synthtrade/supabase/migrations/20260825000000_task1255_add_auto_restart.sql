-- TASK-1255: Stop & Go — auto-restart settimanale sessione
-- Aggiunge la colonna auto_restart_weekly a scalping_sessions

ALTER TABLE scalping_sessions
  ADD COLUMN IF NOT EXISTS auto_restart_weekly boolean NOT NULL DEFAULT false;
