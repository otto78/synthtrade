# TASKS.md — SynthTrade Task Tracking

## Active Tasks

### TASK-814 — Live Mode Bug Fixes (2026-06-05)

Fix issues identified from live session logs:
- [ ] **Issue 1**: WS initial handshake timeout — warmup blocks event loop
- [ ] **Issue 2**: Binance RSS Poller — empty/non-XML response
- [ ] **Issue 3**: CoinGecko News Poller — 401 Unauthorized (news endpoint needs API key)
- [ ] **Issue 4**: News RSS Feed URLs — CoinDesk redirect (add www), TheBlock 404
- [ ] **Issue 5**: No trades executing in live mode — analyze and fix signal pipeline
- [ ] Update docs and commit