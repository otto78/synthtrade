# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-22. Task completati in `docs/ARCHIVE_TASKS.md`.

---

_Nessun task attivo._

---

### EPICA: Short Selling OKX Spot Margin

> **Stato:** TASK-1220 completato (GATE PASSATO). Account in Simple mode — solo **cross margin**.
> **Architettura:** `docs/architecture/okx-short-selling-architecture.md`
> **Risultati spike:** `docs/analysis/okx-short-spike-results.md`
> **Prossimo passo:** TASK-1222 — adapter margin methods

| Task | Titolo | Blocco | Stato |
|------|--------|--------|-------|
| TASK-1220 | Spike read-only OKX margin endpoints | Fase 0 | ✅ Done (cross margin, gate passed) |
| TASK-1221 | Check disponibilità short per simbolo | Fase 1 | ✅ Done (badge + API + 4 test) |
| TASK-1222 | OkxExchangeAdapter margin methods + tdMode | Fase 1 | ✅ Done (14 subtask + 8 test) |
| TASK-1223 | ExchangeAdapterProtocol — open_short | Fase 1 | ⏳ Ready (1222 done) |
| TASK-1224 | OkxExchangeAdapter — open_short | Fase 1 | ⏳ Ready (1222,1223 done) |
| TASK-1225 | candle_processor — invia ordine SELL | Fase 1 | ❌ Blocked (1224) |
| TASK-1226 | _execution_state — short_enabled flag | Fase 1 | ⏳ Ready |
| TASK-1227 | Session start — short_enabled | Fase 1 | ❌ Blocked (1226) |
| TASK-1228 | DB ops — position_side | Fase 1 | ⏳ Ready |
| TASK-1229 | Supervisor prompt — contesto short | Fase 1 | ⏳ Ready |
| TASK-1230 | Time-stop Layer 1+2 (MVP) | Fase 2 | ⏳ Ready (depends on 1220 only) |
| TASK-1231 | Frontend — short_enabled + status | Fase 2 | ❌ Blocked (1227) |
| TASK-1232 | Test end-to-end | Fase 2 | ❌ Blocked (1225,1228,1230) |
| TASK-1233 | Test integrazione completo | Fase 2 | ❌ Blocked (1231,1232) |

---
