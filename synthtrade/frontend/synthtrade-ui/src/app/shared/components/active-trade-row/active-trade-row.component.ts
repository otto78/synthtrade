import { Component, Input, OnDestroy, OnInit, inject, signal, computed } from '@angular/core';
import { NgClass, DatePipe, DecimalPipe } from '@angular/common';
import { Subscription } from 'rxjs';
import { WsService } from '../../../core/services/ws.service';
import { WsMessageType, WsPricePayload } from '../../../core/models/ws-message.model';

export interface ActiveTradeRowData {
  id: string;
  strategy_id: string;
  strategy_title: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  current_price: number;
  unrealized_pnl_pct: number;
  quantity: number;
  opened_at: string;
}

@Component({
  selector: 'app-active-trade-row',
  standalone: true,
  imports: [NgClass, DatePipe, DecimalPipe],
  template: `
    <div class="ar-row">
      <span class="ar-date">{{ trade().opened_at | date:'dd/MM HH:mm' }}</span>
      <span class="ar-symbol">{{ trade().symbol }}</span>
      <span class="ar-side" [ngClass]="trade().side.toLowerCase()">{{ trade().side }}</span>
      <span class="ar-qty">{{ trade().quantity | number:'1.4-6' }}</span>
      <span class="ar-entry">{{ trade().entry_price | number:'1.2-8' }}</span>
      <span class="ar-pnl" [ngClass]="{ 
        positive: pnl() > 0, 
        negative: pnl() < 0,
        'flash-up': flashUp(),
        'flash-down': flashDown() 
      }">{{ pnl() | number:'1.2-2' }}%</span>
      <span class="ar-value">{{ positionValueEur() | number:'1.2-2' }} €</span>
    </div>
  `,
  styles: [`
    .ar-row {
      display: grid;
      grid-template-columns: 1.2fr 1fr 0.6fr 0.8fr 1fr 1fr 1fr;
      padding: 16px 12px;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      align-items: center;
      transition: background 0.2s;
      font-size: 13px;
    }
    .ar-row:hover { background: rgba(255,255,255,0.02); }
    .ar-date { color: var(--text-secondary); font-size: 13px; }
    .ar-symbol { font-weight: 600; color: var(--text-primary); }
    .ar-side { font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .ar-side.buy { color: var(--color-buy); }
    .ar-side.sell { color: var(--color-sell); }
    .ar-qty, .ar-entry, .ar-value { font-family: monospace; color: var(--text-primary); }
    .ar-pnl { font-family: monospace; font-weight: 700; transition: color 0.2s; }
    .positive { color: var(--color-buy); }
    .negative { color: var(--color-sell); }
    .flash-up {
      animation: flashUp 0.5s ease-out;
    }
    .flash-down {
      animation: flashDown 0.5s ease-out;
    }
    @keyframes flashUp {
      0% { background: rgba(0, 255, 100, 0.3); transform: scale(1.1); }
      100% { background: transparent; transform: scale(1); }
    }
    @keyframes flashDown {
      0% { background: rgba(255, 50, 50, 0.3); transform: scale(1.1); }
      100% { background: transparent; transform: scale(1); }
    }
  `]
})
export class ActiveTradeRowComponent implements OnInit, OnDestroy {
  private wsService = inject(WsService);
  protected wsSub = new Subscription();

  trade = signal<ActiveTradeRowData>({
    id: '', strategy_id: '', strategy_title: '', symbol: '',
    side: 'BUY', entry_price: 0, current_price: 0,
    unrealized_pnl_pct: 0, quantity: 0, opened_at: ''
  });

  currentPrice = signal<number>(0);
  flashUp = signal<boolean>(false);
  flashDown = signal<boolean>(false);

  pnl = computed(() => {
    const t = this.trade();
    if (t.entry_price === 0) return 0;
    return ((this.currentPrice() - t.entry_price) / t.entry_price) * 100;
  });

  positionValueEur = computed(() => {
    const t = this.trade();
    return this.currentPrice() * t.quantity;
  });

  /** Required input: ActiveTradeRowData */
  @Input({ required: true }) set tradeData(value: ActiveTradeRowData) {
    this.trade.set(value);
    this.currentPrice.set(value.current_price || value.entry_price);
  }

  ngOnInit(): void {
    this.wsSub.add(
      this.wsService.on<WsPricePayload>(WsMessageType.Price).subscribe(msg => {
        const pair = (msg as any).payload?.pair || (msg as any).pair;
        const price = (msg as any).payload?.price || (msg as any).price;
        if (!pair || !price) return;
        if (pair !== this.trade().symbol) return;

        const oldPnl = this.pnl();
        this.currentPrice.set(price);

        const newPnl = this.pnl();
        if (newPnl > oldPnl) {
          this.flashDown.set(false);
          this.flashUp.set(true);
        } else if (newPnl < oldPnl) {
          this.flashUp.set(false);
          this.flashDown.set(true);
        }

        setTimeout(() => {
          this.flashUp.set(false);
          this.flashDown.set(false);
        }, 500);
      })
    );
  }

  ngOnDestroy(): void {
    this.wsSub.unsubscribe();
  }
}