/**
 * Live Chart Component
 * Mostra le ultime 100 candele 1m del simbolo corrente.
 * 
 * Strategia semplice e robusta:
 *  1. Al mount, carica 100 candele via REST (sempre, anche prima della sessione)
 *  2. Ascolta i candle WS e aggiorna in real-time con series.update()
 *  3. Se il simbolo cambia (sessione avviata o utente ne sceglie uno nuovo), ricarica le 100 candele
 *  4. Se la sessione viene ripristinata (restore), usa il simbolo della sessione
 */

import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ViewChild,
  ElementRef,
  ChangeDetectorRef,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {
  createChart,
  ColorType,
  ISeriesApi,
  UTCTimestamp,
  CrosshairMode,
  CandlestickData,
  IChartApi,
} from 'lightweight-charts';
import { ScalpingWsService } from '../services/scalping-ws.service';
import { SessionApiService } from '../services/session-api.service';
import { NgIf, DecimalPipe } from '@angular/common';
import { Subscription, combineLatest } from 'rxjs';
import { filter, distinctUntilKeyChanged, distinctUntilChanged, map, debounceTime } from 'rxjs/operators';

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
        <span class="panel-title">Live Chart</span>
        <div class="chart-meta">
          <span class="symbol">{{ currentSymbol }}</span>
          <span class="timeframe">1m</span>
          <span class="price-tag" *ngIf="lastPrice > 0">{{ lastPrice | number:'1.2-2' }}</span>
          <span class="loading-dot" *ngIf="loading" title="Caricamento candele...">⟳</span>
        </div>
      </div>
      <div class="title-hr"></div>
      <div #chartContainer class="chart-container"></div>
    </div>
  `,
  imports: [NgIf, DecimalPipe],
  styles: [`
    .live-chart { padding: 12px; display: flex; flex-direction: column; height: 100%; }
    .chart-header { display: flex; justify-content: space-between; align-items: center; }
    .title-hr { height: 1px; background: rgba(234,236,239,0.08); margin: 8px 0 12px 0; }
    .chart-meta { display: flex; align-items: center; gap: 8px; }
    .symbol { font-size: 13px; color: var(--accent-primary, #F0B90B); font-weight: 700; }
    .timeframe { font-size: 10px; color: var(--text-secondary); background: rgba(240,185,11,0.1); padding: 2px 6px; border-radius: 3px; }
    .price-tag { font-size: 13px; color: #26a69a; font-weight: 600; font-variant-numeric: tabular-nums; }
    .loading-dot { font-size: 14px; color: #F0B90B; animation: spin 1s linear infinite; }
    .chart-container { flex: 1; min-height: 280px; width: 100%; }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
})
export class LiveChartComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('chartContainer', { static: true })
  chartContainer!: ElementRef<HTMLDivElement>;

  currentSymbol = 'BNBUSDC';
  lastPrice = 0;
  loading = false;

  private chart: IChartApi | null = null;
  private candleSeries: ISeriesApi<'Candlestick'> | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private sub = new Subscription();
  private _chartReady = false;

  private readonly API_BASE = '/api/scalping';

  constructor(
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    // Determina il simbolo attivo: sessione running ha priorità, altrimenti preview
    // Usiamo distinctUntilChanged per evitare reload multipli per lo stesso simbolo
    const activeSymbol$ = combineLatest([
      this.sessionApi.session$,
      this.sessionApi.previewSymbol$,
    ]).pipe(
      map(([session, preview]) => {
        if (session && session.status !== 'idle' && session.symbol) {
          return session.symbol.toUpperCase();
        }
        return (preview || 'BNBUSDC').toUpperCase();
      }),
      distinctUntilChanged(),
      // Piccolo debounce per evitare doppio-caricamento all'avvio
      debounceTime(150),
    );

    this.sub.add(
      activeSymbol$.subscribe((symbol) => {
        if (symbol !== this.currentSymbol) {
          this.currentSymbol = symbol;
          this.cdr.markForCheck();
        }
        // Ricarica storico se il chart è già pronto, altrimenti ngAfterViewInit lo farà
        if (this._chartReady) {
          this._reloadCandles(symbol);
        }
      })
    );
  }

  ngAfterViewInit(): void {
    this._initChart();
    this._subscribeToCandles();
    this._setupResize();
    this._chartReady = true;

    // Prima inizializzazione: carica le candele del simbolo corrente
    this._reloadCandles(this.currentSymbol);
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
    this.resizeObserver?.disconnect();
    if (this.chart) {
      try { this.chart.remove(); } catch (_) {}
      this.chart = null;
      this.candleSeries = null;
    }
  }

  // ─── Caricamento storico ───────────────────────────────────────────────────

  private _reloadCandles(symbol: string): void {
    if (!this.candleSeries || !this.chart) return;
    if (this.loading) return;

    this.loading = true;
    this.cdr.markForCheck();

    // Svuota il chart prima di caricare i nuovi dati
    this.candleSeries.setData([]);

    this.http
      .get<CandleResponse[]>(`${this.API_BASE}/candles/${symbol}?limit=100`)
      .subscribe({
        next: (candles) => {
          if (!candles || candles.length === 0) {
            this.loading = false;
            this.cdr.markForCheck();
            return;
          }

          // Ordina per timestamp crescente (più vecchio → più recente)
          // Il backend dovrebbe già mandarle in ordine, ma per sicurezza
          const sorted = [...candles].sort(
            (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          );

          const chartData: CandlestickData[] = sorted.map((c) => ({
            time: (new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
          }));

          if (this.candleSeries) {
            this.candleSeries.setData(chartData);
            this.lastPrice = chartData[chartData.length - 1].close;
          }
          if (this.chart) {
            this.chart.timeScale().scrollToRealTime();
          }
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (e) => {
          console.warn('[LiveChart] Failed to load candles for', symbol, e);
          this.loading = false;
          this.cdr.markForCheck();
        },
      });
  }

  // ─── WS real-time updates ─────────────────────────────────────────────────

  private _subscribeToCandles(): void {
    this.sub.add(
      this.ws.candle$
        .pipe(filter((c): c is NonNullable<typeof c> => c !== null))
        .subscribe((candle) => {
          if (!this.candleSeries || !this.chart) return;
          if (candle.symbol.toUpperCase() !== this.currentSymbol.toUpperCase()) return;

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
            this.chart.timeScale().scrollToRealTime();
          } catch (_) {
            // chart rimosso/distrutto, ignora
          }
        })
    );
  }

  // ─── Chart init & resize ──────────────────────────────────────────────────

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
      crosshair: { mode: CrosshairMode.Normal },
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
          return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
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

  private _setupResize(): void {
    if (!this.chart) return;
    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (this.chart && width > 0) {
          try {
            this.chart.applyOptions({ width, height: Math.max(height, 200) });
          } catch (_) {}
        }
      }
    });
    this.resizeObserver.observe(this.chartContainer.nativeElement);
  }
}