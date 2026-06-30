# SynthTrade — Considerazioni Architetturali
**Data:** 20 giugno 2026
**Ambito:** (1) Session log → contesto AI Supervisor, (2) Short selling / margin, (3) Audit Risk Control card

---

## TL;DR

| Punto | Stato | Azione immediata proposta |
|---|---|---|
| 1. Session log → Supervisor | Bloccato dal sync bug UI/backend | Fixare la single source of truth dei log **prima** di darli in pasto all'AI |
| 2. Short selling / margin | Pianificazione esiste, Fase 1 non iniziata | Partire da `margin_short.py` su testnet, isolato da tutto il resto |
| 3. Risk Control card | Da verificare se è enforcement reale o solo display | Serve un audit puntuale + il cooldown anti-perdite-consecutive è il primo gap concreto noto |

Tutto qui sotto rispetta la regola "one change at a time": ogni sezione è pensata come una sequenza di step isolati e testabili singolarmente, non un blocco da implementare tutto insieme.

---

## 1. Session log → contesto del Supervisor AI

### 1.1 Il problema di fondo prima di tutto il resto

Prima di pensare a *come* dare i log al Supervisor, va risolto un problema più urgente: la UI mostra "Momentum Base" mentre il motore esegue `rsi_bollinger`. Se questo mismatch esiste nella visualizzazione, è molto probabile che la **stessa fonte dati sporca** finisca anche nei record salvati in sessione. Dare al Supervisor AI dati che non corrispondono alla realtà di esecuzione sarebbe peggio che non dargliene affatto: rinforzerebbe decisioni sbagliate con sicurezza apparente.

➡️ **Step 0 (prerequisito):** identificare la "single source of truth" per `strategy_executed`. Deve essere scritta da chi piazza l'ordine (l'execution layer), non ricostruita o duplicata altrove. Frontend, log di sessione e Supervisor devono leggere tutti dalla stessa riga.

### 1.2 Schema dati proposto per il session log

Per essere utile a un AI supervisor, il log non deve essere solo "cosa è successo" ma anche "cosa il sistema *pensava* in quel momento". Esempio di struttura (Supabase):

```sql
create table session_trade_log (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null,
  ts timestamptz not null default now(),

  -- decisione presa
  regime_classified text not null,        -- ranging / trending / volatile
  regime_confidence numeric,               -- 0-1, non solo la label
  strategy_selected text not null,
  strategy_executed text not null,         -- deve combaciare con selected, se no -> flag

  -- segnali che hanno portato alla decisione
  signal_score numeric,
  signal_breakdown jsonb,                  -- pesi/contributi singoli (EMA, RSI+BB, ecc.)

  -- esito
  entry_price numeric,
  exit_price numeric,
  exit_reason text,                        -- TP / SL / manual / timeout
  pnl numeric,
  consecutive_loss_count_at_entry int,

  -- contesto mercato
  volatility_snapshot numeric,
  volume_snapshot numeric
);
```

Punti chiave:
- `regime_confidence` numerico, non solo la label: serve per trovare a posteriori i casi di misclassificazione (es. il caso ranging-durante-breakdown già osservato).
- `signal_breakdown` in jsonb: rende ogni decisione spiegabile, non solo un numero finale.
- `consecutive_loss_count_at_entry`: dato già pronto per implementare il cooldown (vedi punto 3).

### 1.3 Pipeline di alimentazione del Supervisor

Non conviene mandare il log grezzo al Supervisor ad ogni chiamata: troppo rumore, troppi token, e l'AI rischia di reagire a singoli trade invece che a pattern. Propongo due livelli:

**A. Digest in tempo reale (per ogni decisione)**
Prima di ogni nuova decisione di regime/strategia, includere nel prompt un riassunto compatto: ultimi 5-10 trade con strategia, regime, esito. Poche righe, alta densità informativa.

