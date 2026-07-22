# SynthTrade — Architettura Short Selling (OKX Spot Margin)

**Versione:** 1.0 — 21 luglio 2026
**Stato:** Pianificazione — zero implementazione, prerequisiti da validare con spike read-only
**Supersede:** `docs/architecture/short-selling-architecture.md` (Binance), `docs/analysis/short-selling-analysis.md` (Binance)

---

## 1. Contesto

Il modulo scalping opera live su OKX (dopo cutover da Binance). Lo short selling non e' implementato: tutti i segnali SELL vengono scartati. Questo documento definisce l'architettura OKX-specifica per abilitare lo short.

Differenza fondamentale vs Binance: **conto unificato**, nessun wallet separato, nessun trasferimento Spot→Margin. Il borrow avviene a livello di ordine se l'account ha `enableSpotBorrow=true`.

---

## 2. Meccanica API Reale

### 2.1 Apertura Short — stessa identica API del long

```
POST /api/v5/trade/order
{
  "instId": "BTC-EUR",
  "tdMode": "cross",     // oggi "cash" (spot puro, niente borrow)
  "side": "sell",
  "ordType": "market",
  "sz": "..."
}
```

Cambia solo `tdMode` (da `cash` a `cross`/`isolated`) e `side`. **Non esiste un parametro "auto-borrow" nell'ordine** — il borrow scatta automaticamente al fill se l'account ha `enableSpotBorrow=true` e c'e' collaterale/limite sufficiente.

### 2.2 Riconoscimento Short a Posteriori

`GET /api/v5/account/positions` (`instType=MARGIN`):
- `posCcy` = quote currency (EUR) → **short**
- `posCcy` = base currency (BTC) → **long**

Nessun flag booleano dedicato.

### 2.3 Bracket TP/SL

Stesso endpoint `order-algo` gia' in uso per il long, solo con direzione invertita:
- TP: sotto l'entry price
- SL: sopra l'entry price

### 2.4 Chiudi Short (Buy-back + Repay)

L'OCO/bracket di chiusura e' un ordine BUY (ricopre la posizione). Il repay e' automatico se l'account ha modalita' auto-repay; altrimenti esplicito.

---

## 3. Modello Costo (Fee + Interesse)

| Voce | Valore | Note |
|------|--------|------|
| Fee round-trip | ~0.70% | Maker/Taker, gi a noto |
| Interesse borrow | `Liability x (APR / 365 / 24)` | Accrual orario |
| Interesse trascurabile? | Si per scalping <2h | No per posizioni >2h |

**Formula interesse:**
```
Interesse = Quantita_borrowata x Prezzo_entry x (APR / 365 / 24) x Ore_aperte
```

**Tasso reale:** verificabile con `GET /api/v5/public/interest-rate-loan-quota?ccy=<asset>` (pubblico, nessuna auth).

**Implicazione per micro-swing:** con SL/TP allargati (pivot micro-swing), la permanenza in posizione aumenta → l'interesse diventa piu' rilevante rispetto a scalping stretto.

---

## 4. Lista Completa API OKX Coinvolte

| # | Endpoint | Metodo | Uso | Note |
|---|----------|--------|-----|------|
| 1 | `/api/v5/account/config` | GET | Verifica `enableSpotBorrow` e account mode | Una volta all'avvio, non per-trade |
| 2 | `/api/v5/trade/order` | POST | Stesso endpoint long — cambia solo `tdMode` e `side` | Nessun nuovo metodo adapter |
| 3 | `/api/v5/account/max-loan` | GET | **Bloccante** — verifica se simbolo/asset e' borrowable e limite disponibile | Parametri: `instId`, `mgnMode` |
| 4 | `/api/v5/account/set-leverage` | POST | Imposta leva per valuta/coppia in margin mode | Solo se si vuole leva diversa da 1x |
| 5 | `/api/v5/account/positions` | GET | Riconoscere long/short via `posCcy`; monitorare `mgnRatio` | Gi a usato in altri contesti |
| 6 | `/api/v5/public/interest-rate-loan-quota` | GET | **Pubblico** — tasso interesse reale per asset | Per check pre-sessione e calcolo costi |
| 7 | `/api/v5/account/quick-margin-borrow-repay-history` | GET | Storico borrow/repay | Per DB fields `borrow_amount`, `margin_interest` |
| 8 | `/api/v5/trade/order-algo` | POST/GET | Stesso endpoint bracket long — nessuna modifica | Solo direzione invertita |
| 9 | `/api/v5/account/interest-limits` | GET | Limite interesse/quota interest-free | Da verificare rilevanza per Spot mode |

