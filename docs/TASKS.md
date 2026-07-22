# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-21. Task completati in `docs/ARCHIVE_TASKS.md`. Recap sessione: `docs/recap/2026-07-16_trading-safety-improvements.md`.

---

### Fix leg detection OCO + resilient polling loop — 2026-07-21

**Problema:** OCO con entrambi i trigger non-zero etichettava sempre `take_profit` indipendentemente dal leg effettivo. OKX EU `orders-algo-history` fornisce `actualSide` (`"tp"`/`"sl"`) ma non veniva usato.

**Soluzione:**
- `_normalize_algo_order`: priorità `actualSide` → fill_price vs trigger → `ordType`
- Step 3 nel polling loop: query `orders-algo-history?ordType=oco&state=effective` per `actualSide`
- Polling loop resiliente: ogni step con try/except isolato
- Recovery logging per monitoraggio

**Stato:** ✅ Completato — lint e test passanti

---

_Nessun task attivo. TASK-1166 spostato in archivio il 2026-07-21._

---
