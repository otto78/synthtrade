-- TASK-1108: DB Migration Provider e Order IDs
-- Aggiunge colonne provider-neutral a scalping_sessions e scalping_trades.
-- Backward compatible: default 'binance' per storico Binance.
--
-- Applica con: Supabase MCP apply_migration o psql diretto.

-- ────────────────────────────────────────────────────────────────
-- 1. scalping_sessions: provider, account_mode, fee tier
-- ────────────────────────────────────────────────────────────────

ALTER TABLE scalping_sessions
    ADD COLUMN IF NOT EXISTS exchange_provider       TEXT        NOT NULL DEFAULT 'binance',
    ADD COLUMN IF NOT EXISTS exchange_account_mode   TEXT        NOT NULL DEFAULT 'test',   -- 'test' | 'live'
    ADD COLUMN IF NOT EXISTS exchange_demo           BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS fee_tier_certified      BOOLEAN,
    ADD COLUMN IF NOT EXISTS fee_tier_maker          FLOAT,
    ADD COLUMN IF NOT EXISTS fee_tier_taker          FLOAT,
    ADD COLUMN IF NOT EXISTS fee_tier_raw            JSONB,
    ADD COLUMN IF NOT EXISTS trade_value             FLOAT,
    ADD COLUMN IF NOT EXISTS log_content             TEXT;

-- ────────────────────────────────────────────────────────────────
-- 2. scalping_trades: provider, exchange-neutral order ids, fee, raw
-- ────────────────────────────────────────────────────────────────

ALTER TABLE scalping_trades
    ADD COLUMN IF NOT EXISTS exchange_provider       TEXT        NOT NULL DEFAULT 'binance',
    ADD COLUMN IF NOT EXISTS exchange_order_id       TEXT,       -- entry order id (any provider)
    ADD COLUMN IF NOT EXISTS exchange_bracket_id     TEXT,       -- OKX algo id OR Binance orderListId
    ADD COLUMN IF NOT EXISTS exchange_tp_order_id    TEXT,       -- TP leg order id
    ADD COLUMN IF NOT EXISTS exchange_sl_order_id    TEXT,       -- SL leg order id
    ADD COLUMN IF NOT EXISTS entry_commission        FLOAT,
    ADD COLUMN IF NOT EXISTS entry_commission_asset  TEXT,
    ADD COLUMN IF NOT EXISTS exit_commission         FLOAT,
    ADD COLUMN IF NOT EXISTS exit_commission_asset   TEXT,
    ADD COLUMN IF NOT EXISTS exchange_raw            JSONB,      -- raw payload for debugging
    -- Legacy Binance column kept for backward compat (do NOT remove until full migration)
    ADD COLUMN IF NOT EXISTS oco_order_list_id       TEXT;       -- Binance OCO orderListId (deprecated)

-- ────────────────────────────────────────────────────────────────
-- 3. Index for fast lookup by exchange order id
-- ────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_scalping_trades_exchange_order_id
    ON scalping_trades(exchange_order_id);

CREATE INDEX IF NOT EXISTS idx_scalping_trades_exchange_bracket_id
    ON scalping_trades(exchange_bracket_id);

CREATE INDEX IF NOT EXISTS idx_scalping_trades_oco_order_list_id
    ON scalping_trades(oco_order_list_id);

-- ────────────────────────────────────────────────────────────────
-- 4. Backfill: map legacy oco_order_list_id -> exchange_bracket_id
--    (only for existing Binance rows)
-- ────────────────────────────────────────────────────────────────

UPDATE scalping_trades
SET exchange_bracket_id = oco_order_list_id
WHERE oco_order_list_id IS NOT NULL
  AND exchange_bracket_id IS NULL;

-- ────────────────────────────────────────────────────────────────
-- 5. Comments for documentation
-- ────────────────────────────────────────────────────────────────

COMMENT ON COLUMN scalping_sessions.exchange_provider IS
    'Exchange provider identifier: binance | okx. Default binance for legacy rows.';

COMMENT ON COLUMN scalping_sessions.exchange_demo IS
    'True when session ran against OKX Demo Trading (x-simulated-trading: 1).';

COMMENT ON COLUMN scalping_trades.exchange_bracket_id IS
    'OKX: algo order ID from /api/v5/trade/order-algo. Binance: orderListId from OCO.';

COMMENT ON COLUMN scalping_trades.oco_order_list_id IS
    'DEPRECATED. Legacy Binance OCO orderListId. Use exchange_bracket_id instead.';
