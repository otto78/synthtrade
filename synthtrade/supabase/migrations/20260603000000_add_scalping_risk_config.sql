-- Migration: Add scalping_risk_config table for persisting risk controls

CREATE TABLE IF NOT EXISTS public.scalping_risk_config (
    id integer PRIMARY KEY DEFAULT 1,
    max_daily_loss numeric NOT NULL DEFAULT 50,
    max_drawdown numeric NOT NULL DEFAULT 10,
    leverage integer NOT NULL DEFAULT 10,
    stop_loss_pct numeric NOT NULL DEFAULT 0.3,
    take_profit_pct numeric NOT NULL DEFAULT 0.5,
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    -- Ensure only one row exists (global config)
    CONSTRAINT scalping_risk_config_id_check CHECK (id = 1)
);

-- Insert default row if it doesn't exist
INSERT INTO public.scalping_risk_config (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- Set up RLS (Row Level Security)
ALTER TABLE public.scalping_risk_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to scalping_risk_config" ON public.scalping_risk_config
    FOR ALL
    USING (true)
    WITH CHECK (true);
