INSERT INTO strategies (id, title, template, pair, timeframe, params, rules, risk, targets, status, expires_at) VALUES
(
  'trend_00001',
  'EMA Trend BTC 5m',
  'trend_ema',
  'BTC/USDT',
  '5m',
  '{"ema_fast": 20, "ema_slow": 50, "stop_loss": 0.02, "take_profit": 0.04}',
  '{"entry": "ema_crossover", "exit": "reverse_signal"}',
  '{"max_position_eur": 100, "max_daily_loss": 15}',
  '{"horizon_days": 7, "expected_return_pct": 4}',
   'PENDING',
   NOW() + INTERVAL '30 days'
),
(
  'mean_00001',
  'RSI Mean Reversion BTC 15m',
  'mean_reversion_rsi',
  'BTC/USDT',
  '15m',
  '{"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "stop_loss": 0.02, "take_profit": 0.04}',
  '{"entry": "rsi_oversold", "exit": "rsi_overbought"}',
  '{"max_position_eur": 100, "max_daily_loss": 15}',
  '{"horizon_days": 7, "expected_return_pct": 3}',
   'PENDING',
   NOW() + INTERVAL '30 days'
),
(
  'brkout_00001',
  'Bollinger Breakout BTC 5m',
  'breakout_bb',
  'BTC/USDT',
  '5m',
  '{"bb_period": 20, "bb_std": 2.0, "stop_loss": 0.02, "take_profit": 0.05}',
  '{"entry": "bb_breakout_up", "exit": "bb_breakout_down"}',
  '{"max_position_eur": 100, "max_daily_loss": 15}',
  '{"horizon_days": 7, "expected_return_pct": 5}',
   'PENDING',
   NOW() + INTERVAL '30 days'
);
