/**
 * Performance API Service
 * REST client for performance metrics
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PerformanceMetrics {
  totalPnl: number;
  totalPnlPct: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  maxDrawdown: number;
  consecutiveLosses: number;
}

@Injectable({
  providedIn: 'root',
})
export class PerformanceApiService {
  private readonly API_URL = '/api/scalping/performance';

  constructor(private http: HttpClient) {}

  /** Get performance metrics */
  getMetrics(): Observable<PerformanceMetrics> {
    return this.http.get<PerformanceMetrics>(this.API_URL);
  }
}