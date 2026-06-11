/**
 * Session Controls Component — redesigned
 * Allows symbol + strategy + trade value selection before start.
 * Paper/Live mode is global (top bar), not shown here.
 */
import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { NgIf, NgClass, NgFor, DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SessionApiService } from '../services/session-api.service';
import { BinanceSymbolsService } from '../services/binance-symbols.service';
import { ScalpingSession } from '../models/session.model';
import { ConfigService } from '../../core/services/config.service';

@Component({
  selector: 'app-session-controls',
  standalone: true,
  imports: [NgIf, NgClass, NgFor, DatePipe, DecimalPipe, FormsModule],
  template: `
    <div class="session-card">

      <!-- IDLE: Session header + config -->
      <ng-container *ngIf="!session || session.status === 'idle'">
        <div class="session-header">
          <span class="panel-title">Session</span>
        </div>
        <div class="title-hr"></div>
        <div class="session-id-row" *ngIf="sessionId">
          <span class="session-id">{{ sessionId }}</span>
        </div>

        <div class="config-grid">
          <div class="field">
            <label>Simbolo</label>
            <div class="symbol-selector">
              <input 
                type="text" 
                [(ngModel)]="symbolFilter" 
                placeholder="Cerca simbolo..."
                class="search-input"
                (focus)="showSymbolDropdown = true"
              />
              <div class="dropdown" *ngIf="showSymbolDropdown && filteredSymbols.length > 0">
                <div 
                  *ngFor="let sym of filteredSymbols.slice(0, 50)" 
                  class="dropdown-item"
                  (click)="selectSymbol(sym)"
                  [class.selected]="sym === selectedSymbol"
                >
                  {{ sym }}
                </div>
              </div>
            </div>
            <div class="selected-symbol" *ngIf="selectedSymbol">
              Selezionato: <strong>{{ selectedSymbol }}</strong>
            </div>
          </div>

          <div class="field">
            <label>Strategia</label>
            <select [(ngModel)]="selectedStrategy" class="select">
              <option value="ema_cross">EMA Cross</option>
              <option value="rsi_bollinger">RSI con Bollinger</option>
              <option value="stoch_rsi_bb_squeeze">Stoch RSI con Bollinger Bands Squeeze</option>
              <option value="vwap_reversion">VWAP Reversion</option>
              <option value="momentum_base">Momentum Base</option>
              <option value="scalping_v2">Scalping</option>
            </select>
          </div>

          <div class="field">
            <label>Valore Trade ($)</label>
            <div class="trade-value-row">
              <input
                type="number"
                [(ngModel)]="tradeValue"
                min="1"
                step="10"
                class="trade-input"
                placeholder="100"
              />
              <span class="trade-currency">USDT</span>
            </div>
            <div class="trade-hint">Importo per singolo trade</div>
          </div>
        </div>

        <button class="btn-start" (click)="startSession()" [disabled]="loading">
          <span class="start-icon">▶</span>
          {{ loading ? 'Avvio...' : 'Avvia Sessione' }}
        </button>
      </ng-container>

      <!-- RUNNING / PAUSED -->
      <ng-container *ngIf="session && session.status !== 'idle'">
        <div class="session-header">
          <span class="panel-title">Session</span>
        </div>
        <div class="title-hr"></div>

        <div class="session-meta">
          <div class="meta-item">
            <span class="meta-label">Simbolo</span>
            <span class="meta-value">{{ session.symbol }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Stato</span>
            <span class="meta-value" [ngClass]="session.status">
              {{ session.status === 'running' ? 'LIVE' : 'PAUSED' }}
            </span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Saldo {{ session.mode === 'live' ? 'Free' : 'Paper' }}</span>
            <span class="meta-value" [class.live-val]="session.mode === 'live'">
              {{ (session.mode === 'live' ? (session.live_balance ?? session.paper_balance) : session.paper_balance) | number:'1.2-2' }}
              {{ getQuoteAsset() }}
            </span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Avviata</span>
            <span class="meta-value">{{ session.started_at | date:'HH:mm:ss' }}</span>
          </div>
        </div>

        <!-- Trade Value edit while session is running -->
        <div class="field trade-live">
          <label>Valore Trade ($) <span class="hint-inline">· dal prossimo trade</span></label>
          <div class="trade-value-row">
            <input
              type="number"
              [(ngModel)]="tradeValue"
              min="1"
              step="10"
              class="trade-input"
              placeholder="100"
            />
            <span class="trade-currency">{{ getQuoteAsset() }}</span>
            <button class="btn-apply" (click)="applyTradeValue()" [disabled]="applyingTradeValue">
              {{ applyingTradeValue ? '...' : '✓' }}
            </button>
          </div>
          <div class="trade-hint" *ngIf="tradeValueApplied">
            ✅ Applicato — prossimo trade: {{ tradeValue }}$
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
          <button class="btn-action stop" (click)="stopSession()" [disabled]="isStopping">
            {{ isStopping ? 'Arresto...' : '⏹ Stop' }}
          </button>
        </div>
        <div class="session-id-row" *ngIf="sessionId">
          <span class="session-id">{{ sessionId }}</span>
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

    /* Session header */
    .panel-title {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .session-header {
      display: flex;
      align-items: baseline;
      gap: 10px;
    }
    .session-id {
      font-size: 11px;
      font-weight: 400;
      color: var(--text-secondary);
      opacity: 0.7;
      font-family: monospace;
    }
    .session-id-row { margin-bottom: 4px; }
    .title-hr {
      height: 1px;
      background: rgba(234,236,239,0.08);
      margin: -6px 0 12px 0;
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
      display: flex;
      flex-direction: column;
      gap: 12px;
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
    .hint-inline {
      text-transform: none;
      opacity: 0.6;
      font-size: 9px;
      letter-spacing: 0;
    }
    .select {
      padding: 8px 12px;
      border-radius: 6px;
      background: rgba(255,255,255,0.05);
      color: var(--text-primary);
      border: 1px solid rgba(234,236,239,0.1);
      font-size: 13px;
      cursor: pointer;
      outline: none;
      transition: all 0.2s;
      width: 100%;
    }
    .select:focus { 
      border-color: var(--accent-primary, #F0B90B);
      background: rgba(255,255,255,0.08);
    }
    .select option {
      background-color: #161b22;
      color: var(--text-primary);
    }

    /* Symbol selector */
    .symbol-selector {
      position: relative;
    }
    .search-input {
      width: 100%;
      padding: 8px 12px;
      border-radius: 6px;
      background: rgba(255,255,255,0.05);
      color: var(--text-primary);
      border: 1px solid rgba(234,236,239,0.1);
      font-size: 13px;
      outline: none;
      transition: all 0.2s;
    }
    .search-input:focus {
      border-color: var(--accent-primary, #F0B90B);
      background: rgba(255,255,255,0.08);
    }
    .dropdown {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      max-height: 200px;
      overflow-y: auto;
      background: #1c2128;
      border: 1px solid rgba(234,236,239,0.15);
      border-radius: 6px;
      margin-top: 4px;
      z-index: 100;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .dropdown-item {
      padding: 8px 12px;
      font-size: 12px;
      cursor: pointer;
      transition: background 0.15s;
    }
    .dropdown-item:hover {
      background: rgba(240,185,11,0.1);
    }
    .dropdown-item.selected {
      background: rgba(240,185,11,0.2);
      color: #F0B90B;
      font-weight: 600;
    }
    .selected-symbol {
      font-size: 11px;
      color: var(--text-secondary);
      margin-top: 6px;
    }
    .selected-symbol strong {
      color: var(--accent-primary, #F0B90B);
    }

    /* Trade Value field */
    .trade-value-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .trade-input {
      flex: 1;
      padding: 8px 12px;
      border-radius: 6px;
      background: rgba(255,255,255,0.05);
      color: var(--text-primary);
      border: 1px solid rgba(234,236,239,0.1);
      font-size: 13px;
      font-weight: 600;
      outline: none;
      transition: all 0.2s;
      min-width: 0;
    }
    .trade-input:focus {
      border-color: var(--accent-primary, #F0B90B);
      background: rgba(255,255,255,0.08);
    }
    .trade-currency {
      font-size: 11px;
      color: var(--text-secondary);
      font-weight: 500;
      white-space: nowrap;
    }
    .trade-hint {
      font-size: 10px;
      color: var(--text-secondary);
      opacity: 0.6;
    }
    .trade-live {
      background: rgba(240,185,11,0.04);
      border: 1px solid rgba(240,185,11,0.12);
      border-radius: 8px;
      padding: 10px 12px;
    }
    .btn-apply {
      padding: 8px 12px;
      border-radius: 6px;
      background: rgba(38,166,154,0.15);
      color: #26a69a;
      border: 1px solid rgba(38,166,154,0.3);
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }
    .btn-apply:hover:not(:disabled) {
      background: rgba(38,166,154,0.25);
    }
    .btn-apply:disabled { opacity: 0.5; cursor: not-allowed; }

    /* Start button */
    .btn-start {
      width: 100%;
      padding: 14px;
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
      gap: 8px;
      transition: opacity 0.2s, transform 0.1s;
      margin-top: 12px;
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
    .meta-value.live-val { color: var(--accent-success, #26a69a); }

    /* Action buttons */
    .action-row {
      display: flex;
      gap: 10px;
      margin-top: 8px;
    }
    .btn-action {
      flex: 1;
      padding: 16px 8px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .btn-action:hover { 
      opacity: 0.85; 
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .btn-action:active { transform: translateY(0); }
    .btn-action.pause { background: rgba(255,183,77,0.15); color: #ffb74d; border: 1px solid rgba(255,183,77,0.3); }
    .btn-action.resume { background: rgba(38,166,154,0.15); color: #26a69a; border: 1px solid rgba(38,166,154,0.3); }
    .btn-action.stop { background: rgba(239,83,80,0.12); color: #ef5350; border: 1px solid rgba(239,83,80,0.25); }
  `],
})
export class SessionControlsComponent implements OnInit {
  session: ScalpingSession | null = null;
  sessionId: string | null = null;
  selectedSymbol = 'BNBUSDC';
  selectedStrategy = 'momentum_base';
  
