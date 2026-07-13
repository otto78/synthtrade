# Collector Intelligence — Stato e Piano

> **Tema trasversale** che emerge da: `docs/recap/2026-06-27_strategie-scalping.md` (eliminato, contenuto in MASTER_RECAP), `docs/recap/MASTER_RECAP.md` §3 (bug #19).
> **Dataframe di riferimento:** `docs/scalping-dataflow-reference.md`.

---

## 1. Stato attuale

Il layer Signal Intelligence è il cuore architetturale del modulo Scalping v2.0. Oggi opera al **30%** della capacità prevista.

| Collector | Stato | Score contribution | Note |
|-----------|-------|-------------------|------|
| Fear & Greed Index | 🟢 Funzionante | 0.10 | Fallback cache funzionante su DNS error |
| Long/Short Ratio | 🟢 Funzionante | 0.10 | OK |
| Open Interest | 🟢 Funzionante | 0.10 | OK |
| Funding Rate | 🔴 Non funzionante | 0.10 | Da diagnosticare |
| CVD (Cumulative Volume Delta) | 🔴 Non funzionante | 0.10 | Grace period 100 trade, da osservare |
| Sentiment (social/media) | 🔴 Non funzionante | 0.10 | Da diagnosticare |
| Whale Alert | 🔴 Non funzionante | 0.10 | Da diagnosticare |
| On-Chain Metrics | 🔴 Non funzionante | 0.10 | Da diagnosticare |

**Totale**: 3/8 funzionanti = 0.30/0.80 contributo massimo.

---

## 2. Impatto

- Il SignalScoreEngine lavora con solo 3 collector su 8
- Le decisioni di Intelligence sono basate su un campione parziale del mercato
- Il Supervisor riceve un context impoverito
- Nuove strategie (es. Mean-Reversion) vengono giudicate con dati incompleti

---

## 3. Priorità di fix suggerita

Basata su facilità di fix e impatto:

1. **CVD**: già implementato, solo grace period da monitorare (100 trade). Verificare se dopo il warmup inizia a contribuire
2. **Funding Rate**: probabilmente un problema di endpoint/symbol mapping
3. **Sentiment**: API CryptoCompare o equivalente — verificare se è un problema di rate limit o di API key
4. **Whale Alert**: richiede API key dedicata
5. **On-Chain**: fonte dati più complessa, da valutare ultima

---

## 4. Collegamento con task

| Task | Cosa | Priorità |
|------|------|----------|
| TASK-INVEST-019 | Verificare endpoint /debug/pipeline per stato collector live | 🔍 Da Investigare |
| TASK-INVEST-016 | Verificare feed intermittenti (CryptoCompare/RSS) | 🔍 Da Investigare |
| TASK-COLLECTOR-001 | Provider-aware collector base (Funding Rate + Open Interest + Long/Short) | CRITICA |
| TASK-COLLECTOR-002 | Sentiment collector fallback affidabile | ALTA |
| TASK-COLLECTOR-003 | Whale collector OKX | MEDIA |
| TASK-COLLECTOR-004 | On-Chain collector con Blockchair | MEDIA |
| TASK-COLLECTOR-005 | CVD collector verifica grace period | BASSA |

---

## 5. OKX Integration Notes

**Problema principale:** I collector sono hardcoded per Binance Futures, non funzionano con OKX EUR pairs.

**Soluzione:**
- Aggiungere interfaccia `CollectorAdapter` con metodi read-only
- Implementare in `OkxExchangeAdapter` per derivatives (USDT pairs)
- Per EUR pairs, usare USDT pairs come proxy (BTC-EUR → BTC-USDT)

**OKX endpoints disponibili:**
- Funding Rate: `GET /api/v5/public/funding-rate-history` (perpetual futures)
- Open Interest: `GET /api/v5/public/open-interest` (perpetual futures)
- Long/Short Ratio: OKX non ha endpoint equivalente

---

**Ultima modifica:** 2026-07-13 — Aggiornato con TASK-COLLECTOR-001..005