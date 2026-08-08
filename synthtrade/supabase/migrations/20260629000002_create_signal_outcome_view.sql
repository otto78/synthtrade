-- TASK-897: Vista aggregata win rate per (strategy_type, regime)
-- FIX: rimuovi filtro decision_type='execute' — la JOIN con scalping_trades garantisce
-- gia' che il segnale abbia prodotto un trade reale. Il filtro escludeva le esecuzioni
-- loggate come 'mean_reversion_override' (TASK-912), falsando il win rate storico.
-- FIX definizione vincita: conta come vincite anche le exit da break-even/trailing
-- (profitto bloccato, mini-TP progressivo), coerente con la regola del supervisor.
CREATE OR REPLACE VIEW signal_outcome_by_strategy_regime AS
SELECT
    sl.strategy_type,
    sl.regime,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (
        WHERE t.pnl > 0 OR t.signal_reason IN ('stop_loss_breakeven', 'stop_loss_trailing')
    ) AS n_wins,
    ROUND(COUNT(t.id) FILTER (
        WHERE t.pnl > 0 OR t.signal_reason IN ('stop_loss_breakeven', 'stop_loss_trailing')
    )::numeric / NULLIF(COUNT(t.id), 0) * 100, 1) AS win_rate_pct,
    ROUND(AVG(t.pnl), 4) AS avg_pnl,
    ROUND(SUM(t.pnl), 4) AS total_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE t.status = 'closed'
GROUP BY sl.strategy_type, sl.regime;
