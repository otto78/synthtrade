/**
 * Session Controls Component — redesigned
 * Allows symbol + strategy selection before start.
 * Paper/Live mode is global (top bar), not shown here.
 */
import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { NgIf, NgClass, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SessionApiService } from '../services/session-api.service';
import { ScalpingSession } from '../models/session.model';

@Component({
  selector: 'app-session-controls',
  standalone: true,
  imports: [NgIf, NgClass, DatePipe, FormsModule],
  template: `
    <div class="session-card">

      <!-- IDLE: config + start -->
      <ng-container *ngIf="!session || session.status === 'idle'">
        <div class="card-header">
          <span class="dot idle"></span>
          <span class="title">Nuova Sessione</span>
        </div>

        <div class="config-grid">
          <div class="field">
            <label>Simbolo</label>
            <select [(ngModel)]="selectedSymbol" class="select">
              <option value="BTCUSDT">BTC / USDT</option>
              <option value="ETHUSDT">ETH / USDT</option>
              <option value="SOLUSDT">SOL / USDT</option>
              <option value="BNBUSDT">BNB / USDT</option>
              <option value="DOGEUSDT">DOGE / USDT</option>
            </select>
          </div>

          <div class="field">
            <label>Strategia</label>
            <select [(ngModel)]="selectedStrategy" class="select">
              <option value="ema_cross">EMA Cross</option>
              <option value="rsi_bollinger">RSI + Bollinger</option>
              <option value="vwap_reversion">VWAP Reversion</option>
              <option value="scalping_v2">Scalping v2 (auto)</option>
            </select>
          </div>
        </div>

        <button class="btn-start" (click)="startSession()" [disabled]="loading">
          <span class="start-icon">▶</span>
          {{ loading ? 'Avvio...' : 'Avvia Sessione' }}
        </button>
      </ng-container>

      <!-- RUNNING / PAUSED -->
      <ng-container *ngIf="session && session.status !== 'idle'">
        <div class="card-header">
          <span class="dot" [ngClass]="session.status"></span>
          <span class="title">{{ session.symbol }}</span>
          <span class="status-pill" [ngClass]="session.status">
            {{ session.status === 'running' ? 'LIVE' : 'PAUSED' }}
          </span>
        </div>

        <div class="session-meta">
          <div class="meta-item">
            <span class="meta-label">Strategia</span>
            <span class="meta-value">{{ formatStrategy(session.strategy) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Avviata</span>
            <span class="meta-value">{{ session.started_at | date:'HH:mm:ss' }}</span>
          </div>
        </div>

        <div class="action-row">
          <button
            *ngIf="session.status === 'running'"
            class="btn-action pause"
            (click)="pauseSession()">
            ⏸ Pausa
          </button>
          <button
            *ngIf="session.status === 'paused'"
            class="btn-action resume"
            (click)="resumeSession()">
            ▶ Resume
          </button>
          <button class="btn-action stop" (click)="stopSession()">
            ⏹ Stop
          </button>
        </div>
      </ng-container>

    </div>
  `,
  styles: [`
    .session-card {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      height: 100%;
    }

    /* Header */
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .dot.idle { background: #555; }
    .dot.running {
      background: #26a69a;
      box-shadow: 0 0 6px #26a69a99;
      animation: pulse 2s infinite;
    }
    .dot.paused { background: #ffb74d; }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .title {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-primary);
      flex: 1;
    }
    .status-pill {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.5px;
      padding: 3px 8px;
      border-radius: 20px;
    }
    .status-pill.running {
      background: rgba(38,166,154,0.15);
      color: #26a69a;
      border: 1px solid rgba(38,166,154,0.3);
    }
    .status-pill.paused {
      background: rgba(255,183,77,0.15);
      color: #ffb74d;
      border: 1px solid rgba(255,183,77,0.3);
    }

    /* Config */
    .config-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .field {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-secondary);
      font-weight: 500;
    }
    .select {
      padding: 7px 10px;
      border-radius: 6px;
      background: rgba(255,255,255,0.05);
      color: var(--text-primary);
      border: 1px solid rgba(255,255,255,0.1);
      font-size: 12px;
      cursor: pointer;
      outline: none;
      transition: border-color 0.2s;
    }
    .select:focus { border-color: var(--accent-primary, #F0B90B); }
    .select option {
      background-color: #161b22;
      color: var(--text-primary);
    }

    /* Start button */
    .btn-start {
      width: 100%;
      padding: 10px;
      border-radius: 8px;
      background: linear-gradient(135deg, #F0B90B, #f5a623);
      color: #000;
      font-weight: 700;
      font-size: 13px;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: opacity 0.2s, transform 0.1s;
    }
    .btn-start:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
    .btn-start:active:not(:disabled) { transform: translateY(0); }
    .btn-start:disabled { opacity: 0.5; cursor: not-allowed; }
    .start-icon { font-size: 11px; }

    /* Session meta */
    .session-meta {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .meta-item {
      background: rgba(255,255,255,0.04);
      border-radius: 6px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .meta-label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-secondary);
    }
    .meta-value {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-primary);
    }

    /* Action buttons */
    .action-row {
      display: flex;
      gap: 8px;
    }
    .btn-action {
      flex: 1;
      padding: 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      border: none;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .btn-action:hover { opacity: 0.85; }
    .btn-action.pause { background: rgba(255,183,77,0.15); color: #ffb74d; border: 1px solid rgba(255,183,77,0.3); }
    .btn-action.resume { background: rgba(38,166,154,0.15); color: #26a69a; border: 1px solid rgba(38,166,154,0.3); }
    .btn-action.stop { background: rgba(239,83,80,0.12); color: #ef5350; border: 1px solid rgba(239,83,80,0.25); }
  `],
})
export class SessionControlsComponent implements OnInit {
  session: ScalpingSession | null = null;
  selectedSymbol = 'BTCUSDT';
  selectedStrategy = 'scalping_v2';
  loading = false;

  constructor(
    private sessionApi: SessionApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.sessionApi.session$.subscribe((data) => {
      this.session = data;
      this.cdr.detectChanges();
    });
    this.sessionApi.getStatus().subscribe();
  }

  startSession(): void {
    this.loading = true;
    this.sessionApi.start('paper', this.selectedStrategy, this.selectedSymbol).subscribe({
      next: (data: ScalpingSession) => {
        this.session = data;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err: Error) => {
        console.error('[SessionControls] FAILED:', err);
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  stopSession(): void {
    if (!this.session) return;
    this.sessionApi.stop().subscribe({
      next: () => { this.session = null; this.cdr.detectChanges(); },
      error: (err: Error) => console.error('Failed to stop session:', err)
    });
  }

  pauseSession(): void {
    if (!this.session) return;
    this.sessionApi.pause().subscribe({
      next: (data: ScalpingSession) => { this.session = data; this.cdr.detectChanges(); },
      error: (err: Error) => console.error('Failed to pause session:', err)
    });
  }

  resumeSession(): void {
    if (!this.session) return;
    this.sessionApi.resume().subscribe({
      next: (data: ScalpingSession) => { this.session = data; this.cdr.detectChanges(); },
      error: (err: Error) => console.error('Failed to resume session:', err)
    });
  }

  formatStrategy(s: string): string {
    const map: Record<string, string> = {
      ema_cross: 'EMA Cross',
      rsi_bollinger: 'RSI + Bollinger',
      vwap_reversion: 'VWAP Reversion',
      scalping_v2: 'Scalping v2',
    };
    return map[s] ?? s;
  }
}
