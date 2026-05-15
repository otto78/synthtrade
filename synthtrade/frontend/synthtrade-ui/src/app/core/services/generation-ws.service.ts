import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { WsService } from './ws.service';
import { WsMessage, WsMessageType } from '../models/ws-message.model';

export interface GenerationCompletePayload {
  generation_id: string;
  count: number;
}

@Injectable({ providedIn: 'root' })
export class GenerationWsService {
  private ws = inject(WsService);

  /**
   * Observable that emits when the backend broadcasts a `generation_complete` message.
   * The payload contains the `generation_id` and the number of generated strategies.
   */
  onGenerationComplete(): Observable<WsMessage<GenerationCompletePayload>> {
    return this.ws.on<GenerationCompletePayload>(WsMessageType.GenerationComplete);
  }
}
