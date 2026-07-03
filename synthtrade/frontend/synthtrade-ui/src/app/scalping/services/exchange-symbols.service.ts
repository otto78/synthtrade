/**
 * TASK-1109: ExchangeSymbolsService — provider-neutral symbol/instrument loader.
 *
 * Replaces BinanceSymbolsService. Fetches instruments from the backend
 * endpoint /api/scalping/exchange/instruments which returns the active exchange's
 * instruments (OKX or Binance depending on EXCHANGE_PROVIDER setting).
 *
 * Backward compatible: if the new endpoint fails, falls back to the legacy
 * Binance endpoint /api/scalping/binance/exchange-info.
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError, shareReplay, tap } from 'rxjs/operators';

/** Provider-neutral instrument model returned by /api/scalping/exchange/instruments */
export interface ExchangeInstrument {
  /** Symbol in exchange format. OKX: "BTC-EUR". Binance: "BTCUSDT" */
  symbol: string;
  /** Base asset, e.g. "BTC" */
  base: string;
  /** Quote asset, e.g. "EUR" or "USDT" */
  quote: string;
  /** Market status, e.g. "live" (OKX) or "TRADING" (Binance) */
  status: string;
  /** Provider that returned this instrument: "okx" | "binance" */
  provider: string;
}

export interface ExchangeInstrumentsResponse {
  provider: string;
  demo: boolean;
  instruments: ExchangeInstrument[];
  default_symbol: string;
}

/** Legacy Binance symbol shape (for fallback compatibility) */
interface BinanceSymbol {
  symbol: string;
  status: string;
  baseAsset: string;
  quoteAsset: string;
}

interface BinanceExchangeInfo {
  symbols: BinanceSymbol[];
}

@Injectable({
  providedIn: 'root',
})
export class ExchangeSymbolsService {
  private readonly NEW_API = '/api/scalping/exchange/instruments';
  private readonly LEGACY_API = '/api/scalping/binance/exchange-info';

  private symbols$: Observable<string[]> | null = null;
  private instruments$: Observable<ExchangeInstrument[]> | null = null;

  /** Currently active provider (populated after first fetch) */
  activeProvider: string = 'okx';
  defaultSymbol: string = 'BTC-EUR';

  constructor(private http: HttpClient) {}

  /**
   * Fetch instruments from exchange-neutral endpoint.
   * Falls back to legacy Binance endpoint if new one is unavailable.
   * Returns list of symbol strings in exchange format.
   */
  getSymbols(): Observable<string[]> {
    if (!this.symbols$) {
      this.symbols$ = this.getInstruments().pipe(
        map((instruments) => instruments.map((i) => i.symbol)),
        shareReplay(1)
      );
    }
    return this.symbols$;
  }

  /**
   * Fetch full instrument objects (with base/quote metadata).
   * Cached after first call.
   */
  getInstruments(): Observable<ExchangeInstrument[]> {
    if (!this.instruments$) {
      this.instruments$ = this.http
        .get<ExchangeInstrumentsResponse>(this.NEW_API)
        .pipe(
          tap((resp) => {
            this.activeProvider = resp.provider;
            this.defaultSymbol = resp.default_symbol || this.defaultSymbol;
            console.log(
              `[ExchangeSymbols] Loaded ${resp.instruments.length} instruments from ${resp.provider} | default=${resp.default_symbol}`
            );
          }),
          map((resp) => resp.instruments),
          catchError((err) => {
            console.warn('[ExchangeSymbols] New endpoint failed, falling back to Binance legacy:', err);
            return this._binanceFallback();
          }),
          shareReplay(1)
        );
    }
    return this.instruments$;
  }

  /**
   * Filter symbols by search query (case-insensitive)
   */
  filterSymbols(symbols: string[], query: string): string[] {
    if (!query) return symbols;
    const q = query.toLowerCase();
    return symbols.filter((s) => s.toLowerCase().includes(q));
  }

  /** Invalidate cache to force reload on next call */
  invalidateCache(): void {
    this.symbols$ = null;
    this.instruments$ = null;
  }

  // ── Private ────────────────────────────────────────────────────────────────

  private _binanceFallback(): Observable<ExchangeInstrument[]> {
    this.activeProvider = 'binance';
    return this.http.get<BinanceExchangeInfo>(this.LEGACY_API).pipe(
      map((response) => {
        const instruments: ExchangeInstrument[] = response.symbols
          .filter(
            (s) =>
              (s.quoteAsset === 'USDT' || s.quoteAsset === 'USDC') &&
              s.status === 'TRADING'
          )
          .map((s) => ({
            symbol: s.symbol,
            base: s.baseAsset,
            quote: s.quoteAsset,
            status: s.status,
            provider: 'binance',
          }))
          .sort((a, b) => a.symbol.localeCompare(b.symbol));
        console.log(`[ExchangeSymbols] Binance fallback: loaded ${instruments.length} symbols`);
        return instruments;
      }),
      catchError(() => {
        // Hard fallback: return OKX EUR instruments
        const hardFallback: ExchangeInstrument[] = [
          { symbol: 'BTC-EUR', base: 'BTC', quote: 'EUR', status: 'live', provider: 'okx' },
          { symbol: 'ETH-EUR', base: 'ETH', quote: 'EUR', status: 'live', provider: 'okx' },
          { symbol: 'SOL-EUR', base: 'SOL', quote: 'EUR', status: 'live', provider: 'okx' },
          { symbol: 'XRP-EUR', base: 'XRP', quote: 'EUR', status: 'live', provider: 'okx' },
        ];
        console.error('[ExchangeSymbols] Both endpoints failed — using hard fallback OKX EUR symbols');
        return of(hardFallback);
      })
    );
  }
}

/**
 * @deprecated Use ExchangeSymbolsService instead.
 * Kept for backward compatibility with modules that inject BinanceSymbolsService.
 */
export { ExchangeSymbolsService as BinanceSymbolsService };
