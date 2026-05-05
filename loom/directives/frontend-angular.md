# Direttiva: Frontend Angular — SynthTrade

## Obiettivo
Guidare la creazione del frontend Angular 17+ di SynthTrade seguendo il design system "Dark Terminal Futurism" e le best practice del progetto.

---

## Stack Frontend

- **Framework:** Angular 17+ standalone components (NO NgModules)
- **Styling:** SCSS con design tokens in `_variables.scss`
- **Grafici:** `lightweight-charts` (TradingView) per candlestick e area chart
- **Tabelle grandi:** `@angular/cdk` Virtual Scroll (10k+ righe)
- **Test:** Jest + Angular Testing Library
- **HTTP:** `HttpClient` con `AuthInterceptor`
- **Realtime:** WebSocket custom (`WsService`) con reconnect automatico

---

## Struttura Cartelle

```
src/app/
├── core/
│   ├── services/        ← auth, api, strategy, dashboard, ws, log
│   ├── guards/          ← auth.guard.ts
│   ├── interceptors/    ← auth.interceptor.ts
│   └── models/          ← strategy.model.ts, trade.model.ts, dashboard.model.ts
├── shared/
│   ├── components/      ← stat-card, badge-status, price-ticker, confirm-modal, chart-widget
│   └── pipes/           ← currency-format.pipe.ts, time-ago.pipe.ts
├── layout/
│   ├── sidebar/
│   ├── topbar/
│   └── app-shell/
└── pages/
    ├── login/
    ├── dashboard/
    ├── strategies/
    ├── active-trade/
    └── logs/
```

---

## Regole Angular

### Componenti
- Sempre `standalone: true`
- Sempre `changeDetection: ChangeDetectionStrategy.OnPush`
- Input con `input()` signal API (Angular 17+) dove possibile
- Template semplici: logica nei servizi, non nei componenti
- Nessun `any` nel TypeScript — interfacce sempre

### Servizi
- `providedIn: 'root'` per tutti i servizi core
- HTTP calls solo nei servizi, mai nei componenti
- Usare `inject()` invece di constructor injection
- Gestire errori con `catchError` e loggare

### Routing
- Lazy loading per tutte le pagine: `loadComponent`
- `AuthGuard` su tutte le route tranne `/login`
- Redirect `/` → `/dashboard`

### Forms
- `ReactiveFormsModule` per il login
- Validazione inline, nessun alert nativo

---

## Pattern HTTP + Auth

```typescript
// auth.interceptor.ts — aggiunge Bearer token ad ogni request
intercept(req: HttpRequest<unknown>, next: HttpHandler) {
  const token = localStorage.getItem('token');
  if (token) {
    req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }
  return next.handle(req);
}
```

```typescript
// api.service.ts — base URL da environment
private base = inject(environment).apiBaseUrl;
getStrategies(status?: string) {
  const params = status ? { strategy_status: status } : {};
  return this.http.get<Strategy[]>(`${this.base}/strategies`, { params });
}
```

---

## Pattern WebSocket

```typescript
// ws.service.ts — connessione con reconnect automatico
connect(): Observable<WsMessage> {
  return new Observable(observer => {
    const connect = () => {
      const ws = new WebSocket(`${wsUrl}?token=${token}`);
      ws.onmessage = e => observer.next(JSON.parse(e.data));
      ws.onclose = () => setTimeout(connect, 3000); // reconnect dopo 3s
      ws.onerror = e => observer.error(e);
    };
    connect();
  });
}
```

---

## Pattern Grafici (lightweight-charts)

```typescript
// chart-widget.component.ts
ngAfterViewInit() {
  const chart = createChart(this.container.nativeElement, {
    layout: { background: { color: '#07090C' }, textColor: '#848E9C' },
    grid: { vertLines: { color: '#161B22' }, horzLines: { color: '#161B22' } },
  });
  const series = chart.addAreaSeries({ lineColor: '#F0B90B', topColor: 'rgba(240,185,11,0.15)' });
  series.setData(this.data);
}
```

---

## Pattern Loading Skeleton

Ogni componente che fa HTTP deve mostrare uno skeleton durante il caricamento:

```html
@if (loading()) {
  <div class="skeleton"></div>
} @else {
  <!-- contenuto reale -->
}
```

```scss
.skeleton {
  background: linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-elevated) 50%, var(--bg-surface) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}
@keyframes shimmer { 0% { background-position: 200% 0 } 100% { background-position: -200% 0 } }
```

---

## Pattern Empty State

Ogni pagina con lista deve avere un empty state:

```html
@if (items().length === 0 && !loading()) {
  <div class="empty-state">
    <span class="text-muted">Nessuna strategia disponibile</span>
  </div>
}
```

---

## Test Jest

```typescript
// Struttura base test componente
describe('StatCardComponent', () => {
  it('should render label and value', () => {
    const { getByText } = render(StatCardComponent, {
      componentInputs: { label: 'Balance', value: '€2,847' }
    });
    expect(getByText('Balance')).toBeTruthy();
    expect(getByText('€2,847')).toBeTruthy();
  });
});
```

- Mock dei servizi con `{ provide: AuthService, useValue: mockAuthService }`
- Test comportamento, non implementazione
- Nessun test su stili CSS

---

## Comandi Utili

```bash
# Genera componente standalone
ng generate component shared/components/stat-card --standalone

# Genera servizio
ng generate service core/services/auth

# Esegui test
npx jest --watch

# Build prod
ng build --configuration production
```

---

**Versione:** 1.0.0
**Ultima modifica:** 2025-01-16
