# TASK-809 — Frontend Dashboard Scalping Implementation Plan

## Overview
Angular frontend per il modulo Scalping v2.0 con WebSocket real-time e pannelli intelligence.

## Files to Create

### 1. Struttura Modulo Angular
```
src/app/scalping/
├── scalping.module.ts
├── scalping-routing.module.ts
├── models/
│   ├── intelligence.model.ts
│   ├── opportunity.model.ts
│   └── session.model.ts
├── services/
│   ├── scalping-ws.service.ts    # WebSocket client
│   ├── intelligence-api.service.ts
│   └── opportunity-api.service.ts
├── components/
│   ├── scalping-dashboard/
│   ├── market-intel-panel/
│   ├── signal-scorecard/
│   └── opportunity-feed/
```

### 2. WebSocket Service — `scalping-ws.service.ts`
```typescript
// Basato sul piano in TASKS.md
export interface ScalpingEvent {
  type: 'candle' | 'signal' | 'order' | 'position' | 'supervisor' | 'risk_block';
  payload: any;
  timestamp: string;
}

// Subjects per ogni tipo evento
candle$ = new Subject<CandleEvent>();
signal$ = new Subject<SignalEvent>();
position$ = new Subject<PositionEvent>();
supervisorDecision$ = new Subject<SupervisorDecision>();
riskBlock$ = new Subject<RiskBlockEvent>();

connect(): void {
  this.ws$ = webSocket<ScalpingEvent>('ws://localhost:8000/ws/scalping');
  this.ws$.pipe(retryWhen(errors => errors.pipe(delay(3000))))
    .subscribe(event => this._dispatch(event));
}
```

### 3. PerformanceMetrics Interface
```typescript
interface PerformanceMetrics {
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
```

## Architettura Componenti

| Componente | Descrizione |
|-----------|-------------|
| ScalpingDashboard | Layout principale con griglia componenti |
| MarketIntelPanel | Funding rate, OI, CVD, Fear&Greed real-time |
| SignalScorecard | Score aggregato 0-100 con breakdown |
| OpportunityFeed | Feed real-time opportunità AI classificate |
| SessionControls | Start/Stop/Pausa sessione scalping |

## Verifica
```bash
cd frontend && npm test -- --runInBand src/app/scalping/
npm run e2e -- scalping-session.spec.ts
```

## TDD Workflow
- Test unit stato subjects WebSocket
- Test dispatch evento per tipo
- Test reconnection logic
- Integration test con mock WebSocket