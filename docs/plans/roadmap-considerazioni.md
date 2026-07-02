# SynthTrade — Roadmap e Considerazioni
**Data:** 2 luglio 2026  
**Ruolo:** Indice sintetico con approfondimenti unici — per dettagli implementativi vedere i file citati.

---

## TL;DR

| Punto | Dettaglio |
|---|---|
| 1. Session log → Supervisor | Schema e criteri progettuali unici in questo file; per implementazione vedi `docs/architecture/supervisor-implementation-plan.md` Fase F |
| 2. Short selling / margin | Architettura dettagliata in `docs/architecture/short-selling-architecture.md`; criteri testnet→mainnet solo qui |
| 3. Risk Control card | Griglia audit e specifiche Angular qui; per fix cooldown vedi `docs/analysis/supervisor-analysis.md` #6 |

---

## 1. Session log → contesto del Supervisor AI

### 1.1 Schema dati (unico in questo file)

```sql
create table session_trade_log (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null,
  ts timestamptz not null default now(),

  regime_classified text not null,
  regime_confidence numeric,
  strategy_selected text not null,
  strategy_executed text not null,

  signal_score numeric,
  signal_breakdown jsonb,

  entry_price numeric,
  exit_price numeric,
  exit_reason text,
  pnl numeric,
  consecutive_loss_count_at_entry int,

  volatility_snapshot numeric,
  volume_snapshot numeric
);
```

Campi chiave non presenti altrove: `signal_breakdown`, `consecutive_loss_count_at_entry`, `volatility_snapshot`.

Per la pipeline di alimentazione (digest in tempo reale + job riflessione periodica), vedi `docs/analysis/supervisor-analysis.md` §3.1.

### 1.2 Versionamento

Taggare i record con la versione del `SignalScoreEngine` usata — altrimenti confronti storici diventano inutili.

---

## 2. Short selling / margin trading

### Criteri per passare da testnet a mainnet (unico in questo file)

Checklist minima:
- N operazioni testnet senza errori di borrow/repay
- Margin level monitorato e mai sceso sotto soglia di sicurezza in nessun test
- OCO short testato sia su TP che su SL
- `WalletOrchestrator` capace di muovere fondi Margin → Spot in caso di emergenza

Per architettura completa, fasi implementative e codice, vedi `docs/architecture/short-selling-architecture.md`.

---

## 3. Audit della Risk Control card

### Griglia domande audit (unica in questo file)

| Domanda | Perché conta |
|---|---|
| È solo **display** o **enforcement reale**? | Determina se è prevenzione o solo reporting |
| Quali soglie applica oggi? | Senza elenco esplicito non si può dire se è "completa" |
| Il trader legge i limiti **prima** di aprire un ordine o dopo? | Preventivo vs a posteriori |
| Viene loggato quando un trade viene bloccato? | Serve per verificare se sta funzionando |
| È aggiornata in real-time o a intervalli? | Rilevante per reazioni veloci |

### Specifiche Angular UI (unico in questo file)

- **Vista mismatch**: evidenziare visivamente righe dove `strategy_selected ≠ strategy_executed` — funge da data quality gate prima del Supervisor
- **Stato regole attive**: mostrare in tempo reale "Cooldown attivo: prossimo trade abilitato alle 14:32", "Limite drawdown: 60% utilizzato"

Per il fix cooldown, vedi `docs/analysis/supervisor-analysis.md` #6.

---

## Collegamenti

| Tema | File primario |
|---|
| Supervisor AI — issues e fix | `docs/analysis/supervisor-analysis.md` |
| Supervisor AI — piano implementazione | `docs/architecture/supervisor-implementation-plan.md` |
| Short selling — roadmap | `docs/analysis/short-selling-analysis.md` |
| Short selling — architettura | `docs/architecture/short-selling-architecture.md` |
| OKX — migrazione exchange | `docs/analysis/okx-api-reference-analysis.md` |
