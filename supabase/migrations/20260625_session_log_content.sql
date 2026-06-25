-- Migration: Session Log Content (stored in DB)
-- Sostituisce log_file_path con log_content salvato direttamente nel DB,
-- così i log sono sempre disponibili anche se i file su disco vengono cancellati.
-- Questo rende il download deploy-safe: non dipende più dal filesystem.

-- 1. Aggiungi colonna log_content
ALTER TABLE IF EXISTS scalping_sessions
    ADD COLUMN IF NOT EXISTS log_content TEXT;

COMMENT ON COLUMN scalping_sessions.log_content IS 'Contenuto completo del dump dei log della sessione (salvato nel DB per deploy-safety).';

-- 2. Index per ricerca full-text opzionale
-- (opzionale, può essere aggiunto in futuro se necessario)