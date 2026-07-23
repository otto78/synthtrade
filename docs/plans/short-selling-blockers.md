# Short Selling — Problemi Rilevati e Analisi

> **Data**: 2026-07-23  
> **Stato**: Short selling BLOCCATO su OKX Spot Margin  
> **Account live**: `acctLv=1` (Spot mode), `enableSpotBorrow=True`

---

## Problema 1 (CRITICO): `tdMode=cross` non supportato

**Errore**: `54000 "Margin trading is not supported"`

**Dove succede**: `_direct_place_market_order()` in `okx_exchange.py:880`

**Accade**: Qualsiasi ordine con `tdMode=cross` o `tdMode=isolated` viene rifiutato da OKX.

**Perché**: L'account (sia demo che live) è in **Spot mode** (`acctLv=1`). In questo modalità:
- `tdMode=cross` → `54000 Margin trading is not supported`
- `tdMode=isolated` → `54000 Margin trading is not supported`
- `tdMode=cash` → ordine accettato MA non auto-borrowa (vedi Problema 2)

**Verificato con**: 
- Demo: `54000` su entrambi
- Live: `54000` su entrambi (log del 2026-07-23 12:13, session `a89de787`)

---

## Problema 2 (CRITICO): `tdMode=cash` non auto-borrowa via API

**Errore**: `51008 "Order failed. Your available balance is insufficient."`

**Dove succede**: `_direct_place_market_order()` con `tdMode=cash` per ordini SELL (short entry)

**Accade**: Un ordine SELL market con `tdMode=cash` per vendere BTC prestati NON funziona perché:
1. `tdMode=cash` per un ordine SELL controlla il saldo BTC reale (che è ~0)
2. L'auto-borrow NON è disponibile via API in Spot mode
3. `enableSpotBorrow=True` è un flag web UI, NON attiva l'auto-borrow via REST API

**OKX docs**: Per Spot mode, l'auto-borrow funziona SOLO via web interface, NON via API endpoint.

**Effetto**: Impossibile aprire uno short position in Spot mode tramite API.

---

## Problema 3 (RISOLTO): OCO bracket — `tgtCcy` non supportato su order-algo

**Errore**: `51000 "Parameter tgtCcy error"`

**Dove succede**: `_direct_place_exit_bracket()` in `okx_exchange.py`

**Causa**: OKX `/api/v5/trade/order-algo` NON supporta il parametro `tgtCcy`. Solo `/api/v5/trade/order` lo supporta.

**Fix**: Rimosso `tgtCcy: "base_ccy"` dal body OCO.

---

## Problema 4 (RISOLTO): Emergency close side inversion

**Causa**: `candle_processor.py:614` passava `side="buy"` a `ClosePositionRequest` per chiudere uno short. Ma `close_position()` in `okx_exchange.py:951` inverte: `opp_side = "sell" if request.side == "buy" else "buy"`. Risultato: piazzava un market SELL (vende altro BTC) invece di un market BUY (compra per ripagare il prestito).

**Fix**: Cambiato `side="buy"` → `side="sell"` nel `ClosePositionRequest` per short emergency close.

---

## Problema 5 (RISOLTO): Bracket qty calcolata su balance totale

