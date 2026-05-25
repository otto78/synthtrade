/**
 * Intelligence API Service
 * REST client for market intelligence data
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { MarketIntelSnapshot } from '../models/intelligence.model';

@Injectable({
  providedIn: 'root',
})
export class IntelligenceApiService {
  private readonly API_URL = '/api/scalping/intelligence';

  constructor(private http: HttpClient) {}

  /** Get latest market intelligence snapshot */
  getLatestSnapshot(symbol: string): Observable<MarketIntelSnapshot> {
    return this.http.get<MarketIntelSnapshot>(
      `${this.API_URL}/${symbol}/snapshot`
    );
  }

  /** Get historical snapshots */
  getHistory(
    symbol: string,
    limit: number = 100
  ): Observable<MarketIntelSnapshot[]> {
    return this.http.get<MarketIntelSnapshot[]>(
      `${this.API_URL}/${symbol}/history?limit=${limit}`
    );
  }
}