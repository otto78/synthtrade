-- Migration: scalping_runtime_config
-- Permette override runtime dei parametri scalping senza restart backend.
-- I valori qui sovrascrivono quelli di .env per la sessione corrente.

CREATE TABLE scalping_runtime_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    value_type  TEXT NOT NULL CHECK (value_type IN ('float', 'int', 'bool', 'str')),
    description TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Valori di default (specchio del .env — cambiarli qui non richiede restart)
INSERT INTO scalping_runtime_config (key, value, value_type, description) VALUES
('SCALPING_TRADE_VALUE',                  '10.0',  'float', 'Valore singolo trade in USDC'),
('SCALPING_MAX_DAILY_LOSS',               '50.0',  'float', 'Perdita giornaliera massima USD'),
('SCALPING_MAX_DRAWDOWN_PCT',             '10.0',  'float', 'Drawdown massimo %'),
('SCALPING_STOP_LOSS_PCT',                '0.3',   'float', 'Stop loss % sul prezzo entrata'),
('SCALPING_TAKE_PROFIT_PCT',              '0.5',   'float', 'Take profit % sul prezzo entrata'),
('SCALPING_SIGNAL_STRENGTH_THRESHOLD',    '15.0',  'float', 'Soglia score intelligence 0-100'),
('SCALPING_MIN_CONFIDENCE',               '0.3',   'float', 'Confidenza minima combinata 0-1'),
('SCALPING_MIN_COLLECTORS',               '4',     'int',   'Collector minimi per usare intelligence'),
('SCALPING_SUPERVISOR_INTERVAL_SEC',      '600',   'int',   'Intervallo supervisor AI (secondi)'),
('SCALPING_STRATEGY_COOLDOWN_SEC',        '1200',  'int',   'Cooldown cambio strategia (secondi)'),
('SCALPING_PARAM_UPDATE_COOLDOWN_SEC',    '600',   'int',   'Cooldown update params (secondi)'),
('SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE', '5', 'int', 'Trade minimi prima di cambiare strategia'),
('SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS', '3',  'int',   'Max decisioni identiche consecutive'),
('SCALPING_REGIME_TREND_THRESHOLD_PCT',   '3.0',   'float', 'Soglia % per regime trending'),
('SCALPING_REGIME_VOLATILE_THRESHOLD',    '0.02',  'float', 'Soglia ATR/close per regime volatile');
