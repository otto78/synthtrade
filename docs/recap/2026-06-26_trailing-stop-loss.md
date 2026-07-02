# SynthTrade — Recap Sessione: Strategia Trailing Stop Loss (Growth Strategy a SL Variabile)

**Data:** 26 giugno 2026
**Contesto:** sessione di sola analisi/proposta architetturale, nessun codice scritto né applicato al progetto reale.

---

## 1. Punti toccati in questa sessione

| # | Argomento | Stato |
|---|---|---|
| 1 | Idea: nuova strategia di "crescita" con solo Stop Loss (no Take Profit), SL che si alza progressivamente col prezzo | 🟢 Validata concettualmente, mappata su pattern noto |
| 2 | Ricerca di strategie esistenti analoghe da cui prendere spunto | 🟢 Risposto con 4 varianti consolidate |
| 3 | Integrazione architetturale nel modello SynthTrade esistente (SignalAggregator, AI Supervisor) | 🟢 Proposta di schema, non implementata |
| 4 | Compatibilità con la natura intraday delle altre strategie di scalping | 🟢 Chiarita: stessa entry gate, exit logic separata |

---

## 2. Richiesta iniziale dell'utente

Aggiungere al modulo di scalping (che oggi usa diverse strategie con OCO gestiti dal Supervisor AI) una nuova **strategia di crescita** con queste caratteristiche:
- Solo Stop Loss, **nessun Take Profit** — l'obiettivo è restare in posizione il più a lungo possibile
- Dopo l'acquisto iniziale si piazza uno SL
- Se il prezzo sale sopra il prezzo di acquisto, lo SL si alza di conseguenza (mai scende)
- Non si esce mai "di proposito": si lascia correre il trend, proteggendo solo i guadagni acquisiti
- Lo SL variabile dovrebbe essere **regolato periodicamente dal Supervisor AI**, in coerenza con la natura intraday/dinamica già presente nelle altre strategie

---

## 3. Risposta — Pattern identificato: Trailing Stop Loss (TSL)

Confermato che la richiesta corrisponde esattamente a una **Trailing Stop Loss Strategy**, tecnica consolidata nel trading sistematico. Presentate 4 varianti esistenti come riferimento:

| Variante | Logica | Note |
|---|---|---|
| **Percentage Trailing Stop** | SL = prezzo massimo − % fissa | Più semplice, non si adatta alla volatilità |
| **ATR Trailing Stop** (Chandelier Exit) | SL = prezzo massimo − (N × ATR) | La più usata nei sistemi automatici; N è il parametro ottimizzabile dall'AI Supervisor |
| **Parabolic SAR** | Punti SAR che accelerano col proseguire del trend | Più aggressivo, esce prima, cattura meno trend |
| **Swing Low Trailing Stop** | SL ancorato al minimo degli ultimi N candle | Più "organico", basato su struttura di mercato |

**Raccomandazione data:** ATR Trailing Stop (Chandelier Exit) come punto di partenza, perché il moltiplicatore ATR è naturalmente il parametro che il Supervisor AI può tarare dinamicamente (esattamente come già fa con altri parametri di strategia).

---

## 4. Proposta di integrazione architetturale in SynthTrade

Separazione concettuale proposta tra **entry** ed **exit**:

```
Entry → gestita dal SignalAggregator come le altre strategie (stesso gate Intelligence Score + segnale tecnico)
Exit  → NON un take profit fisso, ma un trailing stop ricalcolato periodicamente
```

Proposto come nuovo tipo di strategia, distinto dalle 4 esistenti:

- **`StrategyType.TREND_FOLLOW_TSL`** (nome di lavoro)
- **Entry**: stesso gate del `SignalAggregator` (Intelligence Score + filtro tecnico)
- **Exit**: loop periodico separato (schedulato via APScheduler, frequenza da decidere) che ricalcola e aggiorna lo SL via API Binance
- **Parametri AI-driven**: moltiplicatore ATR, periodo ATR, frequenza di rivalutazione dello SL

Snippet pseudocodice condiviso a titolo illustrativo (logica di aggiornamento SL guidata dal Supervisor, vincolo "SL può solo salire, mai scendere").

---

## 5. Punti rimasti aperti / non affrontati in questa sessione

- Nessuna decisione presa su **dove collocare nel codice** la nuova strategia (struttura file in `strategies/`, integrazione in `StrategySelector`/`registry.py`)
- Nessuna decisione su **frequenza di rivalutazione** del trailing stop (ogni candle? ogni N minuti? agganciato al ciclo del Supervisor a 5-15 min?)
- Non discusso il comportamento in caso di **regime change** (es. cosa succede al TSL se il Supervisor rileva un'inversione netta — uscita forzata anticipata vs lasciare lavorare solo il trailing?)
- Non discusso se questa strategia debba **competere** con le altre 4 per la selezione del regime, o essere **complementare** (es. attivabile solo manualmente o solo in regime `TRENDING_UP` forte)
- Non affrontata l'interazione con il **Risk Manager** esistente (max daily loss, consecutive losses) dato che questa strategia per design non ha mai un take profit che "chiude" il ciclo nel modo classico
- Non affrontato il collegamento con il lavoro già in roadmap su **Short Selling** (la stessa logica TSL, mirrorata, sarebbe naturale anche per posizioni short una volta implementate)

---

## 6. Proposta in sospeso a fine sessione

Offerto (non ancora richiesto/elaborato) uno schema architetturale completo della strategia integrata nell'architettura v2.0 di SynthTrade — in attesa di conferma dell'utente per procedere.

---

## 7. File prodotti in questa sessione

1. Questo recap