  /** Trade value: restore from localStorage or default 100 */
  tradeValue: number = (() => {
    try {
      const saved = localStorage.getItem('scalping_trade_value');
      if (saved !== null) {
        const parsed = parseFloat(saved);
        if (!isNaN(parsed) && parsed > 0) return parsed;
      }
    } catch {}
    return 100;
  })();
  
  applyingTradeValue = false;
  tradeValueApplied = false;
  isStopping = false;
  loading = false;
  
  // Symbol search
  allSymbols: string[] = [];
  symbolFilter = '';
  showSymbolDropdown = false;

  globalMode: string = 'test';

  constructor(
    private sessionApi: SessionApiService,
    private binanceSymbols: BinanceSymbolsService,
    private configService: ConfigService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.configService.getMode().subscribe(info => {
      this.globalMode = info.mode;
    });
    
    this.sessionApi.session$.subscribe((data) => {
      this.session = data;
      this.sessionId = data?.session_id || this.sessionId;
      // Sync tradeValue from session if available
      if (data?.trade_value) {
        this.tradeValue = data.trade_value;
      }
      this.cdr.detectChanges();
    });
    this.sessionApi.getStatus().subscribe();
    
    // Load all Binance symbols
    this.binanceSymbols.getSymbols().subscribe((symbols) => {
      this.allSymbols = symbols;
      this.cdr.detectChanges();
    });
    
    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.symbol-selector')) {
        this.showSymbolDropdown = false;
        this.cdr.detectChanges();
      }
    });
  }
  
  get filteredSymbols(): string[] {
    if (!this.symbolFilter) {
      return this.allSymbols.slice(0, 50);
    }
    return this.binanceSymbols.filterSymbols(this.allSymbols, this.symbolFilter);
  }
  
  selectSymbol(symbol: string): void {
    this.selectedSymbol = symbol;
    this.symbolFilter = symbol;
    this.showSymbolDropdown = false;
    // Immediately activate live chart preview with historical candles
    this.sessionApi.setPreviewSymbol(symbol);
    this.cdr.detectChanges();
  }

  /** Persist trade value to localStorage so it survives page reload */
  private saveTradeValue(): void {
    try {
      localStorage.setItem('scalping_trade_value', String(this.tradeValue));
    } catch {}
  }

  startSession(): void {
    this.loading = true;
    this.saveTradeValue();
    const executionMode = this.globalMode === 'live' ? 'live' : 'paper';
    this.sessionApi.start(executionMode, this.selectedStrategy, this.selectedSymbol, this.tradeValue).subscribe({
      next: (data: ScalpingSession) => {
        this.session = data;
        this.sessionId = data.session_id || null;
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

  applyTradeValue(): void {
    if (!this.session || this.applyingTradeValue) return;
    this.applyingTradeValue = true;
    this.tradeValueApplied = false;
    this.saveTradeValue();
    this.sessionApi.updateTradeValue(this.tradeValue).subscribe({
      next: () => {
        this.applyingTradeValue = false;
        this.tradeValueApplied = true;
        this.cdr.detectChanges();
        // Auto-hide confirmation after 3s
        setTimeout(() => {
          this.tradeValueApplied = false;
          this.cdr.detectChanges();
        }, 3000);
      },
      error: (err: Error) => {
        console.error('[SessionControls] updateTradeValue FAILED:', err);
        this.applyingTradeValue = false;
        this.cdr.detectChanges();
      }
    });
  }

  stopSession(): void {
    if (!this.session || this.isStopping) return;
    this.isStopping = true;
    this.sessionApi.stop().subscribe({
      next: () => { 
        this.session = null; 
        this.isStopping = false;
        this.cdr.detectChanges(); 
      },
      error: (err: Error) => {
        console.error('Failed to stop session:', err);
        this.isStopping = false;
        this.cdr.detectChanges();
      }
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
      rsi_bollinger: 'RSI con Bollinger',
      stoch_rsi_bb_squeeze: 'Stoch RSI con Bollinger Bands Squeeze',
      vwap_reversion: 'VWAP Reversion',
      momentum_base: 'Momentum Base',
      scalping_v2: 'Scalping',
    };
    return map[s] ?? s;
  }

  getQuoteAsset(): string {
    // Use session symbol first (when session is running), fallback to selectedSymbol
    const sym = (this.session?.symbol || this.selectedSymbol || '').toUpperCase();
    if (sym.endsWith('USDC')) return 'USDC';
    if (sym.endsWith('EUR')) return 'EUR';
    return 'USDT';
  }
}
