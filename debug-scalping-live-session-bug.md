# Debug Session: scalping-live-session-bug

## Symptoms
- `live_balance` and `paper_balance` show as 0 in a live session despite having USDC balance.
- Session status reverts to `idle` with `session_id: null` after starting.
- Chart scaling is broken (showing values around 60000 and 600 simultaneously).
- No trades are executed.

## Hypotheses
1. **[H1] Balance Fetch Failure**: `BinanceExchangeAdapter.get_balance` fails or returns 0 due to asset mapping or CCXT issues.
2. **[H2] Start Sequence Crash**: Exception during `control_session(start)` after DB save, leading to state loss or cleanup.
3. **[H3] WebSocket Desync**: Stale `session_restored` events with empty data are sent to frontend.
4. **[H4] Chart Scaling/Cleanup**: Chart doesn't clear old data (BTC) when switching to new symbol (BNB).

## Evidence Collected
- (Waiting for logs...)

## Status
- [OPEN]
