/**
 * Opportunity Feed Component
 */

import { Component, OnInit } from '@angular/core';
import { DatePipe, NgForOf, NgIf } from '@angular/common';
import { OpportunityApiService } from '../services/opportunity-api.service';
import { Opportunity } from '../models/opportunity.model';

@Component({
  selector: 'app-opportunity-feed',
  standalone: true,
  imports: [DatePipe, NgForOf, NgIf],
  template: `
    <div class="feed">
      <h3>Opportunities</h3>
      <div *ngIf="!opportunities.length" class="empty">No opportunities yet</div>
      <div class="opportunity-item" *ngFor="let opp of opportunities">
        <div class="header">
          <span class="urgency" [class.high]="opp.urgency === 'high'">{{ opp.urgency }}</span>
          <span class="time">{{ opp.detected_at | date:'shortTime' }}</span>
        </div>
        <div class="title">{{ opp.title }}</div>
      </div>
    </div>
  `,
  styles: [`
    .feed { padding: 12px; max-height: 300px; overflow-y: auto; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .empty { color: var(--text-secondary); font-size: 12px; padding: 8px; }
    .opportunity-item { padding: 8px; background: var(--bg-elevated); border-radius: 4px; font-size: 12px; margin-bottom: 8px; }
    .header { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .urgency { padding: 2px 6px; border-radius: 2px; font-size: 10px; background: var(--text-secondary); color: var(--bg-surface); }
    .urgency.high { background: var(--accent-primary, #F0B90B); }
    .title { font-weight: 500; }
  `],
})
export class OpportunityFeedComponent implements OnInit {
  opportunities: Opportunity[] = [];

  constructor(private oppApi: OpportunityApiService) {}

  ngOnInit(): void {
    this.loadOpportunities();
  }

  private loadOpportunities(): void {
    this.oppApi.getOpportunities({ limit: 50 }).subscribe({
      next: (data) => this.opportunities = data,
      error: () => {}
    });
  }
}