**B. Riflessione periodica (job APScheduler)**
Un job a fine sessione (o ogni N ore) che chiede esplicitamente al Supervisor di analizzare il log della sessione e produrre osservazioni qualitative tipo: *"RSI+BB sottoperforma in mercati ranging-choppy, valutare di alzare la soglia di confidenza"*. Queste osservazioni si salvano in una nuova tabella, es. `supervisor_notes`, e diventano memoria persistente da iniettare nei prompt futuri — è il vero meccanismo di "apprendimento" senza dover allenare nulla.

Questo crea un loop: esito trade → log → riflessione periodica → nota → iniettata nella prossima decisione → strategia migliora nel tempo.

### 1.4 Miglioramenti al salvataggio

- Scrittura del log **transazionale**, agganciata direttamente al modulo di esecuzione (niente ricostruzioni separate lato UI).
- Versionamento leggero: se cambia la logica del `SignalScoreEngine`, taggare i record con la versione usata, altrimenti confronti storici diventano inutili.
- Rollup/compressione delle sessioni vecchie in statistiche aggregate (win rate per strategia/regime, drawdown medio) per non far esplodere la dimensione del contesto da passare al Supervisor nel tempo.

### 1.5 Lato Angular (visto che è il tuo terreno)

Sulla pagina del session log, due aggiunte ad alto valore/basso sforzo:
- **Vista mismatch**: evidenziare visivamente le righe dove `strategy_selected ≠ strategy_executed` — ti aiuta a debuggare tu stesso il sync bug, e funziona anche come "data quality gate" prima che quei dati finiscano al Supervisor.
- **Indicatore di confidenza regime**: se hai `regime_confidence` in tabella, un piccolo badge colorato (alta/media/bassa confidenza) sulla riga rende visibile a colpo d'occhio i casi limite, proprio quelli da rivedere a mano.

---

## 2. Short selling / margin trading

Il piano a 4 fasi che avevi già delineato resta valido. Qui aggiungo le implicazioni su saldo/margine che vanno tenute a mente fin dalla Fase 1, anche se l'implementazione vera arriva dopo.

