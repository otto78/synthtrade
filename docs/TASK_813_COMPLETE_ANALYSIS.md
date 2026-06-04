# TASK-813 Analysis & Action Plan

## 📊 Analisi Situazione Attuale

### ✅ Fix GIÀ COMPLETATI (da verificare)
1. **Persistence** - Backend recovery + BehaviorSubjects frontend
2. **Position WS Events** - position_update + trade_closed
3. **WS Tasks Cleanup** - asyncio.gather await
4. **Intelligence WS Stream** - _intelligence_processor() broadcast ogni 10s ✅
5. **Session Persistence DB** - scalping_sessions, scalping_trades
6. **SignalScorecard** - Connesso a intelligence$ con filter
7. **StrategyPanel** - Reattivo a supervisor decisions
8. **Risk Config API** - GET/POST /scalping/risk/config
9. **Performance Metrics** - total_pnl_pct, consecutive_losses
10. **Position Endpoint** - PnL calculation corretto

### ❌ Fix NON NECESSARI (già funzionanti)
- **Intelligence WS**: Già implementato in `_intelligence_processor()` (broadcast ogni 10s)
- Nessun polling REST nel MarketIntelPanel - usa solo WS

---

## 🔍 NUOVE PROBLEMATICHE IDENTIFICATE

### 1. 🔴 CRITICO: Strategia "momentum_base" Mancante nel Frontend

**Problema**: 
- Backend registry ha 4 strategie: `ema_cross`, `rsi_bollinger`, `vwap_reversion`, `momentum_base`
- Frontend STRATEGY_DEFAULTS ha solo 3 + `scalping_v2` (che non è nel backend)
- **momentum_base NON è presente nel frontend** → UI non può visualizzarla

**Impact**: Se AI Supervisor seleziona `momentum_base`, frontend non la mostra

**Soluzione**: Aggiungere momentum_base al frontend STRATEGY_DEFAULTS

---

### 2. 🟡 IMPORTANTE: Symbol Selector - Lista Limitata vs Opportunities

**Problema Attuale**:
- User può scegliere solo BTCUSDT (hardcoded)
- Opportunity può consigliare trading su simboli non disponibili nella lista
- Conflitto: come tradare un opportunity su SOLUSDT se non è nella lista?

**Soluzioni Proposte**:

#### Opzione A: Lista Completa Binance (CONSIGLIATA)
- Fetch da API Binance: `GET /api/v3/exchangeInfo` → tutti i simboli USDT perpetual
- Dropdown con search/autocomplete (troppi per mostrare tutti)
- Sincronizzato con opportunities: simbolo opportunity automaticamente disponibile

**Vantaggi**: 
- Nessun limite
- Opportunities sempre utilizzabili
- Aggiornato automaticamente con nuove listing

**Implementazione**: 15-20 min

#### Opzione B: Watchlist Dinamica
- Lista base (10 simboli top: BTC, ETH, SOL, BNB, etc.)
- + simboli da opportunities aggiunti automaticamente
- User può aggiungere custom

**Vantaggi**:
- UI più pulita
- Focus su simboli rilevanti

**Implementazione**: 10-15 min

#### ✅ DECISIONE: Opzione A (fetch tutti i simboli Binance)

---

### 3. 🟡 IMPORTANTE: Trade Exit Visualization - Missing Info

**Problema**: 
User ha trade aperto con PnL +9%, NON sa quando uscirà automaticamente

**Dati Mancanti nella UI**:
- **Stop Loss Target**: Entry × 0.997 (-0.3%)
- **Take Profit Target**: Entry × 1.005 (+0.5%)
- **Visual Progress Bar**: Mostrare visivamente quanto manca al TP

**Soluzione**: Arricchire PositionTickerComponent con:
```typescript
interface PositionDisplay {
  // Existing
  entry_price: number;
  current_price: number;
  pnl_pct: number;  // Es: 9.0%
  
  // NEW
  stop_loss_price: number;      // Entry × 0.997
  take_profit_price: number;    // Entry × 1.005
  stop_loss_pct: -0.3;          // -0.3%
  take_profit_pct: 0.5;         // +0.5%
  
  // COMPUTED
  distance_to_tp: number;       // % remaining to TP (es: 0.5 - 0.09 = 0.41%)
  distance_to_sl: number;       // % buffer before SL
  progress_pct: number;         // 0-100% progress bar (SL=0%, TP=100%)
}
```

**Backend già invia questi dati!**
- `position_update` event già contiene `stop_loss_price`, `take_profit_price`, `stop_loss_pct`, `take_profit_pct`
- Frontend deve solo mostrarli

**Implementazione**: 10 min

---

### 4. ⚪ VERIFICHE: Trade Closure Logic

**Da Verificare**:
1. ✅ SL/TP monitoring attivo? → SÌ: `_position_monitor()` ogni 2s
2. ✅ Logica chiusura corretta? → SÌ: BUY (current <= SL | current >= TP), SELL (current >= SL | current <= TP)
3. ✅ Trade_closed event broadcast? → SÌ: `broadcast_scalping_event("trade_closed", trade_record)`
4. ✅ Frontend position reset? → SÌ: PositionTickerComponent sottoscrive trade_closed e resetta a null
5. ⚠️ Trade history persistenza? → PARZIALE: salvato in-memory, non recuperato da DB on restart

