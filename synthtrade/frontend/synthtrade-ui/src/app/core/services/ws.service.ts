import { Injectable } from '@angular/core';
import { Observable, Subject, defer, timer } from 'rxjs';
import { retryWhen, tap, delayWhen, filter } from 'rxjs/operators';
import { TokenStorageService } from './token-storage.service';
import { WsMessage, WsMessageType } from '../models/ws-message.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class WsService {
  private ws: WebSocket | null = null;
  private _output$ = new Subject<WsMessage>();
  private connected = false;
  private _reconnectAttempt = 0;

  constructor(private tokenStorage: TokenStorageService) {}

  connect(): Observable<WsMessage> {
    if (this.connected) return this._output$.asObservable();
    this._reconnectAttempt = 0;
    this.connected = true;

    // Using defer() ensures a NEW WebSocket and Subject are created on each subscription,
    // which is necessary because WebSocket cannot be reused after disconnect.
    const wsFactory = () => {
      this._output$ = new Subject<WsMessage>();
      const token = this.tokenStorage.getAccessToken();
      const url = `${environment.wsUrl}?token=${token}`;
      this.ws = new WebSocket(url);

      this.ws.onmessage = (e: MessageEvent) => {
        try { this._output$.next(JSON.parse(e.data)); } catch {}
      };
      this.ws.onclose = () => this._output$.error(new Error('WebSocket closed'));
      this.ws.onerror = (e) => this._output$.error(e);

      return this._output$;
    };

    defer(wsFactory)
      .pipe(
        retryWhen((errors) =>
          errors.pipe(
            tap(() => {
              this._reconnectAttempt++;
              console.log(`WsService reconnecting (attempt ${this._reconnectAttempt})...`);
            }),
            delayWhen((_) => timer(this._reconnectAttempt > 5 ? 10000 : 3000))
          )
        )
      )
      .subscribe({
        error: (err) => {
          console.error('WsService error:', err);
        },
        complete: () => {
          this.connected = false;
          console.log('WsService completed');
        },
      });

    return this._output$.asObservable();
  }

  disconnect(): void {
    this.connected = false;
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this._output$.complete();
    this._output$ = new Subject<WsMessage>();
  }

  on<T = unknown>(type: WsMessageType): Observable<WsMessage<T>> {
    return this._output$.pipe(filter(m => m.type === type)) as Observable<WsMessage<T>>;
  }
}
