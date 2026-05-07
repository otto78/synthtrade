-- Migration 005: Aggiunta colonna expires_at e funzione di pulizia strategie scadute
-- TASK-320: Persistenza & Scadenza Strategie

ALTER TABLE strategies
  ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ DEFAULT (now() + interval '7 days');

-- Indice per performance su pulizia automatica
CREATE INDEX IF NOT EXISTS idx_strategies_expires_at_status 
  ON strategies (expires_at, status);

-- Funzione di pulizia automatica delle strategie PENDING scadute
CREATE OR REPLACE FUNCTION cleanup_expired_strategies()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  deleted_count integer;
BEGIN
  DELETE FROM strategies
  WHERE status = 'PENDING'
    AND expires_at < now();
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$;

-- Trigger automatico: imposta expires_at su INSERT se non specificato
CREATE OR REPLACE FUNCTION set_default_expiry()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.expires_at IS NULL THEN
    NEW.expires_at := now() + interval '7 days';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_strategies_set_expiry ON strategies;
CREATE TRIGGER trg_strategies_set_expiry
  BEFORE INSERT ON strategies
  FOR EACH ROW
  EXECUTE FUNCTION set_default_expiry();