**Problema Minore**: Trade history in-memory si perde su backend restart
- Soluzione: Query `scalping_trades` table on session recovery (5 min fix)

---

## 📋 ACTION PLAN COMPLETO

### PRIORITÀ 1 - Critici (Bloccanti)
**Nessuno** - Tutti i critici già risolti ✅

### PRIORITÀ 2 - Importanti (High Impact UX)

#### ACTION 1: Symbol Selector con Fetch Binance
**File**: `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts`
**Tempo**: 15-20 min

**Task**:
1. Creare service `binance-symbols.service.ts`:
   ```typescript
   async fetchSymbols(): Promise<string[]> {
     // GET https://api.binance.com/api/v3/exchangeInfo
     // Filter: quoteAsset === 'USDT' && status === 'TRADING'
     // Return: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', ...]
   }
   ```

2. Aggiungere dropdown in SessionControls:
   ```html
   <select [(ngModel)]="selectedSymbol">
     <option *ngFor="let sym of symbols" [value]="sym">{{ sym }}</option>
   </select>
   <input type="text" [(ngModel)]="symbolFilter" placeholder="Search..." />
   ```

3. Passare symbol a POST /session:
   ```typescript
   startSession() {
     this.sessionApi.controlSession({
       action: 'start',
       symbol: this.selectedSymbol  // NEW
     });
   }
   ```

**Test**: Start session con ETHUSDT, verificare chart + intelligence caricano corretto simbolo

---

#### ACTION 2: Trade Exit Info - Enhanced Position Display
**File**: `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/position-ticker.component.ts`
**Tempo**: 10 min

**Task**:
1. Template già riceve `stop_loss_price`, `take_profit_price` da backend
2. Aggiungere al template:
   ```html
   <div class="exit-targets">
     <div class="target sl">
       <span class="label">Stop Loss</span>
       <span class="value">{{ position.stop_loss_price | number:'1.2-2' }}</span>
       <span class="pct">({{ position.stop_loss_pct }}%)</span>
     </div>
     <div class="target tp">
       <span class="label">Take Profit</span>
       <span class="value">{{ position.take_profit_price | number:'1.2-2' }}</span>
       <span class="pct">({{ position.take_profit_pct }}%)</span>
     </div>
   </div>
   
   <div class="progress-bar">
     <div class="fill" [style.width.%]="getProgressPct()"></div>
     <span class="label">{{ position.pnl_pct | number:'1.2-2' }}% / {{ position.take_profit_pct }}%</span>
   </div>
   ```

3. Compute progress:
   ```typescript
   getProgressPct(): number {
     if (!this.position) return 0;
     const range = this.position.take_profit_pct - this.position.stop_loss_pct;
     const current = this.position.pnl_pct - this.position.stop_loss_pct;
     return Math.max(0, Math.min(100, (current / range) * 100));
   }
   ```

**Test**: Open trade → verificare SL/TP prices + progress bar

---

#### ACTION 3: Momentum Base Strategy - Frontend Sync
**File**: `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/strategy-panel.component.ts`
**Tempo**: 5 min

**Task**:
Aggiungere `momentum_base` a STRATEGY_DEFAULTS:
```typescript
const STRATEGY_DEFAULTS: Record<string, { label: string; desc: string; params: StrategyParams }> = {
  ema_cross: { ... },
  rsi_bollinger: { ... },
  vwap_reversion: { ... },
  momentum_base: {
    label: 'Momentum Base',
    desc: 'Trend following con momentum indicators',
    params: { ema_fast: 12, ema_slow: 26, take_profit_pct: 0.6, stop_loss_pct: 0.35 },
  },
  scalping_v2: { ... },
};
```

**Test**: Start session con strategy="momentum_base" → verificare UI mostra strategia

---

### PRIORITÀ 3 - Minori (Nice to Have)

#### ACTION 4: Trade History Persistence Recovery
**File**: `synthtrade/backend/app/scalping/router.py` (GET /session)
**Tempo**: 5 min

**Task**:
In `get_session()` dopo session recovery, query trade history:
```python
if resp.data:
    db_sess = resp.data[0]
    session["db_session_id"] = db_sess["id"]
    # ... restore metadata ...
    
    # NEW: Restore trade history
    trades_resp = supabase.table("scalping_trades") \
        .select("*") \
        .eq("session_id", db_sess["id"]) \
        .order("entry_time", desc=False) \
        .execute()
    
    if trades_resp.data:
        _execution_state["trade_history"] = [
            {
                "symbol": t["symbol"],
                "side": t["side"],
                "entry_price": t["entry_price"],
                "exit_price": t["exit_price"],
                "pnl": t["pnl"],
                "pnl_pct": t["pnl_pct"],
                "timestamp": t["exit_time"],
            }
            for t in trades_resp.data if t["status"] == "closed"
        ]
```

