/**
 * Opportunity Feed Component
 * Real-time AI-classified trading opportunities
 */

import { Component } from '@angular/core';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'app-opportunity-feed',
  standalone: true,
  imports: [DatePipe],
  template: `
    <div class="feed">
      <h3>Opportunities</h3>

      <div class="opportunity-list">
        <div class="opportunity-item" *ngFor="let opp of opportunities">
          <div class="header">
            <span class="urgency" [class.high]="opp.urgency === 'high'">
              {{ opp.urgency }}
            </span>
            <span class="time">{{ opp.detected_at | date:'shortTime' }}</span>
          </div>
          <div class="title">{{ opp.title }}</div>
          <div class="meta">
            <span class="category">{{ opp.category }}</span>
            <span class="symbol" *ngIf="opp.symbol">{{ opp.symbol }}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .feed {
      padding: 12px;
      max-height: 300px;
      overflow-y: auto;
    }
    h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: var(--text-secondary);
    }
    .opportunity-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .opportunity-item {
      padding: 8px;
      background: var(--bg-elevated, #0D1117);
      border-radius: 4px;
      font-size: 12px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
    }
    .urgency {
      padding: 2px 6px;
      border-radius: 2px;
      font-size: 10px;
      background: var(--text-secondary);
      color: var(--bg-surface);
    }
    .urgency.high {
      background: var(--accent-primary, #F0B90B);
    }
    .time {
      color: var(--text-secondary);
    }
    .title {
      font-weight: 500;
      margin-bottom: 4px;
    }
    .meta {
      display: flex;
      gap: 8px;
      font-size: 10px;
      color: var(--text-secondary);
    }
  `],
})
export class OpportunityFeedComponent {
  opportunities = [
    {
      title: 'New BTC listing detection',
      category: 'new_listing',
      urgency: 'high',
      symbol: 'BTC',
      detected_at: new Date().toISOString(),
    },
  ];
}