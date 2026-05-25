/**
 * Intelligence Models for Scalping Dashboard
 * TypeScript interfaces matching Pydantic models from backend
 */

export interface FundingRate {
  symbol: string;
  rate: number;
  timestamp: string;
  next_funding_time: string;
}

export interface OpenInterest {
  symbol: string;
  value_usd: number;
  asset: string;
  timestamp: string;
}

export interface CVDData {
  symbol: string;
  cvd: number;
  buy_volume: number;
  sell_volume: number;
  trend: 'bullish' | 'bearish' | 'neutral';
  timestamp: string;
}

export interface FearGreedData {
  value: number;
  label: string;
  timestamp: string;
}

export interface SignalScore {
  total: number;
  bias: 'bullish' | 'bearish' | 'neutral';
  tradeable: boolean;
  confidence: number;
  breakdown: Record<string, number>;
}

export interface MarketIntelSnapshot {
  funding_rate?: FundingRate;
  open_interest?: OpenInterest;
  long_short_ratio?: {
    symbol: string;
    long_pct: number;
    short_pct: number;
  };
  cvd?: CVDData;
  fear_greed?: FearGreedData;
  signal_score?: SignalScore;
}