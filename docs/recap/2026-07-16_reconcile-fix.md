# Recap — 2026-07-16: Reconciliazione fill reali + bug critico supabase stub

## Contesto

Sessione live BTC-EUR. Trade andato in SL while BE was offline. Al restart, la reconciliazione ha usato il prezzo **ticker** come approssimazione del fill — non il prezzo reale dell'ordine su OKX.

---

## Problemi trovati e risolti

### 1. Reconciliazione usa ticker invece del fill reale (FIX in router.py)

**Problema:** `_reconcile_position_with_exchange()` usava `get_ticker_price()` come fallback quando `bracket_id` era None o non trovava match. Il prezzo ticker al momento del restart (55,952.10) era molto diverso dal fill reale (56,097.40).

**Fix:** Modificata la logica di fill recovery in `router.py:167-231`:
- **Prima:** `if bracket_id: ...` → se None, skip diretto a ticker approximation
- **Dopo:** Sempre fetch dei fill reali da OKX (`/api/v5/trade/fills`), con:
  - Priority 1a: match per `bracket_id` se disponibile
  - Priority 1b: match per `exit_side` (sell per posizione BUY)
  - Fallback: `entry_price` (solo ultima risorsa)
- Rimosso il "ticker approximation" — niente più prezzi inventati

**File:** `synthtrade/backend/app/scalping/router.py:167-231`

### 2. Bug critico: `supabase/` test stub oscurava il pacchetto reale

**Problema:** La directory `supabase/` alla root del progetto conteneva un test stub (`__init__.py` con `_DummyClient`). Poiché Python aggiunge la CWD a `sys.path`, quando l'app viene eseguita dal root directory, `from supabase import create_client` importava il dummy invece del pacchetto reale.

**Impatto:** `get_supabase()` restituiva `_DummyClient` → tutte le query al DB Supabase tornavano vuote → l'app non leggeva/scriveva mai dal DB → i trade erano solo in-memory e persi ad ogni restart.

**Fix:** Rinominata `supabase/` → `_supabase_test_stub/`. Verificato che `create_client()` ora restituisce `SyncClient` reale e che `get_supabase()` funziona correttamente.

**File:** `_supabase_test_stub/__init__.py` (rinominato da `supabase/__init__.py`)

### 3. Trade log con dati sbagliati e duplicati

**Problema:** Dopo diversi tentativi di fix con script one-shot, il trade log mostrava 4 entry duplicate con dati misti (mix di ticker approximation, fill sbagliati, fill corretti).

**Fix:** Ripulito il DB con dati reali da OKX:

| # | Entry | Exit | PnL | Source |
|---|-------|------|-----|--------|
| 1 | 56,383.10 | 56,097.40 | -0.24 | OKX fills: 4 sell @ ~56097 |
| 2 | 56,620.50 | 56,334.40 | -0.24 | OKX fills: 1 sell @ 56334.4 |
| 3 | 55,913.20 | - | - | Open (BUY attivo) |

**Total PnL: -0.48 EUR** — praticamente identico per entrambi (stesso SL% 0.504%, stesso trade_value 20 EUR)

---

## Dati OKX verificati

Fill reali dall'endpoint `/api/v5/trade/fills`:

```
BUY  @55913.2 sz=0.00035769  2026-07-16 08:09:05  (posizione aperta)
SELL @56096.1 sz=0.00009648  2026-07-16 07:36:02  ┐
SELL @56097.7 sz=0.00010725  2026-07-16 07:36:02  ├─ Trade 1 SL (4 partial fills)
SELL @56097.8 sz=0.00015065  2026-07-16 07:36:02  │
SELL @56100.0 sz=0.00000033  2026-07-16 07:36:02  ┘
BUY  @56383.1 sz=0.00035471  2026-07-16 06:40:05  (entry trade 1)
SELL @56334.4 sz=0.00035323  2026-07-16 00:25:02  (Trade 2 SL)
BUY  @56620.5 sz=0.00035322  2026-07-15 12:23:06  (entry trade 2)
```

---

## Lezioni apprese

1. **Mai usare ticker come fill price** — il prezzo corrente al momento del restart può essere molto diverso dal prezzo di esecuzione reale
2. **Il test stub `supabase/` alla root è pericoloso** — oscura il pacchetto reale se la CWD è il root del progetto
3. **L'endpoint `/api/v5/trade/fills` non restituisce `algoId`** per ordini OCO/bracket → il matching per bracket_id non funziona. Il matching per `exit_side` è l'alternativa
4. **`get_supabase()` con `lru_cache`** — se il primo call fallisce e restituisce DummyClient, il cache lo mantiene per tutta la sessione

---

## File modificati

| File | Modifica |
|------|----------|
| `synthtrade/backend/app/scalping/router.py` | Reconcile: fills reali invece di ticker |
| `_supabase_test_stub/__init__.py` | Rinominato da `supabase/__init__.py` |
| `docs/recap/2026-07-16_reconcile-fix.md` | Questo documento |
