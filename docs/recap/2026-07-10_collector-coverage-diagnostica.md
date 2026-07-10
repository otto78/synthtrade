# TASK-1119 — Collector Intelligence: Diagnostica Coverage Reale per Simbolo

**Priorità:** ALTA — prerequisito per qualsiasi fix successivo
**Fase:** 1a (diagnostica pura, zero rischio, nessun cambio di comportamento)
**Dipendenze:** nessuna (usa quanto già fatto in TASK-1116.B: FUTURES_SYMBOL_MAP con OKB-EUR → None)
**Principio guida:** "no estimates, only real data" — questo task produce SOLO log, non cambia nessuna soglia, peso o gate. Il fix comportamentale (1b) parte solo dopo aver letto questi log su una sessione reale.

---

## Problema

Oggi il coverage/bypass del `SignalAggregator` confronta "quanti collector hanno risposto" contro un `min_collectors` fisso pensato per 8 collector totali. Ma per simboli come OKB-EUR, 3 collector (funding_rate, open_interest, long_short_ratio) sono **strutturalmente impossibili** da ottenere su OKX per uno spot EUR senza perpetual — non è un fallimento transitorio, non risponderanno MAI per quel simbolo.

Il denominatore attuale non distingue:
- "collector che non ha ancora risposto ma potrebbe" (transitorio)
- "collector che non risponderà mai per questo simbolo" (strutturale)

Risultato: il sistema logga `2 collector concordi` e poi bypassa l'intelligence per pochi collector, quando in realtà — per quel simbolo — 2 su un massimo strutturale di 4-5 potrebbe essere una coverage accettabile.

## Obiettivo di questo task

Calcolare e loggare, per ogni ciclo di scoring, la **coverage reale**: peso dei collector che hanno risposto diviso peso dei collector strutturalmente disponibili per quel simbolo — **senza cambiare nessun comportamento di trading**.

---

## Modifiche

### 1. Aggiungere `is_symbol_supported()` ai 3 collector Binance-Futures-bound

**File:** `funding_rate.py`, `open_interest.py`, `long_short_ratio.py`

```python
def is_symbol_supported(self, symbol: str) -> bool:
    """
    True se il simbolo può strutturalmente avere questo dato
    (es. perpetual futures esistente), indipendentemente dal
    fatto che la chiamata riesca o fallisca in questo momento.

    Usa la stessa FUTURES_SYMBOL_MAP già presente (TASK-1116.B).
    Se il simbolo non è nella mappa, ritorna True in modo
    conservativo (non possiamo escluderlo a priori senza dati).
    """
    if symbol not in FUTURES_SYMBOL_MAP:
        return True
    return FUTURES_SYMBOL_MAP[symbol] is not None
```

### 2. Aggiungere `get_configurable_weight_total(symbol)` in `signal_score_engine.py`

```python
def get_configurable_weight_total(self, symbol: str) -> tuple[float, list[str]]:
    """
    Calcola il peso configurabile totale per questo simbolo.

    Esclude dal denominatore:
    - whale, se SCALPING_WHALE_ENABLED=False (comportamento già
      esistente da TASK C2 del supervisor-implementation-plan)
    - funding_rate/open_interest/long_short_ratio, se
      is_symbol_supported(symbol) == False per quel collector

    Ritorna (peso_totale_configurabile, lista_nomi_esclusi_strutturalmente)
    """
    weights = dict(self.WEIGHTS)
    excluded: list[str] = []

    if not settings.SCALPING_WHALE_ENABLED:
        weights.pop('whale', None)

    for name, collector in (
        ('funding_rate', self.funding_rate_collector),
        ('open_interest', self.oi_collector),
        ('long_short_ratio', self.ls_collector),
    ):
        if collector is not None and hasattr(collector, 'is_symbol_supported'):
            if not collector.is_symbol_supported(symbol):
                weights.pop(name, None)
                excluded.append(name)

    return sum(weights.values()), excluded
```

### 3. Log diagnostico nel ciclo di scoring esistente

Nel punto dove oggi si calcola `coverage` (già presente, vedi TASK-841/850), aggiungere — **in aggiunta**, non in sostituzione:

```python
configurable_total, structurally_excluded = self.get_configurable_weight_total(symbol)
responded_weight = sum(self.WEIGHTS[k] for k in raw_scores if k in self.WEIGHTS)
real_coverage = responded_weight / configurable_total if configurable_total > 0 else 0.0

no_response_transient = [
    k for k in self.WEIGHTS
    if k not in raw_scores and k not in structurally_excluded
    and (k != 'whale' or settings.SCALPING_WHALE_ENABLED)
]

logger.debug(
    "[ScoreEngine][COVERAGE_REAL] symbol=%s configurable_total=%.2f "
    "responded_weight=%.2f real_coverage=%.1f%% "
    "structurally_unavailable=%s no_response_transient=%s "
    "old_coverage_field=%.1f%%",
    symbol, configurable_total, responded_weight, real_coverage * 100,
    structurally_excluded, no_response_transient, coverage * 100,
)
```

Nota: `old_coverage_field` è il valore già esistente calcolato con denominatore fisso — loggarlo accanto al nuovo serve a verificare quanto diverge, prima di decidere se sostituirlo.

---

## Verifica di completamento

1. Avviare una sessione paper o demo su un simbolo EUR (es. OKB-EUR o BTC-EUR).
2. Dopo 5-10 minuti, estrarre le righe `[ScoreEngine][COVERAGE_REAL]` dal log.
3. Confermare a mano che:
   - per OKB-EUR, `structurally_unavailable` contenga esattamente `funding_rate`, `open_interest`, `long_short_ratio` (coerente con TASK-1116.B)
   - `real_coverage` sia sensibilmente più alto di `old_coverage_field` per lo stesso ciclo (perché il denominatore è più piccolo e corretto)
4. Ripetere su un simbolo con perpetual reale (es. BTC-EUR) e confermare che `structurally_unavailable` sia vuoto o quasi, e che i due valori di coverage siano più vicini tra loro.

**Nessuna azione di trading deve cambiare in questo task.** Se dopo la verifica `real_coverage` risulta consistentemente alto anche quando il sistema oggi bypassa l'intelligence, quello è il segnale per aprire TASK-1120 (fix comportamentale: redistribuzione pesi + sostituzione del bypass con soglia scalata) — con numeri derivati da questi log, non ipotizzati.

---

## Esplicitamente fuori scope per questo task

- Nessuna modifica a `min_collectors`, alla soglia `signal_strength_threshold`, o al comportamento di bypass in `signal_aggregator.py`.
- Nessuna redistribuzione dei pesi tra collector.
- Nessun nuovo collector OKX-specifico (order book imbalance, spread, funding OKX nativo) — quella è una fase successiva e separata, da valutare solo se questo task conferma che il vero problema è la coverage e non altro.