**Causa**: `candle_processor.py` usava `actual_bal` (saldo totale BTC) come `bracket_qty` invece di `exec_qty` (quantità effettiva dell'ordine). Per gli short, il balance totale BTC era ~2x la qty dell'ordine.

**Fix**: `bracket_qty = exec_qty` (linea 584).

---

## Problema 6 (RISOLTO): Mode switch perdeva le sessioni

**Causa**: Quando l'utente switchava tra test/live, il backend fermava la sessione corrente e marcava quella vecchia come `stopped` nel DB. Se l'utente switchava di nuovo, la sessione era persa.

**Fix**: 
- `config_api.py`: `set_mode` ora è async, dopo il switch cerca nel DB sessioni `status=running` con il nuovo mode e le ripristina
- `main.py`: Al startup, se la sessione ha un mode diverso, non la marca come `stopped` — la lascia `running` nel DB per poterla ripristinare

---

## Problema 7 (MINOR): Long emergency close 51008_1016

**Errore**: `51008_1016 "insufficient balance, margin too low for borrowing"`

**Causa**: In demo, BTC posseduti superano il collateral limit del platform e non vengono conteggiati come margin. Anche dopo un BUY riuscito, il SELL di emergenza fallisce.

**Effetto**: Solo long trades in demo. Non blocca gli short.

---

## Riepilogo: Perché lo short non funziona

```
                    ┌─ tdMode=cross → 54000 (margin not supported in Spot mode)
SHORT SELL entry ──┤
                    └─ tdMode=cash  → 51008 (no auto-borrow via API in Spot mode)
```

**Root cause**: L'account OKX è in **Spot mode** (`acctLv=1`). Questa modalità:
- Supporta solo `tdMode=cash`
- Non supporta margin trading via API
- L'auto-borrow è disponibile SOLO via web interface

**Possibili soluzioni**:

| # | Soluzione | Pro | Contro |
|---|-----------|-----|--------|
| 1 | **Pre-borrow manuale** (`/api/v5/account/borrow`) prima del SELL | Funziona in demo e live | Richiede calcolo qty, gestione repay manuale |
| 2 | **Account Multi-currency margin** (`acctLv=2`) | Auto-brink funziona con `tdMode=cash` | Richiede upgrade account (possibile solo live, non demo) |
| 3 | **Switch account a Portfolio margin** (`acctLv=3`) | Massima flessibilità | Requisiti elevati, non disponibile per tutti |
| 4 | **Solo long trades** | Funziona亚 immediatamente | Niente short selling |
| 5 | **Testare in live** con pre-borrow | Dimostra il concept | Rischio reale |

---

## File coinvolti

| File | Modifiche |
|------|-----------|
| `config.py` | `MARGIN_MODE`, `SCALPING_SHORT_TIMESTOP_HOURS` |
| `exchange_models.py` | `ShortAvailability`, `MarginPosition`, `ClosePositionRequest.margin_mode` |
| `okx_exchange.py` | Short availability, margin methods, tgtCcy fix, bracket OCO, close_position |
| `candle_processor.py` | 3-way SELL gate, bracket qty fix, emergency close side fix |
| `trade_executor.py` | `_handle_bracket_failed`, `_close_position_and_record` |
| `market_data.py` | Short availability caching |
| `db_ops.py` | DB save/update per posizioni short |
| `config_api.py` | Mode switch session restore |
| `main.py` | Startup session restore |
| `scalping_jobs.py` | `short_timestop_job()` |
| Frontend: `position-ticker`, `trade-log`, `position.model.ts`, `scalping-ws.service.ts` | UI short support |

---

## Log di test

### Demo — `54000` con `tdMode=cross` (SHORT)
```
2026-07-23 12:09:02,865 [ERROR] Live trade failed: RuntimeError: OKX API error 1: 
  sCode='54000', sMsg='Margin trading is not supported.'
```

### Live — `54000` con `tdMode=cross` (SHORT) 
```
2026-07-23 12:13:21,345 [ERROR] Live trade failed: RuntimeError: OKX API error 1:
  sCode='54000', sMsg='Margin trading is not supported.'
```

### Demo — `51008` con `tdMode=cash` (SHORT)
```
2026-07-23 11:20:21,078 [ERROR] Live trade failed: RuntimeError: OKX API error 1:
  sCode='51008', sMsg='Order failed. Your available balance is insufficient.'
```

### Demo — `51000` OCO con `tgtCcy` (LONG)
```
2026-07-23 12:01:04,085 [ERROR] OKX order-algo POST failed [400]: 
  {"code":"51000","msg":"Parameter tgtCcy error"}
```
