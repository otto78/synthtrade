-- Migration: Session Log File Path
-- Aggiunge il campo log_file_path alla tabella scalping_sessions
-- per tracciare il percorso del file .txt dei log della sessione.

-- 1. Aggiungi colonna log_file_path
ALTER TABLE IF EXISTS scalping_sessions
    ADD COLUMN IF NOT EXISTS log_file_path TEXT;

COMMENT ON COLUMN scalping_sessions.log_file_path IS 'Percorso assoluto del file .txt contenente il dump dei log della sessione (generato allo stop).';