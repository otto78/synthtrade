/**
 * Scalping Dashboard Component - Main page
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { MarketIntelPanelComponent } from './market-intel-panel.component';
import { SessionControlsComponent } from './session-controls.component';
import { PositionTickerComponent } from './position-ticker.component';
import { LiveChartComponent } from './live-chart.component';
import { StrategyPanelComponent } from './strategy-panel.component';
import { TradeLogComponent } from './trade-log.component';
import { PerformancePanelComponent } from './performance-panel.component';
import { SupervisorLogComponent } from './supervisor-log.component';
import { RiskControlsComponent } from './risk-controls.component';
import { ScalpingWsService, WsConnectionStatus } from '../services/scalping-ws.service';
import { SessionApiService } from '../services/session-api.service';
import { Subscription } from 'rxjs';
import { NgFor, NgIf } from '@angular/common';

interface ErrorToast {
  id: number;
  message: string;
  code: string;
}

@Component({
  selector: 'app-scalping-dashboard',
  standalone: true,
  imports: [
    MarketIntelPanelComponent,
    SessionControlsComponent,
    PositionTickerComponent,
    LiveChartComponent,
    StrategyPanelComponent,
    TradeLogComponent,
    PerformancePanelComponent,
    SupervisorLogComponent,
    RiskControlsComponent,
    NgFor,
    NgIf,
  ],
  template: `
    <div class="scalping-dashboard">

      <!-- WS Reconnect Banner -->
      <div class="ws-banner ws-banner--connecting" *ngIf="wsStatus === 'connecting'">
        <span class="ws-spinner"></span>
        <span>Connessione al server in corso...</span>
      </div>
      <div class="ws-banner ws-banner--disconnected" *ngIf="wsStatus === 'disconnected'">
        <span class="ws-icon">⚡</span>
        <span>Connessione WebSocket persa — riconnessione automatica in corso...</span>
      </div>
      <div class="ws-banner ws-banner--reconnected" *ngIf="showReconnectedFlash">
        <span class="ws-icon">✅</span>
        <span>Connessione ripristinata</span>
      </div>

      <!-- Error Toast Notifications -->
      <div class="error-toasts" *ngIf="errorToasts.length > 0">
        <div class="error-toast" *ngFor="let toast of errorToasts" [attr.data-id]="toast.id">
          <span class="error-icon">⚠️</span>
          <span class="error-msg">{{ toast.message }}</span>
          <button class="dismiss-btn" (click)="dismissToast(toast.id)">✕</button>
        </div>
      </div>

      <div class="dashboard-grid">
        <!-- ── NOTA OPPORTUNITY FEED (2026-06-19) ──────────────────────────────────
             Il componente <app-opportunity-feed> è stato rimosso dalla dashboard.
             Motivo: i dati del feed (BinanceRSS, CoinGecko, WhaleAlert, News)
             sono puramente informativi e NON influenzano le decisioni di trading:
             - Non vengono letti dal Supervisor AI
             - Non entrano nel SignalAggregator
             - Le notizie non sono symbol-specific (es. una notizia su BONK non
               dice nulla sul comportamento di BNBUSDC)
             - I segnali whale/sentiment rilevanti sono già coperti dai collector
               intelligence (WhaleCollector, SentimentCollector)

             Il job di polling backend (opportunity_monitor_job) è stato disabilitato
             contestualmente in app/scheduler/jobs.py.

             Per reintrodurlo:
             1. Aggiungere qui: <app-opportunity-feed class="card"></app-opportunity-feed>
             2. Aggiungere OpportunityFeedComponent agli imports del component
             3. Decommentare opportunity_monitor_job in jobs.py
             4. Valutare collegamento con context Supervisor per simbolo attivo
        ─────────────────────────────────────────────────────────────────────── -->
        <!-- Riga 1 -->
        <app-session-controls class="card"></app-session-controls>
        <app-position-ticker class="card"></app-position-ticker>
        <app-live-chart class="card chart-card"></app-live-chart>
        <!-- Riga 2: Performance (doppia larghezza) + Strategy -->
        <app-performance-panel class="card perf-card"></app-performance-panel>
        <app-strategy-panel class="card"></app-strategy-panel>
        <app-supervisor-log class="card"></app-supervisor-log>
        <!-- Riga 3 -->
        <app-trade-log class="card chart-card"></app-trade-log>
        <app-market-intel-panel class="card"></app-market-intel-panel>
        <app-risk-controls class="card"></app-risk-controls>
      </div>
    </div>
  `,
  styles: [`
    .scalping-dashboard { padding: 20px; }
    .dashboard-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; }
    .card { background: var(--bg-surface, #161B22); border: 1px solid var(--border-default, rgba(234,236,239,0.1)); border-radius: 8px; }
    .chart-card { grid-column: span 2; }
    .perf-card { grid-column: span 2; }

    /* WS Status Banners */
    .ws-banner {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 10px;
      animation: slideIn 0.25s ease;
    }
    .ws-banner--connecting {
      background: rgba(240, 185, 11, 0.12);
      border: 1px solid rgba(240, 185, 11, 0.35);
      color: #F0B90B;
    }
    .ws-banner--disconnected {
      background: rgba(239, 83, 80, 0.12);
      border: 1px solid rgba(239, 83, 80, 0.35);
      color: #ef9a9a;
    }
    .ws-banner--reconnected {
      background: rgba(38, 166, 154, 0.12);
      border: 1px solid rgba(38, 166, 154, 0.35);
      color: #26a69a;
    }
    .ws-spinner {
      display: inline-block;
      width: 12px;
      height: 12px;
      border: 2px solid rgba(240,185,11,0.3);
      border-top-color: #F0B90B;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      flex-shrink: 0;
    }
    .ws-icon { font-size: 14px; flex-shrink: 0; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Error Toasts */
    .error-toasts {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }
    .error-toast {
      display: flex;
      align-items: center;
      gap: 10px;
      background: rgba(239, 83, 80, 0.15);
      border: 1px solid rgba(239, 83, 80, 0.5);
      border-radius: 6px;
      padding: 10px 14px;
      font-size: 13px;
      color: #ef9a9a;
      animation: slideIn 0.2s ease;
    }
    .error-icon { font-size: 15px; flex-shrink: 0; }
    .error-msg { flex: 1; line-height: 1.4; }
    .dismiss-btn {
      background: none;
      border: none;
      color: rgba(239,83,80,0.7);
      cursor: pointer;
      font-size: 14px;
      padding: 0 4px;
      flex-shrink: 0;
      line-height: 1;
    }
    .dismiss-btn:hover { color: #ef5350; }
    @keyframes slideIn {
      from { opacity: 0; transform: translateY(-6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `],
})
export class ScalpingDashboardComponent implements OnInit, OnDestroy {
  errorToasts: ErrorToast[] = [];
  wsStatus: WsConnectionStatus = 'disconnected';
  showReconnectedFlash = false;

private _toastCounter = 0;
   private _sub = new Subscription();
   private _prevStatus: WsConnectionStatus = 'disconnected';
   private _reconnectedTimer: ReturnType<typeof setTimeout> | null = null;
   private _httpErrorCallback = (e: Event) => {
     const detail = (e as CustomEvent).detail;
     if (detail?.message && !this.errorToasts.some(t => t.message === detail.message)) {
       this._showError(detail.message, detail.code || 'HTTP_ERROR');
       this.cdr.markForCheck();
     }
   };

   constructor(
    private wsService: ScalpingWsService,
    private sessionApi: SessionApiService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.wsService.connect();

    // Track WS connection status for banner
    this._sub.add(
      this.wsService.connectionStatus$.subscribe((status) => {
        // Mostra il flash "Connessione ripristinata" se siamo tornati da disconnected/connecting
        if (
          status === 'connected' &&
          (this._prevStatus === 'disconnected' || this._prevStatus === 'connecting') &&
          this._prevStatus !== 'disconnected' // Non mostrarlo alla prima connessione
        ) {
          this._showReconnectedFlash();
        }
        this._prevStatus = status;
        this.wsStatus = status;
        this.cdr.markForCheck();
      })
    );

    // Listen for backend errors
    this._sub.add(
      this.wsService.error$.subscribe((err) => {
        this._showError(err.message, err.code);
      })
    );

    // Sync session state from WebSocket (e.g. live balance updates)
    this._sub.add(
      this.wsService.sessionRestored$.subscribe((session) => {
this.sessionApi.updateSession(session);
     })
     );

// Listen for HTTP errors via custom event (fallback when WS error races with HTTP response)
     window.addEventListener('scalping-error', this._httpErrorCallback as EventListener);
   }

ngOnDestroy(): void {
    this.wsService.disconnect();
    this._sub.unsubscribe();
    if (this._reconnectedTimer) clearTimeout(this._reconnectedTimer);
    window.removeEventListener('scalping-error', this._httpErrorCallback as EventListener);
  }

  dismissToast(id: number): void {
    this.errorToasts = this.errorToasts.filter(t => t.id !== id);
  }

  private _showError(message: string, code: string): void {
    const id = ++this._toastCounter;
    this.errorToasts.push({ id, message, code });
    // Auto-dismiss after 8 seconds
    setTimeout(() => this.dismissToast(id), 8000);
  }

  private _showReconnectedFlash(): void {
    this.showReconnectedFlash = true;
    if (this._reconnectedTimer) clearTimeout(this._reconnectedTimer);
    this._reconnectedTimer = setTimeout(() => {
      this.showReconnectedFlash = false;
      this.cdr.markForCheck();
    }, 3000);
  }
}