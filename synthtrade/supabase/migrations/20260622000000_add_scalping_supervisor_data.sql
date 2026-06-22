-- Aggiunta colonne per analisi Supervisor
ALTER TABLE scalping_trades
ADD COLUMN btc_price_at_entry FLOAT,
ADD COLUMN btc_change_1h_pct FLOAT,
ADD COLUMN btc_change_24h_pct FLOAT,
ADD COLUMN macro_regime TEXT,
ADD COLUMN signal_price FLOAT,
ADD COLUMN slippage_pct FLOAT,
ADD COLUMN signal_to_fill_ms INT,
ADD COLUMN strategies_considered JSONB,
ADD COLUMN strategy_rejection_reason TEXT,
ADD COLUMN regime_classified TEXT,
ADD COLUMN candlestick_pattern TEXT,
ADD COLUMN volume_anomaly BOOLEAN,
ADD COLUMN support_resistance_data JSONB;
