/**
 * Live Chart Component
 * Real-time candlestick chart using lightweight-charts
 */

import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ViewChild,
  ElementRef,
  Input,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { createChart, ColorType, ISeriesApi, UTCTimestamp, CrosshairMode, CandlestickData } from 'lightweight-charts';
import { ScalpingWsService } from '../services/scalping-ws.service';

import { NgIf, DecimalPipe } from '@angular/common';

import { Subscription, firstValueFrom } from 'rxjs';
import { filter } from 'rxjs/operators';
import { SessionApiService } from '../services/session-api.service';

/** Candle data returned by GET /api/scalping/candles/{symbol} */
interface CandleResponse {
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
}

@Component({
  selector: 'app-live-chart',
  standalone: true,
  template: `
    <div class="live-chart">
      <div class="chart-header">
        <h3>Live Chart</h3>
        <div class="chart-meta">
          <span class="symbol">{{ symbol }}</span>
          <span class="timeframe">1m</span>
          <span class="price-tag" *ngIf="lastPrice > 0">{{ lastPrice | number:'1.2-2' }}</span>
        </div>
      </div>
      <div #chartContainer class="chart-container"></div>
    </div>
  `,
  imports: [NgIf, DecimalPipe],
  styles: [`
    .live-chart { padding: 12px; display: flex; flex-direction: column; height: 100%; }
    .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    h3 { margin: 0; font-size: 13px; color: var(--text-secondary); font-weight: 500; }
    .chart-meta { display: flex; align-items: center; gap: 8px; }
    .symbol { font-size: 13px; color: var(--accent-primary, #F0B90B); font-weight: 700; }
    .timeframe { font-size: 10px; color: var(--text-secondary); background: rgba(240,185,11,0.1); padding: 2px 6px; border-radius: 3px; }
    .price-tag { font-size: 13px; color: #26a69a; font-weight: 600; font-variant-numeric: tabular-nums; }
    .chart-container { flex: 1; min-height: 280px; width: 100%; }
  `],
})
export class LiveChartComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('chartContainer', { static: true })
  chartContainer!: ElementRef<HTMLDivElement>;

  @Input() symbol: string = 'BNBUSDC';

  lastPrice = 0;

  private chart: ReturnType<typeof createChart> | null = null;
  private candleSeries: ISeriesApi<'Candlestick'> | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private sub = new Subscription();

  private readonly API_BASE = '/api/scalping';

  constructor(
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private http: HttpClient,
  ) {}

  ngOnInit(): void {
    // React to active session changes
    this.sub.add(
      this.sessionApi.session$.subscribe((session) => {
        if (!session || session.status === 'idle') {
          return;
        }
        const oldSymbol = this.symbol;
        this.symbol = session.symbol || this.symbol;
        this.lastPrice = 0;
        if (this.candleSeries && oldSymbol !== this.symbol) {
          this.candleSeries.setData([]);
        }
        // Always reload candles when chart exists — handles both symbol change
        // and page re-entry where chart was just recreated
        this._loadHistoryCandles();
      })
    );

    // React to preview symbol changes (user selects a symbol before starting session)
    // Only activate if there is no active session running
    this.sub.add(
      this.sessionApi.previewSymbol$.subscribe((previewSym) => {
        // Skip if session is active — session$ subscriber handles symbol changes
        const activeSession = this.sessionApi.getActiveSession();
        if (activeSession && activeSession.status !== 'idle') {
          return; // session is in control
        }
        if (previewSym && previewSym !== this.symbol) {
          this.symbol = previewSym;
          this.lastPrice = 0;
          if (this.candleSeries) {
            this.candleSeries.setData([]);
          }
          this._loadHistoryCandles();
        }
      })
    );
  }

  private async _loadHistoryCandles(): Promise<void> {
    if (!this.candleSeries) return;
    try {
      const candles = await firstValueFrom(
        this.http.get<CandleResponse[]>(`${this.API_BASE}/candles/${this.symbol}?limit=100`)
      );
      if (!candles || candles.length === 0) return;
      
      const chartData: CandlestickData[] = candles.map(c => ({
        time: (new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));
      
      this.candleSeries.setData(chartData);
      this.lastPrice = chartData[chartData.length - 1].close;
      if (this.chart) {
        this.chart.timeScale().scrollToRealTime();
      }
      console.log(`Loaded ${chartData.length} historical candles for ${this.symbol}`);
    } catch (e) {
      console.log('Failed to load historical candles:', e);
    }
  }

  ngAfterViewInit(): void {
    this._initChart();
    this._subscribeToCandles();
    this._setupResize();
    
    // Load historical candles now that chart is initialized.
    // Use the active session symbol if available, otherwise keep the default.
    const activeSession = this.sessionApi.getActiveSession();
    if (activeSession && activeSession.symbol && activeSession.status !== 'idle') {
      this.symbol = activeSession.symbol;
    }
    this._loadHistoryCandles();
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
    this.resizeObserver?.disconnect();
    if (this.chart) {
      try {
        this.chart.remove();
      } catch (e) {
        console.warn('Error removing chart:', e);
      }
      this.chart = null;
      this.candleSeries = null;
    }
  }

  private _initChart(): void {
    const el = this.chartContainer.nativeElement;
    this.chart = createChart(el, {
      width: el.clientWidth || 600,
      height: el.clientHeight || 280,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#8B9AB1',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.06)',
        scaleMargins: { top: 0.1, bottom: 0.1 },
        autoScale: true,
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.06)',
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: number) => {
          const d = new Date(time * 1000);
          const h = d.getHours().toString().padStart(2, '0');
          const m = d.getMinutes().toString().padStart(2, '0');
          return `${h}:${m}`;
        },
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true },
    });

    this.candleSeries = this.chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderDownColor: '#ef5350',
      borderUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      wickUpColor: '#26a69a',
    });
  }

  private _subscribeToCandles(): void {
    this.sub.add(
      this.ws.candle$.pipe(
        filter((candle): candle is NonNullable<typeof candle> => candle !== null)
      ).subscribe((candle) => {
        if (!this.candleSeries || !this.chart) return;
        
        // Filtra per simbolo (case-insensitive) — mostra solo candele del simbolo della sessione corrente
        if (candle.symbol.toUpperCase() !== this.symbol.toUpperCase()) {
          return;
        }
        
        try {
          const ts = (new Date(candle.timestamp).getTime() / 1000) as UTCTimestamp;
          this.candleSeries.update({
            time: ts,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
          });
          this.lastPrice = candle.close;
          // Auto-scroll to latest bar
          this.chart.timeScale().scrollToRealTime();
        } catch (e) {
          // If chart was disposed between the check and the call
          // console.log('Chart update skipped (likely disposed):', e);
        }
      })
    );
  }

  private _setupResize(): void {
    if (!this.chart) return;
    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (this.chart && width > 0) {
          try {
            this.chart.applyOptions({ width, height: Math.max(height, 200) });
          } catch (e) {
            // console.log('Chart resize skipped (likely disposed):', e);
          }
        }
      }
    });
    this.resizeObserver.observe(this.chartContainer.nativeElement);
  }
}