# SynthTrade — Recap Situazione Completa (2026-07-14)

> Obiettivo: quadro completo dello stato per analisi approfondita (TASK-908/909 e validazione empirica).
> Head commit: `885cf1a` (main, pushato su `github.com/otto78/synthtrade`).

---

## 1. Stato sistema

- **Provider operativo:** OKX (EEA/EU) — unico exchange attivo (Bybit EU chiusa: non rilascia API key HMAC per bot custom).
- **Sessione live attiva:** `797794c7-adef-41a5-90d8-51f9c013a517`, simbolo **OKB-EUR**, `mode=live`. Posizione ripristinata: BUY @70.89, qty 0.28212, balance 3.2876 EUR.
- **Short selling:** NON implementato → tutti i segnali SELL vengono ignorati (`Short selling non implementato`). Solo BUY possibili.
- **Architettura:** backend FastAPI; pipeline = collectors intelligence → `SignalScoreEngine` → supervisor AI (decisioni pause/resume/threshold) → `router`/execution OKX; market data da WS business/public OKX; fill/TP-SL via REST polling (`orders-history`).

---

## 2. Collector Intelligence — stato su OKB-EUR (da log live post-fix)

| Collector | active | status | Fonte | Nota |
|---|---|---|---|---|
| funding_rate | on | OK | OKX `/funding-rate` nativo | TASK-1153 |
| open_interest | on | OK | OKX perpetual nativo | TASK-1153 |
| long_short_ratio | on | OK | OKX rubik `ccy` | TASK-1158 (14/07) |
| fear_greed | on | OK | CryptoFear&Greed | indipendente |
| sentiment | on | OK | CryptoCompare+NewsAPI+RSS | TASK-1154 |
| whale | on | **NONE** | Blockchair (BTC/LTC only) | TASK-1155 — atteso su OKB |
| onchain | on | OK* | proxy macro | TASK-1156 pending (fallback robusto) |
| order_book_imbalance | on | OK | OKX books sz=20 | TASK-1151 |
| spread | on | OK | OKX ticker | wiring **OFF** (TASK-1152), visibile solo in diag |
| cvd | on | OK | trades WS | calcolato da `cvd_calculator` |

- `real_coverage = 73.9%` (configurable_total=1.15, responded_weight=0.85)
- `structurally_unavailable = []` (nessun collector bloccato per design)
- **whale=NONE** è *graceful* (`no_response_transient`, non `structurally_unavailable`): OKB non esiste su Blockchair; OKX-asset richiede Whale Alert API a pagamento → TASK-1155 bassa priorità, non blocca.

---

## 3. Configurazione trading attuale

| Parametro | Valore | Fonte |
|---|---|---|
| STOP_LOSS (net) | **1.05%** | `backend/.env` (TASK-OKX-RECAL, 14/07) |
| TAKE_PROFIT (net) | **1.55%** | `backend/.env` |
| R:R | **1.48:1** | derivato |
| Fee maker / taker OKX | 0.20% / 0.35% | screenshot fee tier |
| **Round-trip fee** | **0.70%** | taker+taker (entry+exit market) |
| Signal-strength threshold | **~10–15** | `config.py` `SCALPING_SIGNAL_STRENGTH_THRESHOLD=10.0`; `config_loader`/DB override ~15 |
| Weights (DEFAULT_WEIGHTS) | funding 0.20, cvd 0.20, oi 0.15, lsr 0.15, fg 0.15, whale 0.10, sentiment 0.05, onchain 0.0, obi 0.15 | `signal_score_engine.py:64` |

Trade eseguibile solo se `|score| >= threshold` **AND** `bias != neutral` (`signal_score_engine.py:525`).

> Nota: lo SL/TP a 0.3%/0.5% storico era geometricamente impossibile con fee 0.70% (round-trip > SL). I 34.3% win-rate su 70 trade storici (BNBUSDC) NON sono un baseline affidabile.

---

## 4. IL COLLO DI BOTTIGLIA — raccolta dati empirica lentissima

**Osservazione (Andrea, 14/07):** la sessione live genera **~1–2 trade/giorno**.

