/**
 * Scalping WebSocket Service
 * Real-time connection to scalping backend
 */

import { Injectable, OnDestroy } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Subject, Observable, timer } from 'rxjs';
import { retryWhen, delayWhen, take } from 'rxjs/operators';

// Event types matching backend
export type ScalpingEventType =
  | 'candle'
  | 'signal'
  | 'order'
  | 'position'
  | 'supervisor'
  | 'risk_block';

export interface ScalpingEvent {
  type: ScalpingEventType;
  payload: any;
  timestamp: string;
}

// Specific payload types
export interface CandleEvent {
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
}

export interface SignalEvent {
  symbol: string;
  type: 'BUY' | 'SELL';
  price: number;
  confidence: number;
  reason: string;
}

export interface PositionEvent {
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_pct: number;
}

export interface SupervisorDecision {
  action: 'MODIFY_PARAMS' | 'CHANGE_STRATEGY' | 'PAUSE' | 'RESUME';
  reason: string;
  confidence: number;
  previous_params?: Record<string, any>;
  new_params?: Record<string, any>;
}

export interface RiskBlockEvent {
  symbol: string;
  blocked: boolean;
  reason: string;
}

@Injectable({
  providedIn: 'root',
})
export class ScalpingWsService implements OnDestroy {
  private ws$!: WebSocketSubject<ScalpingEvent>;
  private readonly WS_URL = 'ws://localhost:8000/ws/scalping';

  // Subjects per ogni tipo evento
  candle$ = new Subject<CandleEvent>();
  signal$ = new Subject<SignalEvent>();
  position$ = new Subject<PositionEvent>();
  supervisorDecision$ = new Subject<SupervisorDecision>();
  riskBlock$ = new Subject<RiskBlockEvent>();

  private connected = false;

  connect(): void {
    if (this.connected) return;

    this.ws$ = webSocket<ScalpingEvent>(this.WS_URL);

    this.ws$
      .pipe(
        retryWhen((errors) =>
          errors.pipe(
            delayWhen((_) => timer(3000)),
            take(5)
          )
        )
      )
      .subscribe({
        next: (event) => this._dispatch(event),
        error: (err) => console.error('Scalping WS error:', err),
      });

    this.connected = true;
  }

  disconnect(): void {
    if (this.ws$) {
      this.ws$.complete();
      this.connected = false;
    }
  }

  private _dispatch(event: ScalpingEvent): void {
    switch (event.type) {
      case 'candle':
        this.candle$.next(event.payload as CandleEvent);
        break;
      case 'signal':
        this.signal$.next(event.payload as SignalEvent);
        break;
      case 'position':
        this.position$.next(event.payload as PositionEvent);
        break;
      case 'supervisor':
        this.supervisorDecision$.next(event.payload as SupervisorDecision);
        break;
      case 'risk_block':
        this.riskBlock$.next(event.payload as RiskBlockEvent);
        break;
    }
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}