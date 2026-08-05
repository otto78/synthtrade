-- TASK-1246: Trailing stop progressivo — persistenza step (solo telemetria/UI).
-- La fonte di verità del prezzo SL è sl_price; trailing_step non partecipa a calcoli.
ALTER TABLE public.scalping_trades
  ADD COLUMN IF NOT EXISTS trailing_step int NOT NULL DEFAULT 0;
