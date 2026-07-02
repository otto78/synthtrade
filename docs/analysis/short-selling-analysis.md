# Short Selling — Roadmap e Stato

> **Tema trasversale** che emerge da: `docs/recap/2026-06-20_risk-controls-audit.md`, `docs/recap/2026-06-25_mean-reversion-short.md`, `docs/recap/2026-06-26_trailing-stop-loss.md`.
> **Consolidato in:** `docs/recap/MASTER_RECAP.md` §4.1.
> **Architettura:** `docs/short-selling-architecture.md`.

---

## 1. Stato attuale

**Nessun codice scritto.** Architettura completa a 4 fasi pronta, zero implementazione.

---

## 2. Perché è importante

Dai log reali: in due sessioni osservate, ~15-22 segnali SELL validi sono stati scartati con log `"Short selling non implementato"`. Il sistema è limitato a LONG-only, il che significa:
- In regime `trending_down`, l'unica opzione è non fare nulla o fare mean-reversion contro-trend (rischioso)
- Il Supervisor non ha visibilità di questo blocco architetturale e propone `change_strategy`/`update_threshold` quando il vero problema è l'assenza dello short
- Il Resume Guard (TASK-908) è un palliativo per mitigare il problema in attesa dello short

---

## 3. Architettura a 4 fasi

### Fase 1 — Borrow/repay isolato (TASK-1000: WalletOrchestrator)
- `open_short()` (borrow + sell) e `close_short()` (buy + repay)
- Validabile su testnet senza toccare la logica di trading esistente
- **Alternativa emersa il 26/06:** `sideEffectType: "AUTO_BORROW_REPAY"` su `create_margin_order` — da validare su testnet e decidere se sostituisce o si combina con l'approccio manuale
- **WalletOrchestrator**: snapshot→resolve→execute→verify, priorità Spot→Funding→Earn

### Fase 2 — Entry-side awareness nel SignalAggregator
- Decisione di prodotto aperta: short solo trend-following (consigliato) vs anche short mean-reversion (più rischioso)

### Fase 3 — OCO mirrorato
- TP sotto l'entry, SL sopra, PnL invertito (entry−exit) ovunque oggi si assume long-only

### Fase 4 — Risk Controls / StrategySelector simmetrici
- % SL/TP applicate per direzione invece che solo per long

---

## 4. Dettagli tecnici raccolti

| Parametro | Valore | Fonte |
|-----------|--------|-------|
| `userMinBorrow` | 0 per USDC | Documentazione Binance |
| Vincolo reale | `minNotional` del pair | API Binance |
| Margin Level minimo | 1.1 (liquidazione) | Binance Margin |
| Buffer sicuro consigliato | >2.0 | Analisi 26/06 |
| Tipo margin raccomandato | Isolated Margin | Per scalping short |
| Collaterale | USDC nel Margin account (non l'asset preso a prestito) | API Binance |
| Interessi orari | ~0.0001 USDC/ora su trade da 10 USDC | Trascurabile per scalping |
| Universal Transfer API | `POST /sapi/v1/asset/transfer` | Per movimenti Funding/Spot/Margin |
| Earn→Spot redeem | `POST /sapi/v1/simple-earn/flexible/redeem` | Endpoint dedicato |

---

## 5. Decisioni aperte

1. **AUTO_BORROW_REPAY vs margin_short.py manuale** — emerso il 26/06, non deciso
2. **Short solo trend-following o anche mean-reversion** — impatta Fase 2
3. **WalletOrchestrator come prerequisite o parte della Fase 1** — TASK-1000 lo tratta come prerequisite

---

## 6. Collegamento con task

| Task | Cosa | Priorità |
|------|------|----------|
| TASK-1000 | WalletOrchestrator Fase 1 (resolve puro + snapshot) | 🔴 Alta |
| TASK-908 | Resume Guard (palliativo in attesa dello short) | 🔴 Alta |
| TASK-INVEST-014 | Verificare se Supervisor menziona blocco SHORT nel prompt | 🔍 Da Investigare |

---

**Ultima modifica:** 2026-07-02 — Cline