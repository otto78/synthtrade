/**
 * Opportunity Feed Component
 * Shows real-time trading opportunities detected by AI.
 * Polls backend every 5m with switchMap to avoid race conditions.
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { NgFor, NgIf, UpperCasePipe } from '@angular/common';
import { Subscription, timer } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { OpportunityApiService } from '../services/opportunity-api.service';
import { Opportunity, OpportunityUrgency } from '../models/opportunity.model';

@Component({
  selector: 'app-opportunity-feed',
  standalone: true,
  imports: [NgFor, NgIf, UpperCasePipe],
  template: `
    <div class="opportunity-feed">
      <span class="panel-title">Opportunity Feed</span>
      <div class="title-hr"></div>

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
          <div class="opp-actions">
            <button class="btn-action watch" (click)="watchOpp(opp)">Watch</button>
            <button class="btn-action ignore" (click)="ignoreOpp(opp)">Ignore</button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .opportunity-feed { padding: 12px; }
    .panel-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
    .title-hr { height: 1px; background: rgba(234,236,239,0.08); margin: 10px 0 12px 0; }
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
    .opp-actions { display: flex; gap: 4px; margin-top: 6px; }
    .btn-action { padding: 2px 6px; border-radius: 3px; font-size: 10px; border: none; cursor: pointer; font-weight: 600; }
    .watch { background: rgba(38, 166, 154, 0.2); color: var(--accent-success, #26a69a); }
    .ignore { background: rgba(239, 83, 80, 0.2); color: var(--accent-danger, #ef5350); }
  `],
})
export class OpportunityFeedComponent implements OnInit, OnDestroy {
  opportunities: Opportunity[] = [];
  private sub = new Subscription();
  /** Counter to track how many times we've successfully fetched opportunities */
  private fetchCount = 0;

  constructor(
    private opportunityApi: OpportunityApiService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    // Poll every 5 minutes, using switchMap to cancel previous HTTP call if still in-flight
    this.sub.add(
      timer(0, 300_000).pipe(
        switchMap(() =>
          this.opportunityApi.getOpportunities({ limit: 50 }).pipe(
            catchError((err) => {
              console.error('Opportunities load error:', err);
              return []; // Return empty array on error so the stream doesn't die
            })
          )
        )
      ).subscribe((data: Opportunity[]) => {
        this.fetchCount++;
        this.opportunities = data.slice(0, 20); // Keep max 20
        // console.log(`[OpportunityFeed] Fetched ${data.length} opportunities (fetch #${this.fetchCount})`);
        // Force change detection — Angular OnPush is not used but ensure UI update
        this.cdr.detectChanges();
      })
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

  watchOpp(opp: Opportunity): void {
    if (!opp.id) return;
    this.opportunityApi.watchOpportunity(opp.id).subscribe({
      next: () => {
        // console.log(`[OpportunityFeed] Watched opportunity: ${opp.title}`);
        this.loadOpportunities();
      },
      error: (err: Error) => console.error('Watchlist add failed:', err)
    });
  }

  ignoreOpp(opp: Opportunity): void {
    if (!opp.id) return;
    this.opportunityApi.ignoreOpportunity(opp.id).subscribe({
      next: () => {
        // console.log(`[OpportunityFeed] Ignored opportunity: ${opp.title}`);
        this.loadOpportunities();
      },
      error: (err: Error) => console.error('Ignore failed:', err)
    });
  }

  /** Force a manual refresh */
  private loadOpportunities(): void {
    this.opportunityApi.getOpportunities().subscribe({
      next: (data: Opportunity[]) => {
        this.opportunities = data.slice(0, 20);
        this.cdr.detectChanges();
      },
      error: (err: Error) => {
        console.error('Opportunities load error:', err);
      }
    });
  }
}