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
  symbol?: string;
  funding_rate?: number;
  open_interest?: number;
  signal_score?: number;
  signal_bias?: 'bullish' | 'bearish' | 'neutral';
  tradeable?: boolean;
  confidence?: number;
  fear_greed_value?: number;
  fear_greed_label?: string;
  cvd_trend?: string;
  long_pct?: number;
  short_pct?: number;
  breakdown?: Record<string, number>;
  recorded_at?: string;
  
  // Extended format for detailed data
  funding_rate_detail?: FundingRate;
  open_interest_detail?: OpenInterest;
  long_short_ratio?: {
    symbol: string;
    long_pct: number;
    short_pct: number;
  };
  cvd?: CVDData;
  fear_greed?: FearGreedData;
  signal_score_detail?: SignalScore;
}