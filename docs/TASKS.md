# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato.
> I task completati sono spostati in [ARCHIVE_TASKS.md](ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](BACKLOG.md).

---

## 🚀 TASK-431 — Modalità TEST/LIVE: separazione dati, API key, toggle UI

**Status:** In Progress
**Priorità:** Alta
**Dipende da:** Nessuno

**Dettagli:**
Implementare la separazione completa tra modalità TEST e LIVE nel sistema. Include:
- Separazione API key Binance (testnet vs produzione)
- Separazione dati DB (strategie, trade, log etichettati con modalità)
- ExchangeFactory centralizzato per reconnect dinamico
- Endpoint API per leggere/cambiare modalità a runtime
- Indicatore dinamico TEST/LIVE nella topbar frontend con toggle

### Piano di Attuazione:

**1. Config (`config.py`)**
- Aggiungere `TRADING_MODE: str = 'test'`
- Aggiungere `ALLOW_LIVE_MODE: bool = False`
- Aggiungere `BINANCE_API_KEY_LIVE: str = ''` e `BINANCE_SECRET_KEY_LIVE: str = ''`
- Proprietà dinamiche: `binance_api_key`, `binance_secret_key`, `BINANCE_TESTNET` derivate da `TRADING_MODE`

**2. `.env`**
- Aggiungere `TRADING_MODE=test`, `ALLOW_LIVE_MODE=false`
- Scommentare/rinominare le OLD key come `BINANCE_API_KEY_LIVE` / `BINANCE_SECRET_KEY_LIVE`

**3. ExchangeFactory (`app/core/exchange_factory.py` — nuovo)**
- Centralizza tutte le istanze `ccxt.binance()`
- `get_exchange()` → cache singleton
- `reconnect(mode)` → ricrea connessione con key/URL corretti
- Aggiornare `market_data.py`, `binance_balance.py`, `exchange.py`, `main.py` per usare ExchangeFactory

**4. Migrazioni DB**
- Colonna `mode TEXT DEFAULT 'test'` su `strategies`, `trades`, `operation_logs`
- Popolare dati esistenti: `paper=true` → `mode='test'`

**5. ModeFilterMixin (repository layer)**
- Aggiunge `.eq("mode", current_mode)` a ogni query nei repository
- Applicato a `StrategyRepository`, `TradeRepository`

**6. API endpoint `/api/config/mode`**
- `GET` → `{mode: "test"|"live", allow_live: bool}`
- `POST` → cambia modalità, chiama `ExchangeFactory.reconnect()`
- Richiede `ALLOW_LIVE_MODE=True` per passare a LIVE

**7. Frontend — Topbar**
- Mostra "TEST" (giallo/arancione) o "LIVE" (verde) dinamicamente
- Click sul pallino → dropdown con "Switch to LIVE/TEST"
- Conferma obbligatoria per LIVE

**Test:**
- `test_get_mode_returns_test`: GET → `mode="test"`
- `test_switch_to_live_blocked`: senza ALLOW_LIVE_MODE → 403
- `test_switch_to_test`: POST → 200
- `test_exchange_factory_reconnect`: reconnect cambia URL
- `test_filter_applies_to_repositories`: mode filter aggiunto alle query
- `test_topbar_shows_mode`: mock API → TEST/LIVE visibile

---

## 📋 Riepilogo Dipendenze e Ordine di Esecuzione

```
TASK-431 (Modalità TEST/LIVE)
  └─→ (nessuna dipendenza, task autonomo)
```

---

## ✅ Regole per questo task

1. **Non rompere i test esistenti** — eseguire `pytest tests/` dopo ogni modifica sostanziale
2. **Commit selettivo** — solo file modificati direttamente
3. **Aggiornare STORY.md** dopo completamento