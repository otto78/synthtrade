-- TASK-897: Vista aggregata win rate per (strategy_type, regime)
CREATE OR REPLACE VIEW signal_outcome_by_strategy_regime AS
SELECT
    sl.strategy_type,
    sl.regime,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(COUNT(t.id) FILTER (WHERE t.pnl > 0)::numeric / NULLIF(COUNT(t.id), 0) * 100, 1) AS win_rate_pct,
    ROUND(AVG(t.pnl), 4) AS avg_pnl,
    ROUND(SUM(t.pnl), 4) AS total_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE sl.decision_type = 'execute'
  AND t.status = 'closed'
GROUP BY sl.strategy_type, sl.regime;
