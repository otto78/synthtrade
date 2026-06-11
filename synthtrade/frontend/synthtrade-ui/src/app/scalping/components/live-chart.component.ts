/**
 * Live Chart Component
 * Candlestick chart 1m del simbolo corrente.
 *
 * Approccio: switchMap pulisce le richieste HTTP in-flight quando il simbolo cambia.
 * finalize() garantisce che loading torni sempre false, anche in caso di eccezione.
 */

import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ViewChild,
  ElementRef,
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
import {
  Subject,
  Subscription,
  combineLatest,
  of,
} from 'rxjs';
import {
  switchMap,
  distinctUntilChanged,
  debounceTime,
  map,
  catchError,
  finalize,
  filter,
  tap,
} from 'rxjs/operators';

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
          <span class="price-tag" *ngIf="lastPrice > 0">{{ lastPrice | number:'1.2-4' }}</span>
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
    .loading-dot { font-size: 14px; color: #F0B90B; display: inline-block; animation: spin 1s linear infinite; }
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

  /** Emette il simbolo corrente → triggera il reload delle candele */
  private symbolTrigger$ = new Subject<string>();

  private readonly API_BASE = '/api/scalping';

  constructor(
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private http: HttpClient,
  ) {}

  ngOnInit(): void {
    // ── Determina simbolo attivo: sessione running > preview ──────────────
    const activeSymbol$ = combineLatest([
      this.sessionApi.session$,
      this.sessionApi.previewSymbol$,
    ]).pipe(
      map(([session, preview]) =>
        (session?.status !== 'idle' && session?.symbol
          ? session.symbol
          : preview || 'BNBUSDC'
        ).toUpperCase()
      ),
      distinctUntilChanged(),
    );

    this.sub.add(
      activeSymbol$.subscribe((symbol) => {
        this.currentSymbol = symbol;
        this.symbolTrigger$.next(symbol);
      })
    );

    // ── switchMap: cancella HTTP in-flight se il simbolo cambia ───────────
    // finalize() è il "finally" di RxJS: gira sempre, anche se l'observable
    // termina con errore o viene annullato dal switchMap.
    this.sub.add(
      this.symbolTrigger$.pipe(
        debounceTime(100),
        switchMap((symbol) => {
          if (!this.candleSeries) {
            // chart non ancora pronto, retry quando sarà inizializzato
            return of(null);
          }
          this.loading = true;
          // Pulisci il chart immediatamente
          try { this.candleSeries.setData([]); } catch (_) {}

          return this.http
            .get<CandleResponse[]>(`${this.API_BASE}/candles/${symbol}?limit=100`)
            .pipe(
              tap((candles) => this._applyCandles(symbol, candles)),
              catchError((err) => {
                console.warn('[LiveChart] HTTP error loading candles for', symbol, err);
                return of(null);
              }),
              finalize(() => {
                // Garantito: loading = false sia in successo che in errore
                this.loading = false;
              })
            );
        })
      ).subscribe()
    );
  }

  ngAfterViewInit(): void {
    this._initChart();
    this._subscribeToWsCandles();
    this._setupResize();

    // Ora che il chart è pronto, triggera il caricamento del simbolo corrente
    this.symbolTrigger$.next(this.currentSymbol);
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
    this.symbolTrigger$.complete();
    this.resizeObserver?.disconnect();
    if (this.chart) {
      try { this.chart.remove(); } catch (_) {}
      this.chart = null;
      this.candleSeries = null;
    }
  }

  // ─── Applica dati ricevuti dal backend ────────────────────────────────────

  private _applyCandles(symbol: string, candles: CandleResponse[] | null): void {
    if (!candles || candles.length === 0 || !this.candleSeries || !this.chart) return;

    try {
      // Ordina per timestamp crescente (oldest → newest)
      const sorted = [...candles].sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );

      // Deduplica: tieni solo l'ultima candela per ogni timestamp
      // (il buffer potrebbe avere duplicati per la candela corrente)
      const seen = new Map<number, CandlestickData>();
      for (const c of sorted) {
        const ts = Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp;
        seen.set(ts, {
          time: ts,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        });
      }

      const chartData = Array.from(seen.values()).sort((a, b) =>
        (a.time as number) - (b.time as number)
      );

      if (chartData.length === 0) return;

      this.candleSeries.setData(chartData);
      this.lastPrice = chartData[chartData.length - 1].close;
      this.chart.timeScale().scrollToRealTime();
    } catch (err) {
      console.warn('[LiveChart] Error applying candle data:', err);
    }
  }

  // ─── WS real-time updates ─────────────────────────────────────────────────

  private _subscribeToWsCandles(): void {
    this.sub.add(
      this.ws.candle$
        .pipe(filter((c): c is NonNullable<typeof c> => c !== null))
        .subscribe((candle) => {
          if (!this.candleSeries || !this.chart) return;
          if (candle.symbol.toUpperCase() !== this.currentSymbol.toUpperCase()) return;

          try {
            const ts = Math.floor(
              new Date(candle.timestamp).getTime() / 1000
            ) as UTCTimestamp;
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