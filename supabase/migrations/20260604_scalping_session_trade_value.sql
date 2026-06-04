-- Migration: Aggiunge colonna trade_value a scalping_sessions
-- Descrizione: Permette di salvare/ripristinare il trade_value della sessione
-- Task: FIX persistenza trade_value al reload

ALTER TABLE scalping_sessions ADD COLUMN IF NOT EXISTS trade_value NUMERIC(12,2) DEFAULT 100.00;

COMMENT ON COLUMN scalping_sessions.trade_value IS 'Valore in USD per singolo trade (trade_value)';

-- Aggiunge anche mode se non già TEXT (da vecchia migration potrebbe essere già TEXT)
-- Non serve fare nulla, mode è già TEXT CHECK (PAPER/LIVE/BACKTEST)