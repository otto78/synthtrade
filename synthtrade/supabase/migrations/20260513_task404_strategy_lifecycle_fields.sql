-- TASK-404: Nuovi campi per il lifecycle delle strategie attive
-- Aggiunge: activated_at, stopped_at, initial_capital_usdt,
--           current_value_usdt, allocation_trades, last_tick_at

ALTER TABLE strategies
  ADD COLUMN IF NOT EXISTS activated_at       TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS stopped_at         TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS initial_capital_usdt FLOAT,
  ADD COLUMN IF NOT EXISTS current_value_usdt   FLOAT,
  ADD COLUMN IF NOT EXISTS allocation_trades    JSONB,
  ADD COLUMN IF NOT EXISTS last_tick_at        TIMESTAMPTZ;

-- Indice per query rapide su strategie ACTIVE
CREATE INDEX IF NOT EXISTS idx_strategies_status_active
  ON strategies (status)
  WHERE status = 'ACTIVE';

-- Aggiunge il valore STOPPED all'insieme degli stati previsti (documentativo)
-- I valori validi sono: PENDING, APPROVED, REJECTED, ACTIVE, EXPIRED, STOPPED
COMMENT ON COLUMN strategies.activated_at IS 'Timestamp di attivazione della strategia (POST /activate)';
COMMENT ON COLUMN strategies.stopped_at IS 'Timestamp di stop della strategia (POST /stop)';
COMMENT ON COLUMN strategies.initial_capital_usdt IS 'Capitale USDT allocato al momento dell''attivazione';
COMMENT ON COLUMN strategies.current_value_usdt IS 'Valore corrente USDT del portafoglio della strategia (aggiornato dal monitor job)';
COMMENT ON COLUMN strategies.allocation_trades IS 'Snapshot JSON dei trade iniziali di allocazione capitale';
COMMENT ON COLUMN strategies.last_tick_at IS 'Timestamp dell''ultimo tick dello scheduler su questa strategia';
