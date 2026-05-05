# Direttiva: Component Patterns — SynthTrade

## Obiettivo
Pattern e interfacce standard per i componenti shared e le pagine di SynthTrade. Seguire questi pattern garantisce coerenza visiva e comportamentale.

---

## Modelli TypeScript

```typescript
// strategy.model.ts
export interface Strategy {
  id: string;
  title: string;
  template: string;
  pair: string;
  timeframe: string;
  params: Record<string, number>;
  score: number | null;
  ai_score: number | null;
  ai_risk: 'LOW' | 'MEDIUM' | 'HIGH' | null;
  ai_note: string | null;
  ai_strengths: string[];
  ai_warnings: string[];
  status: 'PENDING' | 'APPROVED' | 'ACTIVE' | 'REJECTED' | 'EXPIRED';
  backtest: BacktestResult | null;
  equity_curve: number[];
  created_at: string;
}

export interface BacktestResult {
  pnl_pct: number;
  win_rate: number;
  sharpe: number;
  max_drawdown_pct: number;
  num_trades: number;
}

// dashboard.model.ts
export interface DashboardData {
  balance: number;
  pnl_today: number;
  active_strategy: Partial<Strategy> | null;
  engine_status: string;
}

export interface EquityPoint { ts: string; value: number; }

// trade.model.ts
export interface LogEntry {
  id: string;
  strategy_id: string | null;
  action: 'BUY' | 'SELL' | 'SKIP' | 'BLOCK' | 'ERROR';
  price: number | null;
  quantity: number | null;
  reason: string | null;
  ai_score: number | null;
  created_at: string;
}

// ws.model.ts
export type WsMessage =
  | { type: 'ping' }
  | { type: 'price'; pair: string; price: number }
  | { type: 'engine_status'; status: string }
  | { type: 'error'; code: number; detail: string };
```

---

## StatCardComponent

```typescript
@Component({
  selector: 'app-stat-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="stat-card">
      <span class="label">{{ label }}</span>
      <span class="value" [class.positive]="delta > 0" [class.negative]="delta < 0">
        {{ value }}
      </span>
      @if (delta !== null) {
        <span class="delta">{{ delta > 0 ? '+' : '' }}{{ delta | number:'1.2-2' }}%</span>
      }
    </div>
  `
})
export class StatCardComponent {
  label = input.required<string>();
  value = input.required<string>();
  delta = input<number | null>(null);
}
```

---

## BadgeStatusComponent

```typescript
@Component({
  selector: 'app-badge-status',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="badge" [ngClass]="statusClass()">{{ status() }}</span>`,
})
export class BadgeStatusComponent {
  status = input.required<string>();

  statusClass = computed(() => ({
    'badge--active':   ['ACTIVE', 'APPROVED'].includes(this.status()),
    'badge--pending':  this.status() === 'PENDING',
    'badge--rejected': ['REJECTED', 'EXPIRED'].includes(this.status()),
  }));
}
```

```scss
.badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-family: $font-mono; }
.badge--active   { color: var(--color-buy);  background: rgba(14,203,129,0.1); }
.badge--pending  { color: var(--color-warn); background: rgba(240,185,11,0.1); }
.badge--rejected { color: var(--color-sell); background: rgba(246,70,93,0.1);  }
```

---

## PriceTickerComponent

```typescript
@Component({
  selector: 'app-price-ticker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span class="price" [ngClass]="flashClass()" (animationend)="flashClass.set('')">
      {{ price() | number:'1.2-2' }}
    </span>
  `
})
export class PriceTickerComponent {
  price = input.required<number>();
  flashClass = signal('');

  constructor() {
    effect(() => {
      const p = this.price();
      // la logica di flash viene gestita dal parent che confronta old/new
    });
  }
}
```

---

## ConfirmModalComponent

```typescript
@Component({
  selector: 'app-confirm-modal',
  standalone: true,
  template: `
    @if (visible()) {
      <div class="modal-overlay" (click)="cancel.emit()">
        <div class="modal" (click)="$event.stopPropagation()">
          <p>{{ message() }}</p>
          <div class="modal-actions">
            <button class="btn-danger" (click)="confirm.emit()">Conferma</button>
            <button class="btn-ghost" (click)="cancel.emit()">Annulla</button>
          </div>
        </div>
      </div>
    }
  `
})
export class ConfirmModalComponent {
  visible = input.required<boolean>();
  message = input<string>('Sei sicuro?');
  confirm = output<void>();
  cancel = output<void>();
}
```

---

## CurrencyFormatPipe

```typescript
@Pipe({ name: 'currencyFormat', standalone: true, pure: true })
export class CurrencyFormatPipe implements PipeTransform {
  transform(value: number | null): string {
    if (value === null || value === undefined) return '—';
    return new Intl.NumberFormat('it-IT', {
      style: 'currency', currency: 'EUR', minimumFractionDigits: 2
    }).format(value);
  }
}
// Uso: {{ balance | currencyFormat }} → €2.847,32
```

---

## TimeAgoPipe

```typescript
@Pipe({ name: 'timeAgo', standalone: true, pure: false })
export class TimeAgoPipe implements PipeTransform {
  transform(value: string | null): string {
    if (!value) return '—';
    const seconds = Math.floor((Date.now() - new Date(value).getTime()) / 1000);
    if (seconds < 60)  return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  }
}
// Uso: {{ log.created_at | timeAgo }} → "2m ago"
```

---

## Layout AppShell

```
┌─────────────────────────────────────────────────────────┐
│  SidebarComponent (240px fixed, bg-surface)             │
│  + TopbarComponent (56px, live ticker via WsService)    │
│  + <router-outlet> (flex-1, bg-base)                    │
└─────────────────────────────────────────────────────────┘
```

```typescript
// app-shell.component.ts
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [SidebarComponent, TopbarComponent, RouterOutlet],
  template: `
    <div class="shell">
      <app-sidebar />
      <div class="main">
        <app-topbar />
        <main class="content"><router-outlet /></main>
      </div>
    </div>
  `
})
```

---

## Pagine — Checklist

### /login
- [ ] Fullscreen `bg-base`, logo centrato con tagline
- [ ] Input password con show/hide toggle
- [ ] Submit on Enter, disable button durante loading
- [ ] Redirect a `/dashboard` dopo login

### /dashboard
- [ ] 3 StatCard (Balance, PnL oggi, Strategia attiva)
- [ ] Area chart equity (lightweight-charts, dark theme)
- [ ] Engine status panel + ultimi 5 log
- [ ] Skeleton loading su tutti i dati

### /strategies
- [ ] Tabella con tab filter PENDING / ACTIVE / ALL
- [ ] Modal dettaglio con equity curve backtest
- [ ] Azioni inline: APPROVE (gold), REJECT (red)
- [ ] Empty state se nessuna strategia

### /active
- [ ] Candlestick chart live (pair + timeframe)
- [ ] Progress bar verso target
- [ ] KPI: ai_score, drawdown, PnL live
- [ ] Bottone STOP rosso con ConfirmModal

### /logs
- [ ] CDK Virtual Scroll (performance 10k+ righe)
- [ ] Filtri: action BUY/SELL, strategy_id
- [ ] Bottone Export CSV → chiama GET /logs/export

---

**Versione:** 1.0.0
**Ultima modifica:** 2025-01-16