### 2.1 Le 4 fasi (riepilogo)
1. `margin_short.py` isolato, solo testnet, con `AUTO_BORROW_REPAY`
2. `SignalAggregator` consapevole di `entry_side` (LONG/SHORT)
3. Logica OCO speculare per gli short (attenzione: SL sopra l'entry, TP sotto — è invertito rispetto al long)
4. Risk Controls + `StrategySelector` aggiornati per la leva

### 2.2 Cosa cambia sul saldo (da considerare già in Fase 1)

Lo short su margin introduce concetti che lo spot non ha:
- **Margin level** (asset totali / passività totali): va monitorato e va definita una soglia di sicurezza (es. restare sopra 2.0) ben distante dalla soglia di liquidazione di Binance.
- **Interesse sul prestito**: accrual orario sull'asset preso in prestito — va trattato come un costo nel calcolo del PnL reale, non solo fee di trading.
- **Posizionamento dei fondi**: i fondi devono stare nel margin wallet, non in spot/funding. Questo significa che il `WalletOrchestrator` deve saper fare il trasferimento Spot → Margin (e viceversa) *prima* che la Fase 1 possa anche solo essere testata con soldi veri — anche se in Fase 1 si lavora solo su testnet, è bene progettare già l'interfaccia di trasferimento.

### 2.3 Criteri per passare da testnet a mainnet (size minima)

Prima di passare anche solo a size piccole su mainnet, propongo una checklist minima:
- N operazioni testnet senza errori di borrow/repay
- Margin level monitorato e mai sceso sotto soglia di sicurezza in nessun test
- OCO short testato sia su TP che su SL (non solo lo scenario "felice")
- `WalletOrchestrator` capace di muovere fondi Margin → Spot in caso di emergenza/stop manuale

### 2.4 Impatti su moduli esistenti
- `StrategySelector`: deve sapere non solo "quale strategia" ma anche "in che direzione" — un regime trending-down oggi probabilmente non genera nessun segnale attuabile, con lo short diventa un'opportunità.
- Risk Controls: la leva introduce un nuovo asse di rischio che il sizing attuale (pensato per spot) non gestisce.

---

## 3. Audit della Risk Control card

Qui devo essere onesto: non ho visibilità diretta sul codice/comportamento attuale della card, quindi sotto trovi una griglia di domande da verificare tu stesso (o da incollarmi insieme a screenshot/codice se vuoi che la analizzi nel dettaglio), più un gap concreto che già sappiamo esistere.

### 3.1 Domande chiave per l'audit

| Domanda | Perché conta |
|---|---|
| È solo **display** o **enforcement reale**? | Una card che mostra limiti ma non li applica è solo dashboard, non risk control |
| Quali soglie applica oggi? (size massima, drawdown giornaliero, perdite consecutive...) | Senza un elenco esplicito non si può dire se è "completa" |
| Il trader (il motore, non tu) **legge** questi limiti prima di apriore un ordine, o sono calcolati a posteriori? | Determina se è preventivo o solo di reporting |
| Viene loggato **quando** un trade viene bloccato da un limite? | Senza log di blocco, non puoi sapere se la card sta facendo qualcosa o è morta |
| È aggiornata in real-time o a intervalli (polling)? | Rilevante se in futuro deve reagire velocemente a una sequenza di stop-loss |

### 3.2 Gap già noto e concreto

Sappiamo già che **non esiste un cooldown dopo perdite consecutive** — nuovi trade si aprono entro ~1 minuto da uno stop-loss. Questo è di fatto un buco nella Risk Control attuale, a prescindere dalla risposta alle domande sopra: è un caso in cui la card *dovrebbe* bloccare/ritardare e non lo fa.

Proposta minima (one change at a time):
1. Aggiungere un campo `cooldown_until` calcolato da `consecutive_loss_count` (già previsto nello schema log al punto 1.2).
2. Il motore controlla `cooldown_until` prima di aprire un nuovo trade — singolo punto di enforcement, facile da testare in isolamento.
3. Solo dopo, eventualmente, esporre il countdown del cooldown in UI.

### 3.3 Altri miglioramenti possibili (da prioritizzare dopo l'audit)
- Limite di drawdown giornaliero con stop automatico della sessione
- Position sizing dinamico in funzione della volatilità recente, non solo size fissa
- Quando arriva lo short: integrazione con il margin level come ulteriore vincolo di Risk Control

### 3.4 Lato Angular: rendere la card "viva" e trasparente

Visto che è la tua area: la card di Risk Control guadagnerebbe molto a mostrare non solo i numeri statici ma **lo stato delle regole attive in tempo reale** — es. "Cooldown attivo: prossimo trade abilitato alle 14:32", "Limite drawdown giornaliero: 60% utilizzato". Questo la trasforma da pannello informativo a strumento di debug operativo, ed è anche il modo più rapido per *te* per verificare empiricamente se l'enforcement funziona davvero (domanda 3.1).

---

## Prossimi passi suggeriti (in ordine, one-change-at-a-time)

1. Fix sync bug strategy_selected/executed (prerequisito per tutto il punto 1)
2. Implementare `cooldown_until` nel motore (gap concreto, basso rischio, alto valore)
3. Schema `session_trade_log` aggiornato con `regime_confidence` e `signal_breakdown`
4. Job di riflessione periodica del Supervisor (dopo aver verificato che i dati in ingresso sono puliti)
5. `margin_short.py` su testnet, isolato
6. Audit puntuale della Risk Control card con dati reali (condividimi log/screenshot quando vuoi scendere nel dettaglio)

---

*Nota: per i punti 1 e 3 questo documento è un'analisi architetturale basata su quanto già sappiamo del progetto. Se mi condividi i log di sessione reali o il codice attuale della Risk Control card, posso raffinare le proposte con osservazioni puntuali invece che generiche.*