**Perché:**
1. Fee OKX round-trip **0.70%** → SL/TP devono essere ampi (1.05%/1.55%) per essere matematicamente sostenibili.
2. Soglia score **alta (~10–15)** → pochi setup qualificano come tradeabili.
3. **Solo BUY** (short non implementato) → metà dei segnali potenziali scartata.

**Conseguenza:** ogni task di validazione che dipende dagli *esiti* dei trade reali è a **mesi di distanza** alla velocità attuale.

---

## 5. Task di validazione e i loro gate (tutti lenti)

| Task | Gate originale | Dipende da esiti trade? | Stato |
|---|---|---|---|
| **TASK-1157** CVD grace | "dopo 100 trade" | NO (codice difensivo) | Pending — **si può chiudere ora** |
| **TASK-1159** reweight pesi | "2–3 sessioni reali" + esiti | SÌ (parziale) | Pending — reweight strutturale possibile ora |
| **TASK-898** trend analysis | ≥20 trade chiusi con `signal_log_id` | SÌ | Pending |
| **TASK-906** falling knife | drop di mercato reale | SÌ | Pending |
| **TASK-908/909** resume guard / async | riservati per analisi | no | Riservati |
| **TASK-1155** whale | API key a pagamento | n/a | Bassa prio, atteso NONE su OKB |
| **TASK-1156** on-chain fallback | — | n/a | Pending bassa prio |

**Punto chiave:** il gate "100 trade" di TASK-1157 era una scelta conservativa interna, non un requisito di sistema. CVD è `OK` in *ogni* sessione live → il grace (non penalizzare se CVD manca) è codice difensivo per uno scenario che non si è mai verificato. Si implementa e chiude senza aspettare dati.

---

## 6. Opzioni per sbloccare la validazione (da analizzare)

**A. Decoupling difensivo (zero dati)**
- TASK-1157: implementare il grace ora e chiudere. Rischio nullo.

**B. Reweight strutturale (dati già disponibili)**
- La `[COVERAGE_REAL]` per-sessione dà reliability/coverage di ogni collector *senza* esiti trade.
- TASK-1159 può essere fatto in due fasi: (1) ora, pesi su affidabilità strutturale dei collector; (2) poi, affinamento su esiti reali quando accumulati.

**C. Aumentare la *velocità* di raccolta dati**
- **Più simboli live in parallelo** (BTC-EUR, ETH-EUR): moltiplica il rate di trade/esiti *senza* cambiare il rischio per-simbolo. Leva più pulita della soglia bassa.
- **Abbassare la soglia score** (~10→es. 6): più trade, ma più rumore/falsi positivi.
- **Short selling**: sbloccherebbe metà dei segnali, ma è lavoro architetturale grosso (EPICA SHORT, TASK-1000 sospeso).

**D. Riutilizzare lo storico (con caveat)**
- 70 trade BNBUSDC storici (SL/TP 0.3/0.5, pre-collector, pre-migrazione OKX): utili solo per analisi *qualitativa* di regime/trend, **non** come baseline quantitativa per reweight.

---

## 7. Domande aperte per l'analisi

1. TASK-1157 va implementato/chiuso ora (senza attendere 100 trade)? → **Raccomandato sì.**
2. Leva per velocità dati: **più simboli in parallelo** vs **soglia score più bassa**? (La prima non degrada la qualità del segnale.)
3. TASK-1159: accettare un reweight *strutturale* ora (su coverage/reliability) e rinviare il tuning *outcome-based*?
4. Lo short selling è nello scope 2026? (Sbloccherebbe ~50% dei segnali ma richiede EPICA SHORT.)

---

## 8. Recenti commit (head → old)

```
885cf1a chore(logging): compact per-collector diagnostic + TASK-1155 whale analysis
ba43825 feat(intelligence): LSR OKX provider-aware + fix OKX_PERPETUAL_MAP OKB bug (TASK-1158)
5df5afe fix: merge conflicts + OBI/Spread symbol-normalization regression
430b9e7 docs: TASKS.md/STORY.md TP/SL fill detection
8512b77 fix: Consolidate orders-history calls in OKX polling loop
4b5825a fix: OKX EU algo fill detection via orders-history fallback
... (vedi git log per il resto)
```

---

*Recap generato per analisi (non modifica codice). Prossimo passo consigliato: implementare TASK-1157 (difensivo, zero dati) e scegliere la leva di C per la raccolta dati.*
