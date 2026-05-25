/**
 * Opportunity Models for Scalping Dashboard
 */

export type OpportunityCategory =
  | 'new_listing'
  | 'price_alert'
  | 'whale_movement'
  | 'news_sentiment'
  | 'technical_breakout';

export type OpportunityUrgency = 'low' | 'medium' | 'high';

export interface Opportunity {
  id: string;
  source: string;
  category: OpportunityCategory;
  urgency: OpportunityUrgency;
  scalping_opportunity: boolean;
  title: string;
  action?: string;
  symbol?: string;
  expected_volatility?: string;
  time_sensitive: boolean;
  url?: string;
  detected_at: string;
  user_action?: 'watched' | 'ignored' | 'acted';
}