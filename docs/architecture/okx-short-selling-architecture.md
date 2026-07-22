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
  "tdMode": "isolated",   // oggi "cash" (spot puro, niente borrow)
  "side": "sell",
  "ordType": "market",
  "sz": "..."
}
```

Cambia solo `tdMode` (da `cash` a `isolated`) e `side`. **Non esiste un parametro "auto-borrow" nell'ordine** — il borrow scatta automaticamente al fill se l'account ha `enableSpotBorrow=true` e c'e' collaterale/limite sufficiente.

**Decisione: isolated (non cross)** — il rischio di ogni posizione e' segregato; se una posizione short va in liquidazione, non intacca il resto del saldo. Piu' sicuro per un sistema in fase di test.

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
| 2 | `/api/v5/trade/order` | POST | Stesso endpoint long — cambia solo `tdMode=isolated` e `side=sell` | Nessun nuovo metodo adapter |
| 3 | `/api/v5/account/max-loan` | GET | **Bloccante** — verifica se simbolo/asset e' borrowable e limite disponibile | Parametri: `instId`, `mgnMode` |
| 4 | `/api/v5/account/set-leverage` | POST | Imposta leva per singola **valuta** (`ccy`), non per coppia | Solo se si vuole leva diversa da 1x |
| 4b | `/api/v5/account/leverage-info` | GET | **NUOVO** — leggere la leva attualmente impostata prima di modificarla | |
| 5 | `/api/v5/account/positions` | GET | Riconoscere long/short via `posCcy`; **`mgnRatio` per monitorare rischio liquidazione** | Soglie: ≥300% sicuro, 100-300% alert, ≤100% liquidazione |
| 6 | `/api/v5/public/interest-rate-loan-quota` | GET | **Pubblico** — tasso interesse reale per asset | Per check pre-sessione e calcolo time-stop |
| 7 | `/api/v5/account/quick-margin-borrow-repay-history` | GET | Storico borrow/repay | Per DB fields `borrow_amount`, `margin_interest` |
| 8 | `/api/v5/trade/order-algo` | POST/GET | Stesso endpoint bracket long — nessuna modifica | Solo direzione invertita |
| 9 | `/api/v5/account/interest-limits` | GET | Eventuale quota interest-free | Da verificare rilevanza per Spot mode |
| 10 | `/api/v5/account/position-tiers` | GET | **NUOVO** — maintenance margin ratio per tier di posizione/simbolo | Necessario per calcolare collaterale minimo reale |

**Prerequisito prima di tutto:** nessuno di questi endpoint e' mai stato chiamato empiricamente sul vostro account reale. Serve uno spike read-only (punti 1, 3, 6, 10).

---

## 5. Feature: Check Disponibilita' Short per Simbolo

### 5.1 Perche'

Prima che l'utente apra una sessione, deve sapere se il simbolo supporta lo short — altrimenti si riproduce lo stesso problema attuale (segnali SELL scartati).

### 5.2 Quando verificare

Al momento della selezione simbolo, nello stesso punto del flusso dove oggi gira l'instrument discovery (TASK-1116.G).

### 5.3 Cosa verificare

Per il simbolo selezionato (es. `BTC-EUR`):
1. `GET /api/v5/account/max-loan?instId=BTC-EUR&mgnMode=isolated` — se il valore ritorna 0 o l'endpoint erroa, **short non disponibile**
2. `GET /api/v5/public/interest-rate-loan-quota?ccy=BTC` — se l'asset non compare nella risposta, conferma aggiuntiva di non-disponibilita'; se compare, il tasso va mostrato all'utente

### 5.4 Cosa mostrare all'utente

- **"Short disponibile — tasso attuale: X% APR"** se `max-loan > 0`
- **"Short non disponibile per questo simbolo"** se `max-loan = 0` o endpoint fallisce

### 5.5 Implicazione per il simbolo di default

OKB e' il candidato piu' a rischio di non essere borrowable (token nativo, mercato prestito probabilmente sottile). Questo check risolvera' la domanda in modo definitivo.

### 5.6 Integrazione con TASK-1116.G

L'endpoint `/api/scalping/exchange/instruments` puo' restituire anche `short_available: bool` e `short_borrow_rate_apr: float | null` per strumento, calcolato una volta per ciclo di discovery.

---

## 6. Time-Stop Interest-Based (Design Completo)

> Rif.: `docs/analysis/2026-07-21_okx-short-timestop-design.md` per dettagli, esempi numerici e valutazione complessiva.
> Decisioni chiuse: tasso **fisso** (bloccato all'apertura), margine **isolated**, meccanismo **buffer rolling 24h**.

### 6.1 Concetto

Il trade resta aperto finche' il costo cumulato dell'interesse non equivale al valore dello Stop Loss. Il meccanismo funziona con un **refresh orario** del bracket: ad ogni hora, ricalcoli SL/TP assumendo che l'interesse continuera' a maturare per altre **24h** oltre a quelle gia' trascorse (buffer rolling). Questo "spinge in avanti" il bracket in modo conservativo: se il PC si spegne subito dopo un refresh, il bracket piazzato resta sicuro per le successive 24h di silenzio.

**Risultato pratico:** lo SL si restringe nel tempo (l'interesse consuma budget di perdita) e il TP si allontana (l'interesse consuma profitto netto). Il processo e' **auto-limitante**: quando lo SL effettivo tocca zero, il sistema chiude, garantendo un tempo massimo di detenzione finito e calcolabile.

### 6.2 Formule (Layer per Layer)

**Layer 1 — Target netti (invariato, stessi valori del long):**
```
SL_net_target = 1.05%     (da TASK-OKX-RECAL)
TP_net_target = 1.55%
```

**Layer 2 — Aggiustamento fee (riuso di `_net_to_gross_pct`):**
```
SL_gross_fee_only = |_net_to_gross_pct(SL_net_target, fee_taker, fee_taker)|
TP_gross_fee_only = |_net_to_gross_pct(TP_net_target, fee_taker, fee_taker)|
```
Con fee taker 0,35%: `SL_gross_fee_only ≈ 0,35%`, `TP_gross_fee_only ≈ 2,26%`

**Layer 3 — Interesse proiettato (cuore del meccanismo):**
```
rate_hourly = APR_al_open / 365 / 24        (tasso fisso, bloccato all'apertura)
BUFFER_HOURS = 24                            (configurabile, copre notte di PC spento)

interest_projected_pct(t) = rate_hourly × (elapsed_real_h(t) + BUFFER_HOURS)
```
Il **primo bracket** (t=0) usa gia' `interest_projected_pct(0) = rate_hourly × BUFFER_HOURS` — non parte "nudo".

**Layer 4 — Soglie effettive:**
```
SL_effective_gross(t) = SL_gross_fee_only − interest_projected_pct(t)
TP_effective_gross(t) = TP_gross_fee_only + interest_projected_pct(t)
```

**Layer 5 — Prezzi bracket (direzione invertita rispetto al long):**
```
SL_price(t) = entry_price × (1 + SL_effective_gross(t) / 100)     [SL sopra entry]
TP_price(t) = entry_price × (1 − TP_effective_gross(t) / 100)     [TP sotto entry]
```

**Layer 6 — Floor guard:**
```
if SL_effective_gross(t) <= FLOOR_MIN_PCT:   # es. 0.02%
    → chiudi immediatamente a mercato
    → exit_reason = "stop_loss_interest"
```

### 6.3 Gate Pre-Apertura (validazione obbligatoria PRIMA di aprire lo short)

```
if (rate_hourly × BUFFER_HOURS) >= SL_gross_fee_only:
    → BLOCCA apertura short
    → motivo: "buffer di sicurezza (24h) incompatibile col tasso di interesse attuale"
```

### 6.4 Formula Tempo Massimo di Detenzione

```
elapsed_max_h = SL_gross_fee_only / rate_hourly − BUFFER_HOURS
```
Esempio con APR=15%: `0,35/0,0017123 − 24 ≈ 180 ore (~7,5 giorni)`.
Con APR=50%: `0,35/0,0057 − 24 ≈ 37 ore (~1,5 giorni)` — il meccanismo si autoregola.

### 6.5 Margine Isolated — Collaterale Necessario

- **Leva bassa** (1x-2x via `set-leverage`)
- **Collaterale ≥ 3× il notional** come regola pratica (per trade da 20€, tenere almeno 60€)
- **Verifica empirica obbligatoria**: al primo trade reale, leggere `mgnRatio` da `GET /api/v5/account/positions` — se e' gia' vicino a 300%, aumentare il collaterale
- Soglie OKX: ≥300% sicuro, 100-300% alert, ≤100% liquidazione forzata

### 6.6 Limiti Noti

- **Tasso fisso**: se il tasso reale sale molto durante la vita del trade, il calcolo sottostima l'interesse reale — mitigato dal buffer 24h
- **Refresh orario**: introduce una finestra di rischio operativo (cancel + replace bracket ogni ora) — va testata a fondo
- **Collaterale minimo reale** e' ancora ignoto — non aprire short live finche' non si ha un numero confermato

### 6.7 Raccomandazione: Implementazione in 2 Fasi

**Fase 1 (MVP):** short con SL/TP mirrorati identici al long, **nessun Layer 3-6**, ma con un **time-stop fisso conservativo** (48h flat) come rete di sicurezza. Serve solo a validare che apertura/chiusura short funzioni tecnicamente su OKX (tdMode, posCcy, bracket).

**Fase 2:** dopo aver osservato trade reali e il tasso interesse reale, introdurre il meccanismo completo Layer 3-6 con i numeri veri.

Questo evita di introdurre contemporaneamente: nuovo tipo ordine (short), nuovo margin mode (isolated), nuovo meccanismo rischio (interesse dinamico) e nuova logica refresh bracket — tutto insieme, senza aver mai visto un short reale.

---

## 7. Task da Aprire

| # | Task | Descrizione | Prerequisito | Fase |
|---|------|-------------|--------------|------|
| T1 | Spike read-only OKX account | Chiamare punti 1, 3, 6, 10 della tabella API sul conto reale | Nessuno | — |
| T2 | Check disponibilita' short | Implementare feature 5 (badge simbolo) | T1 | — |
| T3 | Adapter short margin | Aggiungere metodi margin all'OkxExchangeAdapter (`tdMode=isolated`) | T1 | — |
| T4 | ExecutionLoop branch short (MVP) | `_open_short()`, `_close_short()`, bracket identico long, time-stop 48h fisso | T2, T3 | Fase 1 |
| T5 | DB migration | Nuove colonne `scalping_trades`/`scalping_sessions` | T4 | Fase 1 |
| T6 | Time-stop interest-based completo | Layer 3-6 con tassi reali, refresh orario bracket | T4 + dati reali osservati | Fase 2 |

---

*Documento generato da `docs/recap/2026-07-21_okx-short-selling-analysis-recap.md` + `docs/analysis/2026-07-21_okx-short-timestop-design.md`*
*Ultimo aggiornamento: 21 luglio 2026*
