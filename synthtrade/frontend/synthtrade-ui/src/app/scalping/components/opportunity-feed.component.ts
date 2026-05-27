/**
 * Opportunity Feed Component
 * Shows real-time trading opportunities detected by AI.
 * Polls backend every 60s (TASK-810 will add WebSocket streaming).
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { NgFor, NgIf, UpperCasePipe } from '@angular/common';
import { Subscription, interval } from 'rxjs';
import { OpportunityApiService } from '../services/opportunity-api.service';
import { Opportunity, OpportunityUrgency } from '../models/opportunity.model';

@Component({
  selector: 'app-opportunity-feed',
  standalone: true,
  imports: [NgFor, NgIf, UpperCasePipe],
  template: `
    <div class="opportunity-feed">
      <h3>Opportunity Feed</h3>

      <div *ngIf="opportunities.length === 0" class="empty-state">
        No opportunities yet
      </div>

      <div class="opportunity-list">
        <div *ngFor="let opp of opportunities" class="opportunity-item"
             [class.high]="isHigh(opp.urgency)"
             [class.medium]="isMedium(opp.urgency)">
          <div class="opp-header">
            <span class="opp-urgency" [class]="opp.urgency">{{ opp.urgency | uppercase }}</span>
            <span class="opp-category">{{ opp.category }}</span>
          </div>
          <div class="opp-title">{{ opp.title }}</div>
          <div class="opp-meta">
            <span *ngIf="opp.symbol" class="opp-symbol">{{ opp.symbol }}</span>
            <span class="opp-source">{{ opp.source }}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .opportunity-feed { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .empty-state { padding: 20px; text-align: center; color: var(--text-secondary, #848E9C); font-size: 12px; }
    .opportunity-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
    .opportunity-item { padding: 8px; border-radius: 4px; background: var(--bg-elevated); border-left: 3px solid var(--text-secondary); }
    .opportunity-item.high { border-left-color: var(--color-sell, #F6465D); }
    .opportunity-item.medium { border-left-color: var(--accent-warning, #ffb74d); }
    .opp-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
    .opp-urgency { font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
    .opp-urgency.high { background: rgba(246,70,93,0.15); color: #F6465D; }
    .opp-urgency.medium { background: rgba(255,183,77,0.15); color: #ffb74d; }
    .opp-urgency.low { background: rgba(132,142,156,0.15); color: #848E9C; }
    .opp-category { font-size: 10px; color: var(--text-secondary, #848E9C); }
    .opp-title { font-size: 12px; color: var(--text-primary, #EAECEF); margin-bottom: 4px; }
    .opp-meta { display: flex; gap: 8px; align-items: center; }
    .opp-symbol { font-size: 10px; font-weight: 600; color: var(--accent-primary, #F0B90B); font-family: monospace; }
    .opp-source { font-size: 10px; color: var(--text-secondary, #848E9C); }
  `],
})
export class OpportunityFeedComponent implements OnInit, OnDestroy {
  opportunities: Opportunity[] = [];
  private sub = new Subscription();

  constructor(private opportunityApi: OpportunityApiService) {}

  ngOnInit(): void {
    this.loadOpportunities();
    // Poll every 60 seconds
    this.sub.add(
      interval(60_000).subscribe(() => this.loadOpportunities())
    );
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  /** Type-safe helpers for template comparisons */
  isHigh(urgency: OpportunityUrgency): boolean {
    return urgency === 'HIGH';
  }

  isMedium(urgency: OpportunityUrgency): boolean {
    return urgency === 'MEDIUM';
  }

  private loadOpportunities(): void {
    this.opportunityApi.getOpportunities().subscribe({
      next: (data: Opportunity[]) => {
        this.opportunities = data.slice(0, 20); // Keep max 20
      },
      error: (err: Error) => {
        console.error('Opportunities load error:', err);
      }
    });
  }
}