**Test**: Backend restart → verificare performance metrics accurate

---

#### ACTION 5: WS Connection Management - User Feedback
**File**: `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/scalping-ws.service.ts`
**Tempo**: 10 min

**Task**:
1. Aumentare retry count:
   ```typescript
   retryWhen((errors) =>
     errors.pipe(
       delayWhen((_, i) => {
         if (i > 10) {  // After 10 retries (~30s), notify user
           this.connectionError$.next('WebSocket disconnesso. Verifica connessione.');
         }
         return timer(3000);
       })
     )
   )
   ```

2. Aggiungere connection status Subject:
   ```typescript
   connectionStatus$ = new BehaviorSubject<'connected' | 'disconnected' | 'reconnecting'>('disconnected');
   ```

3. Toast notification in dashboard on permanent disconnect

**Test**: Disconnect network → verificare toast dopo 30s

---

#### ACTION 6: Opportunity Feed - Watch/Ignore Buttons
**File**: `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/opportunity-feed.component.ts`
**Tempo**: 10 min

**Task**:
Template già ha pulsanti, collegare a API:
```typescript
watchOpportunity(oppId: string) {
  this.opportunityApi.addToWatchlist(oppId).subscribe(() => {
    // Update UI - mark as watched
  });
}

ignoreOpportunity(oppId: string) {
  this.opportunityApi.ignoreOpportunity(oppId).subscribe(() => {
    // Remove from list
  });
}
```

**Test**: Click Watch → simbolo aggiunto a watchlist, Click Ignore → opportunity sparisce

---

## 🧪 TEST PLAN

### Test 1: Symbol Selection
```bash
1. Frontend: Open SessionControls
2. Dropdown deve mostrare 200+ simboli
3. Type "SOL" in search → filtra solo SOL* symbols
4. Select SOLUSDT → Start session
5. Verify: Chart loads SOLUSDT candles
6. Verify: Intelligence panel shows SOLUSDT metrics
```

### Test 2: Trade Exit Visibility
```bash
1. Start session → wait for trade open
2. Position ticker deve mostrare:
   - Entry price: 95000.00
   - Current price: 95855.00 (esempio)
   - PnL: +0.09 (+9.0%)
   - Stop Loss: 94715.00 (-0.3%)
   - Take Profit: 95475.00 (+0.5%)
   - Progress bar: 90% filled (vicino a TP)
3. Verify: Se current >= TP → trade chiude automaticamente
4. Verify: Position ticker resetta a "No open position"
```

### Test 3: Momentum Base Strategy
```bash
1. Backend: POST /session con strategy="momentum_base"
2. Frontend: StrategyPanel deve mostrare "Momentum Base"
3. Verify: Parametri corretti (ema_fast=12, ema_slow=26, tp=0.6%, sl=0.35%)
```

### Test 4: Trade History Persistence
```bash
1. Start session → esegui 3 trade (chiusi)
2. Performance panel mostra: total_trades=3, win_rate=XX%
3. Backend restart (Ctrl+C + restart)
4. Frontend reload (F5)
5. Verify: Performance panel ancora mostra total_trades=3
6. Verify: Trade Log mostra gli stessi 3 trade
```

---

## 📊 SUMMARY

### Fixes da Rimuovere (già funzionanti)
- ❌ Intelligence WS Stream (già implementato)
- ❌ MarketIntelPanel polling removal (non esiste polling)

### Fixes da Aggiungere
1. ✅ **Symbol Selector** - fetch tutti i simboli Binance (15 min)
2. ✅ **Trade Exit Info** - SL/TP prices + progress bar (10 min)
3. ✅ **Momentum Base Sync** - aggiungere strategia a frontend (5 min)
4. ⚪ **Trade History Recovery** - query DB on restart (5 min) [NICE TO HAVE]
5. ⚪ **WS Connection Feedback** - toast su disconnect permanente (10 min) [NICE TO HAVE]
6. ⚪ **Opportunity Actions** - collegare Watch/Ignore buttons (10 min) [NICE TO HAVE]

### Total Effort
- **Priorità Alta**: 30 min (Actions 1-3)
- **Priorità Media**: 25 min (Actions 4-6)
- **Total**: 55 min

### Files da Modificare
**Frontend (4 files)**:
- `session-controls.component.ts` + nuovo `binance-symbols.service.ts`
- `position-ticker.component.ts`
- `strategy-panel.component.ts`
- `scalping-ws.service.ts` [optional]

**Backend (1 file)**:
- `router.py` (GET /session) [optional]

---

## ✅ CONGRATS: Trade Aperto!

Il fatto che un trade sia partito significa:
1. ✅ Signal generation funziona
2. ✅ Intelligence score OK (o paper_mode fallback attivo)
3. ✅ Position manager apre correttamente
4. ✅ WS broadcast posizione a frontend

**Prossimi passi**: Implementare Actions 1-3 per migliorare UX durante il trade.
