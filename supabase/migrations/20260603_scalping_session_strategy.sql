-- Migration: Aggiunge colonne strategy e strategy_params a scalping_sessions
-- Descrizione: Permette di salvare/ripristinare la strategia corrente della sessione
-- Task: TASK-810 (fix persistenza strategia)

-- 1. Aggiunge colonna strategy (testuale, nome della strategia)
ALTER TABLE scalping_sessions ADD COLUMN IF NOT EXISTS strategy TEXT DEFAULT 'scalping_v2';

-- 2. Aggiunge colonna strategy_params (JSONB, parametri specifici della strategia)
ALTER TABLE scalping_sessions ADD COLUMN IF NOT EXISTS strategy_params JSONB;

-- 3. Aggiunge colonna risk_config se non già presente (da migration precedente)
ALTER TABLE scalping_sessions ADD COLUMN IF NOT EXISTS risk_config JSONB;

-- 4. Aggiunge colonna active_strategy (nome corrente applicato, per compatibilità)
ALTER TABLE scalping_sessions ADD COLUMN IF NOT EXISTS active_strategy TEXT DEFAULT 'scalping_v2';

COMMENT ON COLUMN scalping_sessions.strategy IS 'Nome della strategia di trading corrente (es. scalping_v2, rsi_bollinger, ema_cross, vwap_reversion)';
COMMENT ON COLUMN scalping_sessions.active_strategy IS 'Strategia attivamente applicata (sinonimo di strategy per chiarezza)';
COMMENT ON COLUMN scalping_sessions.strategy_params IS 'Parametri correnti della strategia (JSON)';