/**
 * Opportunity Models for Scalping Dashboard
 */

export type OpportunityCategory =
  | 'listing'
  | 'launchpool'
  | 'news'
  | 'whale'
  | 'airdrop'
  | 'staking'
  | 'delisting'
  | 'other';

export type OpportunityUrgency = 'HIGH' | 'MEDIUM' | 'LOW';

export interface Opportunity {
  id: string;
  symbol?: string;
  category: OpportunityCategory;
  urgency: OpportunityUrgency;
  source: string;
  title: string;
  description?: string;
  url?: string;
  is_tradeable: boolean;
  confidence_score?: number;
  published_at?: string;
  created_at: string;
  is_watched: boolean;
  is_ignored: boolean;
  time_sensitive?: boolean;
  user_action?: 'watched' | 'ignored' | 'acted';
}