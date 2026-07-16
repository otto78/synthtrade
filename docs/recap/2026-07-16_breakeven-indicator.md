# Recap — 2026-07-16: Breakeven indicator + OKX OCO fee fix

## Contesto

Sessione live BTC-EUR. Utente richiedeva un indicatore di breakeven sulla barra di progresso del position-ticker, con marker giallo che mostra il prezzo di break-even (entry + fee round-trip).

---

## Problemi trovati e risolti

### 1. Breakeven marker posizionato male sulla barra (FIX frontend)

**Problema:** `getBreakevenPct()` e `getProgressPct()` usavano i prezzi lordi dei bracket OKX (`stop_loss_price`/`take_profit_price`) per mappare il marker sulla barra. Con SL=-1.05% netto, il prezzo lordo SL era solo -0.35% da entry (le fee assorbono gran parte della perdita). Risultato: entry appariva al ~13% della barra, BE al ~40% — entrambi a sinistra.

**Fix:** Riscritte entrambe le funzioni in `position-ticker.component.ts` per usare le percentuali nette SL/TP configurate (`stop_loss_pct`/`take_profit_pct`) anziché i prezzi lordi:
- Barra virtuale: SL = entry × (1 - slDist%), TP = entry × (1 + tpDist%)
- Con SL=1.05%, TP=1.55%, BE=0.55%: marker BE a `(0.55+1.05)/(1.05+1.55) × 100 = 61.5%` — lato destro ✓
- Il fill della barra usa `current_price` mappato sulla stessa scala

**File:** `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/position-ticker.component.ts`

### 2. Layout UI breakeven migliorato (FIX frontend)

**Problema:** Il tag BE era posizionato assoluto dentro la barra, spesso fuori viewport. Testo "Below Breakeven" troppo piccolo, senza spaziatura.

**Fix:** Ristrutturato template e CSS:
- Rimosso il `breakeven-tag` posizionato `absolute` dalla barra
- Aggiunto `breakeven-row` sotto la barra con BE tag a sinistra, status a destra
- Margine 14px sotto la barra, testo BE 11px, status 12px
- Color-coded: "Above Breakeven" in verde, "Below Breakeven" in rosso

**File:** `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/position-ticker.component.ts`

### 3. OKX OCO usa market orders (taker), non maker — fee round-trip errato (FIX backend)

**Problema CRITICO:** Il backend calcolava `breakeven_pct` e le fee di exit usando `"maker"` per l'exit fee:
```python
exit_fee_rate = _get_fee_rate(fee_tier, "maker", 0.001)  # OCO orders = maker
```
Ma OKX OCO usa `tpOrdPx: "-1"` e `slOrdPx: "-1"` → entrambe le gamme sono **market order (taker)**.

Con il vecchio calcolo: taker(0.35%) + maker(0.20%) = **0.55%** — sbagliato.
Con il fix: taker(0.35%) + taker(0.35%) = **0.70%** — corretto.

**Conferma:** L'ordine OCO su OKX mostra "TP Market" e "SL Market". Log OKX REST API: `[OKX FEE DIRECT] BTC-EUR maker=0.0020 taker=0.0035`.

**Fix:** Cambiate 10 occorrenze in `router.py` da `"maker"` a `"taker"` per l'exit fee:
- `exit_fee_pricing` (line ~2013) — pricing iniziale bracket
- `exit_fee_rate` (line ~531, ~1286) — calcolo PnL
- `exit_fee_r` (line ~1534) — position update PnL
- `_xf` / `_xf_p` (line ~511, ~3790) — calcolo prezzi SL/SL lordi
- `breakeven_pct` (line ~2394, ~2503) — broadcast position events
- `_get_fee_rate(fee_tier, "maker", ...)` eliminato da tutti i contesti exit

**Impatto:** Questo fix corregge NON solo il display breakeven, ma anche:
- I prezzi lordi SL/TP calcolati al placement del bracket (più larghi, più fedeli)
- Il PnL calcolato nei broadcast position_update
- La fee_round_trip nel REST endpoint `/position`

**File:** `synthtrade/backend/app/scalping/router.py` (10 occorrenze)

---

## Dati verificati

**OKX REST API fee tier** (BTC-EUR, EU demo, base level):
```
maker = 0.0020 (0.20%)
taker = 0.0035 (0.35%)
```

**OKX OCO order type** (`/api/v5/trade/order-algo`):
```json
{
  "tpOrdPx": "-1",    // -1 = market order
  "slOrdPx": "-1",    // -1 = market order
  "tpTriggerPxType": "last",
  "slTriggerPxType": "last"
}
```

**Posizione attiva:**
- Entry: 55,907.80 (BUY BTC-EUR)
- SL: 55,626.32 (-1.05%)
- TP: 57,087.96 (+1.55%)
- Breakeven: 0.70% (taker + taker)

---

## Lezioni apprese

1. **OKX OCO usa market orders per entrambe le gamme** — il codice assumeva maker per l'exit perché "limit orders sono maker", ma OKX esegue come market order when triggered. Verificare sempre con ordini reali.
2. **Il fee tier OKX può avere maker e taker diversi** — maker 0.20% vs taker 0.35% non è simmetrico. Il codice precedente usava maker per l'exit → fee round-trip sottostimato.
3. **Usare le percentuali nette per la barra, non i prezzi lordi** — i prezzi lordi SL/TP sono molto asimmetrici rispetto a entry (SL vicino, TP lontano) perché le fee assorbono gran parte dello SL. La barra visiva deve usare le distanze nette configurate.

---

## File modificati

| File | Modifica |
|------|----------|
| `synthtrade/frontend/.../position-ticker.component.ts` | Marker BE + layout UI |
| `synthtrade/backend/app/scalping/router.py` | Exit fee: maker → taker (10 occorrenze) |
| `docs/recap/2026-07-16_breakeven-indicator.md` | Questo documento |
