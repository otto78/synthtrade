# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-23. Task completati in `docs/ARCHIVE_TASKS.md`.

---

_Nessun task attivo._

---

### EPICA: Short Selling OKX Spot Margin

> **Stato:** Fase 1 MVP completata (TASK-1220→1226). Account in Simple mode — solo **cross margin**.
> **Architettura:** `docs/architecture/okx-short-selling-architecture.md`
> **Risultati spike:** `docs/analysis/okx-short-spike-results.md`
> **Piano:** `docs/plans/okx-short-selling-epic-combined.md`
> **Prossimo passo:** TASK-1229 (validazione demo) o TASK-1228 (test integrazione)

| Task | Titolo | Blocco | Stato |
|------|--------|--------|-------|
| TASK-1220 | Spike read-only OKX margin endpoints | Fase 0 | ✅ Done (cross margin, gate passed) |
| TASK-1221 | Check disponibilità short per simbolo | Fase 1 | ✅ Done (badge + API + 4 test) |
| TASK-1222 | OkxExchangeAdapter margin methods + tdMode | Fase 1 | ✅ Done (14 subtask + 8 test) |
| TASK-1223 | Session config short_enabled + SignalAggregator gate | Fase 1 | ✅ Done (flag + gate + toggle + 11 test) |
| TASK-1224 | Flusso apertura short (MVP) | Fase 1 | ✅ Done (margin_mode + bracket + emergency close + paper + 11 test) |
| TASK-1225 | Chiusura short + time-stop fisso 48h (MVP) | Fase 1 | ✅ Done (PnL inverted + timestop job + 17 test) |
| TASK-1226 | DB migration: campi short-specific | Fase 1 | ✅ Done (migration + CHECK constraint + db_ops) |
| TASK-1227 | Frontend: supporto UI completo per short | Fase 2 | ✅ Done (badge LONG/SHORT + trade log + timestop style) |
| TASK-1228 | Test di integrazione short (fake adapter) | Fase 2 | ⏳ Ready (1225 done) |
| TASK-1229 | Validazione demo/live minimo end-to-end | Fase 2 | ⏳ Ready (1224 done) |
| TASK-1230 | Time-stop interest-based completo (Layer 3-6) | Fase 2 | ⏳ Ready (depends on 1220 only) |
| TASK-1231 | Supervisor AI: awareness short | Fase 2 | ❌ Blocked (1225) |
| TASK-1232 | Risk Manager simmetrico per short | Fase 2 | ❌ Blocked (1225,1230) |
| TASK-1233 | Documentazione: chiusura riferimenti superseded | Fase 3 | ⏳ Ready |

---
