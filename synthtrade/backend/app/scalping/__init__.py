"""Scalping Module v2.0 — Signal Intelligence & High-Frequency Trading.

Questo modulo contiene ESCLUSIVAMENTE la logica ad alta frequenza:
- Intelligence Layer: collectors, score engine, market context
- Opportunità: multi-source polling, classificazione AI
- Supervisor: parameter updater, scheduler decisioni AI
- Engine: execution loop, regime detector, signal aggregator
- Strategie: filtri di timing (EMA cross, RSI+BB, VWAP)
- Session: session management, daily summary
- Backtest: backtest engine, performance calculator

I moduli core (indicators, risk, exchange, ws broadcast, model client)
vengono riusati da app/core/, app/execution/ e app/ai/.
"""