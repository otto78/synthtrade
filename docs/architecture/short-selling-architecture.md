# SynthTrade — Architettura Short Selling (Margin Spot)
**Versione:** 1.0 — Giugno 2026  
**Scope:** Aggiunta supporto SHORT al modulo scalping live su BNBUSDC  
**Stato:** In fase di progettazione — nessun codice implementato ancora

---

## 1. Contesto e Decisioni Prese

### 1.1 Situazione Attuale

Il modulo scalping è **già in produzione live** su Binance (BNBUSDC) con le seguenti caratteristiche:

- Exchange: **ccxt** (`ccxt.binance`)
- Mercato: **Spot** (`api.binance.com`)
- Ordini: **OCO server-side** (Stop Loss + Take Profit gestiti da Binance anche se l'app è offline)
- Direzione: solo **LONG** (BUY → attendi OCO fill → ciclo successivo)
- Safety net: gli OCO server-side proteggono la posizione anche durante disconnessioni WebSocket o crash dell'app — comportamento già verificato in sessioni live

### 1.2 Problema

Il `SignalScoreEngine` produce segnali bearish validi (score negativo, bias `bearish`, regime `trending_down`) che il sistema attualmente scarta con `BLOCKING SHORT ENTRY: side=SELL is not supported`. Nella sessione del 23/06/2026 sono stati bloccati ~15 segnali SELL validi durante un trend ribassista da 580 a 572 su BNBUSDC (~1.4% di movimento mancato).

### 1.3 Opzioni Valutate

| Opzione | Pro | Contro | Esito |
|---------|-----|--------|-------|
| **Futures perpetual** (`fapi.binance.com`) | Modo nativo per short, più pulito concettualmente | Perde OCO nativi, richiede riscrittura gestione ordini, wallet separato | ❌ Scartata |
| **Margin spot** (`api.binance.com`) | Mantiene OCO, stesso ccxt, stesso mercato | Richiede gestione borrow/repay, WalletOrchestrator | ✅ Scelta |

### 1.4 Motivazione della Scelta

Il margin spot è il percorso meno rischioso perché:
1. Gli **OCO continuano a funzionare** esattamente come ora — nessuna modifica alla gestione SL/TP
2. **ccxt supporta il margin spot** con lo stesso adapter, solo con un parametro aggiuntivo (`marginMode`)
3. Il codice del flusso long **non viene toccato** — short è un path separato
4. Il `WalletOrchestrator` già progettato copre esattamente questo scenario

---

## 2. Architettura Proposta

### 2.1 Flusso Completo Short

```
Segnale SELL approvato da SignalAggregator
    │
    ▼
WalletOrchestrator.ensure_funded(asset="USDC", required=trade_amount*2, target=MARGIN)
    ├── snapshot()   → legge balance Earn / Funding / Spot / Margin in parallelo
    ├── resolve()    → calcola trasferimenti minimi necessari (puro, testabile)
    ├── execute()    → esegue i trasferimenti (Spot→Margin, Funding→Margin, ecc.)
    └── verify()     → polling per confermare arrivo fondi nel Margin wallet
    │
    ▼
MarginBorrowManager.borrow(asset="BNB", amount=qty)
    → POST /sapi/v1/margin/loan (Binance REST via ccxt)
    │
    ▼
OrderExecutor.place_margin_sell(symbol="BNBUSDC", qty=qty)
    → Vende BNB preso in prestito al prezzo corrente
    │
    ▼
OrderExecutor.place_oco(symbol="BNBUSDC", side="BUY", qty=qty, sl=sl_price, tp=tp_price)
    → OCO server-side per chiudere lo short (BUY per ricoprire)
    │
    ▼
[Attesa fill OCO — Binance gestisce autonomamente]
    │
    ▼
MarginBorrowManager.repay(asset="BNB", amount=qty)
    → POST /sapi/v1/margin/repay
    │
    ▼
[Opzionale] WalletOrchestrator: riporta fondi da Margin a Spot
```

### 2.2 Componenti da Creare

```
app/scalping/
├── wallet_orchestrator.py       ← NUOVO — già progettato, da implementare
├── margin_borrow_manager.py     ← NUOVO — gestione borrow/repay
└── [esistenti invariati]
    ├── execution_loop.py
    ├── order_executor.py
    ├── position_manager.py
    └── signal_aggregator.py
```

### 2.3 Componenti da Modificare (minimamente)

| File | Modifica |
|------|----------|
| `execution_loop.py` | Aggiungere branch `if signal.type == SELL → short_flow()` |
| `order_executor.py` | Aggiungere `place_margin_sell()` e `place_margin_oco_buy()` |
| `position_manager.py` | Tracciare `position_side` (`LONG`/`SHORT`) e `borrow_amount` |
| `scalping_trades` (DB) | Aggiungere colonne `position_side`, `borrow_amount`, `borrow_asset`, `margin_interest` |

---

## 3. WalletOrchestrator — Dettaglio Implementativo

### 3.1 Struttura (già progettata)

```python
class WalletOrchestrator:
    async def snapshot(asset) → WalletSnapshot      # legge Earn/Funding/Spot/Margin in parallelo
    def resolve(snapshot, required, target) → list[TransferStep]  # PURO — no API calls
    async def execute(asset, steps)                  # esegue i trasferimenti
    async def verify(asset, required, target) → bool # polling conferma
    async def ensure_funded(asset, required, target) → bool  # entry point principale
```

### 3.2 Logica resolve() — Priorità Trasferimenti

```
Margin (già lì) → non serve trasferimento
Spot            → MAIN_MARGIN (trasferimento diretto)
Funding         → FUNDING_MARGIN
Earn            → redeem a Spot → poi MAIN_MARGIN (due step, con delay 2s)
```

Il metodo `resolve()` è **puro** (nessuna chiamata API) — testabile con semplici unit test senza mock complessi.

### 3.3 Endpoint Binance Utilizzati

| Operazione | Endpoint | Note |
|-----------|----------|------|
| Balance spot | `GET /api/v3/account` | Campo `balances` |
| Balance funding | `GET /sapi/v1/asset/get-funding-asset` | |
| Balance margin | `GET /sapi/v1/margin/account` | Campo `userAssets` |
| Balance earn | `GET /sapi/v1/simple-earn/flexible/position` | Escludere token `LD`-prefissati |
| Transfer universale | `POST /sapi/v1/asset/transfer` | Parametro `type`: es. `MAIN_MARGIN` |
| Redeem earn | `POST /sapi/v1/simple-earn/flexible/redeem` | Richiede `productId` |

> ⚠️ **Attenzione nota**: Binance espone i balance Flexible Earn come token `LD`-prefissati in `info.balances` (es. `LDUSDC`). Questi vanno esclusi esplicitamente dal calcolo del balance spot per evitare double-counting.

### 3.4 Gestione Errori

```python
class InsufficientFundsError(Exception): pass   # fondi totali < required
class TransferTimeoutError(Exception): pass      # verify() fallisce dopo N retry
class MarginNotEnabledError(Exception): pass     # account non abilitato al margin
```

---

## 4. MarginBorrowManager — Dettaglio Implementativo

### 4.1 Operazioni

```python
class MarginBorrowManager:
    async def borrow(asset: str, amount: float) → BorrowReceipt
    async def repay(asset: str, amount: float) → RepayReceipt
    async def get_borrow_limit(asset: str) → float      # max borrowable
    async def get_interest_rate(asset: str) → float     # tasso interesse orario
    async def get_outstanding_loans() → list[LoanRecord]
```

### 4.2 Endpoint Binance

| Operazione | Endpoint |
|-----------|----------|
| Borrow | `POST /sapi/v1/margin/loan` |
| Repay | `POST /sapi/v1/margin/repay` |
| Max borrowable | `GET /sapi/v1/margin/maxBorrowable` |
| Dettagli prestito | `GET /sapi/v1/margin/loan` |

### 4.3 Gestione Interesse

Il margin interest matura ogni ora su Binance. Per trade di scalping (durata tipica <30 minuti) l'interesse è trascurabile ma va:
- Loggato nel campo `margin_interest` di `scalping_trades`
- Sottratto dal PnL finale per calcolo corretto
- Monitorato se la sessione dura più di 1 ora con posizioni aperte

---

## 5. Schema DB — Modifiche Necessarie

### 5.1 Tabella `scalping_trades` — Nuove Colonne

```sql
ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
    position_side TEXT CHECK (position_side IN ('LONG', 'SHORT')) DEFAULT 'LONG';

ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
    borrow_amount NUMERIC(16, 8);          -- quantità asset presa in prestito

ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
    borrow_asset TEXT;                      -- es. 'BNB'

ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
    margin_interest NUMERIC(16, 8);        -- interesse maturato al momento della chiusura

ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
    repay_status TEXT CHECK (repay_status IN ('pending', 'completed', 'failed'));

ALTER TABLE scalping_trades ADD COLUMN IF NOT EXISTS
    wallet_transfer_log JSONB;             -- log dei trasferimenti WalletOrchestrator
```

### 5.2 Tabella `scalping_sessions` — Nuova Colonna

```sql
ALTER TABLE scalping_sessions ADD COLUMN IF NOT EXISTS
    allows_short BOOLEAN DEFAULT FALSE;    -- sessione abilitata allo short?
```

---

## 6. Modifiche all'Execution Loop

### 6.1 Branch Logico

```python
# execution_loop.py — pseudocodice

async def _process_candle(self, candle):
    # ... logica esistente invariata fino alla decisione di eseguire ...

    if signal.type == SignalType.BUY and not position_manager.has_open():
        # LONG — flusso esistente, invariato
        await self._open_long(signal)

    elif signal.type == SignalType.SELL and not position_manager.has_open():
        # SHORT — nuovo flusso
        if self.session_config.allows_short:
            await self._open_short(signal)
        else:
            logger.debug("SHORT signal skipped: short not enabled for this session")

    elif signal.type in (SignalType.CLOSE, SignalType.SELL):
        if position_manager.has_open():
            await self._close_position()

async def _open_short(self, signal: Signal):
    # 1. Finanzia Margin wallet
    funded = await self.wallet_orchestrator.ensure_funded(
        asset=self.quote_asset,        # es. USDC
        required=self.trade_value * 2,
        target=WalletType.MARGIN
    )
    if not funded:
        logger.error("SHORT aborted: could not fund Margin wallet")
        return

    # 2. Borrow asset base
    borrow_qty = self._calculate_short_qty(signal)
    receipt = await self.borrow_manager.borrow(
        asset=self.base_asset,         # es. BNB
        amount=borrow_qty
    )

    # 3. Sell sul margin market
    sell_order = await self.order_executor.place_margin_sell(
        symbol=self.symbol,
        qty=borrow_qty
    )

    # 4. OCO per ricoprire (BUY)
    oco = await self.order_executor.place_margin_oco_buy(
        symbol=self.symbol,
        qty=borrow_qty,
        sl_price=signal.price * (1 + self.sl_pct),   # SL più alto del prezzo corrente
        tp_price=signal.price * (1 - self.tp_pct)    # TP più basso del prezzo corrente
    )

    # 5. Salva posizione
    await self.position_manager.open_short(sell_order, oco, receipt)
    await self._save_short_to_db(sell_order, oco, receipt)
```

### 6.2 Chiusura Short (OCO Fill)

Quando l'OCO viene fillato (via UserDataStream):

```python
async def _on_oco_filled(self, event):
    position = self.position_manager.get_open()
    if position.side == 'SHORT':
        # Repay automatico
        await self.borrow_manager.repay(
            asset=position.borrow_asset,
            amount=position.borrow_amount
        )
        # Calcola interesse maturato
        interest = await self.borrow_manager.get_accrued_interest(
            asset=position.borrow_asset,
            from_time=position.entry_time
        )
        # Aggiorna DB con interesse e repay_status
        await self._update_closed_short_in_db(event, interest)
    else:
        # LONG — flusso esistente
        await self._update_closed_position_in_db(event)
```

---

## 7. Modifiche all'OrderExecutor

### 7.1 Nuovi Metodi

```python
class OrderExecutor:
    # Esistenti — invariati
    async def place_oco(self, ...): ...
    async def place_market_buy(self, ...): ...

    # NUOVI per short
    async def place_margin_sell(self, symbol: str, qty: float) -> Order:
        """Vende asset preso in prestito sul margin market"""
        return await self.exchange.create_order(
            symbol=symbol,
            type='market',
            side='sell',
            amount=qty,
            params={'marginMode': 'cross'}   # o 'isolated'
        )

    async def place_margin_oco_buy(
        self,
        symbol: str,
        qty: float,
        sl_price: float,
        tp_price: float
    ) -> OcoOrder:
        """OCO di chiusura short — BUY per ricoprire"""
        # stessa logica dell'OCO long ma side=BUY e prezzi invertiti
        # sl_price > current_price, tp_price < current_price
        ...
```

---

## 8. Configurazione Sessione

Il supporto short va abilitato esplicitamente per sessione — non automatico.

```python
# Parametro nel body di POST /scalping/session/start
{
    "symbol": "BNBUSDC",
    "mode": "live",
    "trade_value": 100,
    "allows_short": true     # ← nuovo parametro opzionale, default false
}
```

Questo permette di testare il flusso short in modo controllato senza toccare le sessioni long esistenti.

---

## 9. Prerequisiti Binance

Prima di poter usare il margin spot, l'account Binance deve avere:

1. **Margin trading abilitato** — attivazione manuale una tantum dal sito Binance
2. **Fondi nel Margin wallet** — il `WalletOrchestrator` si occupa del trasferimento
3. **Asset borrowable** — BNB deve essere disponibile nel pool di prestito Binance (quasi sempre vero per asset principali)
4. **Cross margin** (raccomandato per iniziare) vs **Isolated margin** — cross usa tutto il margin balance come collaterale, isolated isola il rischio per coppia

> Il `MarginBorrowManager.get_borrow_limit()` va chiamato prima di aprire una posizione short per verificare che il borrow sia disponibile.

---

## 10. Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Repay non eseguito dopo OCO fill | Bassa | Alto | Retry automatico + job di controllo ogni 5 min |
| Fondi insufficienti per borrow collaterale | Media | Medio | `get_borrow_limit()` prima di ogni short |
| Interesse margin accumula su posizione lunga | Bassa | Basso | Logging `margin_interest`, alert se posizione >2h |
| OCO fill ma repay fallisce → loan aperto | Bassa | Alto | `repay_status` in DB + job di recovery |
| WalletOrchestrator trasferisce troppo → spot vuoto | Media | Medio | Trasferire solo `required`, non tutto il saldo |
| Margin call durante alta volatilità | Bassa | Alto | `max_position_pct` basso (es. 10% del margin balance) |
| Binance `LD`-token conteggiati nel balance spot | Alta | Medio | Filtro esplicito su token con prefisso `LD` |

---

## 11. Fasi di Implementazione

### Fase 1 — WalletOrchestrator (prerequisito tutto il resto)
- [ ] Implementare `wallet_orchestrator.py` con i 4 metodi principali
- [ ] Unit test su `resolve()` (puro, no mock API): fondi solo in Spot, distribuiti, insufficienti
- [ ] Integration test con Binance Testnet (se disponibile su margin)
- [ ] Verificare esclusione token `LD`-prefissati dal balance spot

### Fase 2 — MarginBorrowManager
- [ ] Implementare `margin_borrow_manager.py`
- [ ] Test `borrow()` e `repay()` su Testnet
- [ ] Test `get_borrow_limit()` prima di ogni operazione

### Fase 3 — OrderExecutor — nuovi metodi margin
- [ ] Aggiungere `place_margin_sell()` e `place_margin_oco_buy()`
- [ ] Verificare che gli OCO su margin abbiano la stessa struttura di quelli spot
- [ ] Test su Testnet con quantità minime

### Fase 4 — ExecutionLoop — branch short
- [ ] Aggiungere `allows_short` alla session config
- [ ] Implementare `_open_short()` e modifica `_on_oco_filled()` per repay automatico
- [ ] Aggiungere `position_side` al `PositionManager`

### Fase 5 — DB Migration
- [ ] Migration SQL con nuove colonne `scalping_trades` e `scalping_sessions`
- [ ] Aggiornare `_save_short_to_db()` e `_update_closed_short_in_db()`

### Fase 6 — Test Live Controllato
- [ ] Prima sessione short con `trade_value` minimo (es. 10 USD)
- [ ] Monitoraggio manuale del ciclo completo: borrow → sell → OCO fill → repay
- [ ] Verifica PnL calcolato correttamente includendo interesse margin
- [ ] Almeno 1 settimana di osservazione prima di aumentare il trade_value

---

## 12. Note sul Supervisor AI

Il `SupervisorScheduler` attualmente non ha visibilità sul fatto che i segnali SHORT vengano bloccati da `BLOCKING SHORT ENTRY` — abbassa la soglia pensando che il blocco sia legato all'intelligence score, ma il vero blocco è strutturale. 

**Da aggiungere nel contesto del supervisor:**
```python
# context_builder.py
"short_enabled": self.session_config.allows_short,
"short_blocked_count": self.position_manager.short_blocked_count,
"short_blocked_reason": "margin_not_enabled" | "signal_rejected" | None
```

Questo permette al supervisor di distinguere tra "mercato neutro" e "short strutturalmente non disponibile" e di non abbassare la soglia inutilmente in sessioni long-only.

---

*Documento generato da analisi della conversazione — Giugno 2026*  
*Prossima revisione: dopo implementazione Fase 1 (WalletOrchestrator)*
