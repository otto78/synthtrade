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
import { createChart, ColorType, ISeriesApi, UTCTimestamp, CrosshairMode } from 'lightweight-charts';
import { ScalpingWsService } from '../services/scalping-ws.service';

import { NgIf, DecimalPipe } from '@angular/common';

import { Subscription } from 'rxjs';
import { SessionApiService } from '../services/session-api.service';

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

  @Input() symbol: string = 'BTCUSDT';

  lastPrice = 0;

  private chart: ReturnType<typeof createChart> | null = null;
  private candleSeries: ISeriesApi<'Candlestick'> | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private sessionSub?: Subscription;

  constructor(
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService
  ) {}

  ngOnInit(): void {
    this.sessionSub = this.sessionApi.session$.subscribe((session) => {
      if (session && session.symbol && session.symbol !== this.symbol) {
        this.symbol = session.symbol;
        this.lastPrice = 0;
        if (this.candleSeries) {
          this.candleSeries.setData([]);
        }
      }
    });
  }

  ngAfterViewInit(): void {
    this._initChart();
    this._subscribeToCandles();
    this._setupResize();
  }

  ngOnDestroy(): void {
    this.sessionSub?.unsubscribe();
    this.resizeObserver?.disconnect();
    if (this.chart) {
      this.chart.remove();
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
    this.ws.candle$.subscribe((candle) => {
      if (!this.candleSeries || !this.chart) return;
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
    });
  }

  private _setupResize(): void {
    if (!this.chart) return;
    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (this.chart && width > 0) {
          this.chart.applyOptions({ width, height: Math.max(height, 200) });
        }
      }
    });
    this.resizeObserver.observe(this.chartContainer.nativeElement);
  }
}