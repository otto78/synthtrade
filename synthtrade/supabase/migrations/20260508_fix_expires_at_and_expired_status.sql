-- Migration 006: Fix expires_at NULL values and add EXPIRED status lifecycle
-- TASK-STRATEGY-FIX

-- 1. Set expires_at for all records with NULL expires_at (7 days from creation)
UPDATE strategies
SET expires_at = created_at + INTERVAL '7 days'
WHERE expires_at IS NULL;

-- 2. Update the cleanup function to also handle ACTIVE -> EXPIRED transition
CREATE OR REPLACE FUNCTION cleanup_expired_strategies()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  active_expired_count integer;
  pending_deleted_count integer;
  total_count integer := 0;
BEGIN
  -- Transizione ACTIVE scadute -> EXPIRED
  UPDATE strategies
  SET status = 'EXPIRED', updated_at = now()
  WHERE status = 'ACTIVE'
    AND expires_at < now();
  GET DIAGNOSTICS active_expired_count = ROW_COUNT;
  total_count := total_count + active_expired_count;

  -- Pulizia PENDING scadute
  DELETE FROM strategies
  WHERE status = 'PENDING'
    AND expires_at < now();
  GET DIAGNOSTICS pending_deleted_count = ROW_COUNT;
  total_count := total_count + pending_deleted_count;

  RETURN total_count;
END;
$$;