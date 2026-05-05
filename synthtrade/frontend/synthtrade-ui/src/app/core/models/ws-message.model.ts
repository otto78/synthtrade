export enum WsMessageType {
  Ping = 'ping',
  Price = 'price',
  EngineStatus = 'engine_status',
  StatsUpdate = 'stats_update',
  NewLog = 'new_log',
  Error = 'error',
}

export interface WsMessage<T = unknown> {
  type: WsMessageType;
  payload?: T;
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
