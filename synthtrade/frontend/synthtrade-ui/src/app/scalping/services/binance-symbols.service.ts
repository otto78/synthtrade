/**
 * Binance Symbols Service
 * Fetches all available USDT trading pairs via backend proxy to avoid CORS.
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError, shareReplay } from 'rxjs/operators';

interface BinanceSymbol {
  symbol: string;
  status: string;
  baseAsset: string;
  quoteAsset: string;
}

interface BinanceExchangeInfo {
  symbols: BinanceSymbol[];
}

import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class BinanceSymbolsService {
  private readonly PROXY_API = `${environment.apiUrl}/scalping/binance/exchange-info`;
  private symbols$: Observable<string[]> | null = null;

  constructor(private http: HttpClient) {}

  /**
   * Fetch all USDT trading pairs via backend proxy
   * Cached after first call
   */
  getSymbols(): Observable<string[]> {
    if (!this.symbols$) {
      this.symbols$ = this.http.get<BinanceExchangeInfo>(this.PROXY_API).pipe(
        map((response) => {
          // Filter: USDT and USDC pairs + TRADING status only
          const usdtSymbols = response.symbols
            .filter((s) => (s.quoteAsset === 'USDT' || s.quoteAsset === 'USDC') && s.status === 'TRADING')
            .map((s) => s.symbol)
            .sort();
          
          console.log(`Loaded ${usdtSymbols.length} USDT symbols via proxy`);
          return usdtSymbols;
        }),
        catchError((error) => {
          console.error('Failed to fetch Binance symbols:', error);
          // Fallback to common symbols if API fails
          return of([
            'BNBUSDC', 'BTCUSDC', 'ETHUSDC', 'SOLUSDC',
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
            'XRPUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT'
          ]);
        }),
        shareReplay(1) // Cache result
      );
    }
    return this.symbols$;
  }

  /**
   * Filter symbols by search query
   */
  filterSymbols(symbols: string[], query: string): string[] {
    if (!query) return symbols;
    const q = query.toLowerCase();
    return symbols.filter((s) => s.toLowerCase().includes(q));
  }
}
