export enum WsMessageType {
  Ping = 'ping',
  Price = 'price',
  EngineStatus = 'engine_status',
  StatsUpdate = 'stats_update',
  NewLog = 'new_log',
  Error = 'error',
  TradeOpened = 'trade_opened',
  TradeClosed = 'trade_closed',
  StrategyStopped = 'strategy_stopped',
  StrategyPnlUpdated = 'strategy_pnl_updated',
}

export interface WsMessage<T = any> {
  type: WsMessageType | string;
  payload?: T;
  [key: string]: any; // Keep index signature for generic access if needed
}

export interface WsPricePayload {
  pair: string;
  price: number;
}

export interface WsEngineStatusPayload {
  status: string;
}

export interface WsErrorPayload {
  code: number;
  detail: string;
}

export interface WsTradeOpenedPayload {
  strategy_id: string;
  trade_id: string;
  symbol: string;
  direction: string;
  price: number;
  quantity: number;
}

export interface WsTradeClosedPayload {
  strategy_id: string;
  trade_id: string;
  pnl_pct: number;
  exit_price: number;
}

export interface WsStrategyStoppedPayload {
  strategy_id: string;
  final_pnl_pct: number;
  final_value_usdt: number;
}

export interface WsStrategyPnlUpdatedPayload {
  strategy_id: string;
  current_pnl_pct: number;
  current_pnl_eur: number;
  current_value_usdt: number;
}
