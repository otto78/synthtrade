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
import { createChart, ColorType, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import { ScalpingWsService, CandleEvent } from '../services/scalping-ws.service';

@Component({
  selector: 'app-live-chart',
  standalone: true,
  template: `
    <div class="live-chart">
      <div class="chart-header">
        <h3>Live Chart</h3>
        <span class="symbol">{{ symbol }}</span>
      </div>
      <div #chartContainer class="chart-container"></div>
    </div>
  `,
  styles: [`
    .live-chart { padding: 12px; }
    .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    h3 { margin: 0; font-size: 14px; color: var(--text-secondary); }
    .symbol { font-size: 12px; color: var(--accent-primary, #F0B90B); font-weight: 600; }
    .chart-container { height: 300px; width: 100%; }
  `],
})
export class LiveChartComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('chartContainer', { static: true })
  chartContainer!: ElementRef<HTMLDivElement>;

  @Input() symbol: string = 'BTCUSDT';

  private chart: ReturnType<typeof createChart> | null = null;
  private candleSeries: ISeriesApi<'Candlestick'> | null = null;

  constructor(private ws: ScalpingWsService) {}

  ngOnInit(): void {
    this.ws.connect();
  }

  ngAfterViewInit(): void {
    this._initChart();
    this._subscribeToCandles();
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.remove();
    }
  }

  private _initChart(): void {
    this.chart = createChart(this.chartContainer.nativeElement, {
      width: this.chartContainer.nativeElement.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: '#161B22' },
        textColor: '#EAECEF',
      },
      grid: {
        vertLines: { color: 'rgba(234,236,239,0.05)' },
        horzLines: { color: 'rgba(234,236,239,0.05)' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: 'rgba(234,236,239,0.1)',
      },
      timeScale: {
        borderColor: 'rgba(234,236,239,0.1)',
      },
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
      if (this.candleSeries) {
        this.candleSeries.update({
          time: (new Date(candle.timestamp).getTime() / 1000) as UTCTimestamp,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        });
      }
    });
  }
}