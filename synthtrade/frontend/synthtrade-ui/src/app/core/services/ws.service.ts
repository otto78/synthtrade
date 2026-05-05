import { Injectable } from '@angular/core';
import { Observable, Subject, filter } from 'rxjs';
import { TokenStorageService } from './token-storage.service';
import { WsMessage, WsMessageType } from '../models/ws-message.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class WsService {
  private ws: WebSocket | null = null;
  private subject$ = new Subject<WsMessage>();

  constructor(private tokenStorage: TokenStorageService) {}

  connect(): Observable<WsMessage> {
    const token = this.tokenStorage.getAccessToken();
    const url = `${environment.wsUrl}?token=${token}`;
    this.ws = new WebSocket(url);

    this.ws.onmessage = (e: MessageEvent) => {
      try { this.subject$.next(JSON.parse(e.data)); } catch {}
    };
    this.ws.onclose = () => this.subject$.complete();
    this.ws.onerror = (e) => this.subject$.error(e);

    return this.subject$.asObservable();
  }

  disconnect(): void {
    this.ws?.close();
    this.subject$.complete();
    this.subject$ = new Subject<WsMessage>();
  }

  on<T = unknown>(type: WsMessageType): Observable<WsMessage<T>> {
    return this.subject$.pipe(filter(m => m.type === type)) as Observable<WsMessage<T>>;
  }
}
