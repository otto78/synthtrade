-- Migration: OCO Flow v2 — TASK-825
-- Aggiunge colonne TP/SL price e OCO order IDs a scalping_trades
-- per supportare il flusso OCO definitivo (OCO_FLOW.md v2.0)

-- Prezzi target OCO (per UI e restore sessione)
ALTER TABLE scalping_trades
    ADD COLUMN IF NOT EXISTS tp_price FLOAT,
    ADD COLUMN IF NOT EXISTS sl_price FLOAT;

-- ID ordini OCO Binance (per matchare gli eventi UDS)
ALTER TABLE scalping_trades
    ADD COLUMN IF NOT EXISTS oco_order_list_id TEXT,
    ADD COLUMN IF NOT EXISTS sl_order_id TEXT,
    ADD COLUMN IF NOT EXISTS tp_order_id TEXT;

-- Commento
COMMENT ON COLUMN scalping_trades.tp_price IS 'Prezzo take profit OCO — usato da UI e restore sessione';
COMMENT ON COLUMN scalping_trades.sl_price IS 'Prezzo stop loss OCO — usato da UI e restore sessione';
COMMENT ON COLUMN scalping_trades.oco_order_list_id IS 'orderListId Binance OCO — per match UDS events';
COMMENT ON COLUMN scalping_trades.sl_order_id IS 'orderId dello STOP_LOSS_LIMIT nel OCO';
COMMENT ON COLUMN scalping_trades.tp_order_id IS 'orderId del LIMIT_MAKER nel OCO';