**Prerequisito prima di tutto:** nessuno di questi endpoint e' mai stato chiamato empiricamente sul vostro account reale. Serve uno spike read-only (punti 1, 3, 6).

---

## 5. Feature: Check Disponibilita' Short per Simbolo

### 5.1 Perche'

Prima che l'utente apra una sessione, deve sapere se il simbolo supporta lo short — altrimenti si riproduce lo stesso problema attuale (segnali SELL scartati).

### 5.2 Quando verificare

Al momento della selezione simbolo, nello stesso punto del flusso dove oggi gira l'instrument discovery (TASK-1116.G).

### 5.3 Cosa verificare

Per il simbolo selezionato (es. `BTC-EUR`):
1. `GET /api/v5/account/max-loan?instId=BTC-EUR&mgnMode=cross` — se il valore ritorna 0 o l'endpoint erroa, **short non disponibile**
2. `GET /api/v5/public/interest-rate-loan-quota?ccy=BTC` — se l'asset non compare nella risposta, conferma aggiuntiva di non-disponibilita'; se compare, il tasso va mostrato all'utente

### 5.4 Cosa mostrare all'utente

- **"Short disponibile — tasso attuale: X% APR"** se `max-loan > 0`
- **"Short non disponibile per questo simbolo"** se `max-loan = 0` o endpoint fallisce

### 5.5 Implicazione per il simbolo di default

OKB e' il candidato piu' a rischio di non essere borrowable (token nativo, mercato prestito probabilmente sottile). Questo check risolvera' la domanda in modo definitivo.

### 5.6 Integrazione con TASK-1116.G

L'endpoint `/api/scalping/exchange/instruments` puo' restituire anche `short_available: bool` e `short_borrow_rate_apr: float | null` per strumento, calcolato una volta per ciclo di discovery.

---

## 6. Time-Stop Legato allo SL — **TBD**

### 6.1 Concetto (da approfondire)

Invece di un time-stop a durata fissa, l'idea e': il trade resta aperto finche' il costo cumulato dell'interesse non equivale al valore dello Stop Loss. A quel punto la posizione viene chiusa — non perche' il prezzo ha toccato lo SL, ma perche' l'interesse accumulato "ha eroso" un budget di rischio equivalente.

### 6.2 Perche' NON e' ancora chiuso

Tre ambiguita' da risolvere in sessione dedicata:
1. **Contro cosa si misura l'interesse accumulato?** Valore assoluto dello SL nominale, o budget di rischio residuo che si aggiorna col movimento prezzo?
2. **L'interesse "consuma" lo SL o si somma al movimento di prezzo?** Se prezzo si muove leggermente contro + interesse accumula, la condizione deve scattare sulla somma dei due.
3. **Come si traduce "equivale allo SL" in una soglia calcolabile in tempo reale?** Valore assoluto vs percentuale sul notional, polling ogni accrual vs stimato.

### 6.3 Cosa portare alla sessione dedicata

- Tassi di interesse reali per BTC ed ETH (via `interest-rate-loan-quota`)
- Conferma se OKB e' borrowable
- Valore SL attuale del long (1,05% netto, da TASK-OKX-RECAL) come riferimento

---

## 7. Task da Aprire

> Nota: i task vanno aperti solo dopo che il time-stop (6) sara' chiuso in sessione dedicata.

| # | Task | Descrizione | Prerequisito |
|---|------|-------------|--------------|
| T1 | Spike read-only OKX account | Chiamare punti 1, 3, 6 della tabella API sul conto reale | Nessuno |
| T2 | Check disponibilita' short | Implementare feature 5 (badge simbolo) | T1 |
| T3 | Adapter short margin | Aggiungere metodi margin all'OkxExchangeAdapter | T1 |
| T4 | ExecutionLoop branch short | `_open_short()`, `_close_short()`, repay automatico | T2, T3 |
| T5 | DB migration | Nuove colonne `scalping_trades`/`scalping_sessions` | T4 |
| T6 | Time-stop (se approvato) | Logica interest-based stop | Sessione dedicata |

---

*Documento generato da `docs/recap/2026-07-21_okx-short-selling-analysis-recap.md` — 21 luglio 2026*
*Prossima revisione: dopo sessione dedicata time-stop (6) e spike read-only (T1)*
