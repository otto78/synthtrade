# ANALISI — Il bot non ha un edge; le fee mangiano tutto

> **Versione 2 — 2026-09-30.** Riscritta dopo l'analisi di Claude sulla v1.
> Tutte le cifre sono **rimisurate sul DB di produzione** (197 trade chiusi, 2026-07-24 → 2026-09-30).
> Le inferenze sono marcate. L'inferenza è marcata come tale anche quando è mia.
> Query di riproduzione: §10.

---

## 0. Cosa cambia rispetto alla v1 — due errori miei

La v1 conteneva due affermazioni che **non reggono**. Le correggo qui esplicitamente.

### 0.1 ❌ Errore mio: `pnl_pct` non è corrotta

La v1 riportava «valori da −106% a +125%, colonna corrotta, va sanata prima di ogni analisi».

**Era un mio errore di calcolo, non un difetto dei dati.** Avevo stampato `mean(pnl_pct) * 100`, cioè moltiplicato per 100 un campo che è già in percentuale. Il risultato (−22.99% medio, −106% min, +125% max) era il doppio dei valori veri.

Verifica sul codice (`trade_executor.py:280`): `pnl_pct = (pnl / (entry_f * qty_f)) * 100` — corretta. Ricalcolata su tutti i trade, errore max **0.20 punti** (arrotondamento a 2 decimali).

```
pnl_pct reale:  min -1.060%   max +1.250%   media -0.230%
```

Valori perfettamente normali. **Nessuna anomalia, nessun lavoro di sanatoria necessario.** La voce "pulizia dei dati" della v1 (che la elencava come anomalia #1, ora ritirata in §7) era infondata su questo punto.

### 0.2 ⚠️ Claude ha ragione: lo score non è mai stato il gate

La v1 concludeva «lo score non predice il P&L (r = +0.0098)». **Questa inferenza non era sostenuta**, perché non ho verificato come i trade entrassero effettivamente.

Verifica sul campo `strategy_rejection_reason` (popolato su 197/197 trade):

```
178 trade  "MEAN-REVERSION BUY permesso (source=rsi_bollinger(atr=0.04%)) nonostante bias=..."
 12 trade  "intelligence=N (bullish) [trend=N diverging] + tecnico=BUY@N"
  7 trade  altri (live_mode fallback, trend converging/stable)
```

| | n | score medio | score > +6.0 | win rate | P&L tot |
|---|---|---|---|---|---|
| **mean-revision** | **178 (90%)** | **−9.37** | **0** | 33.1% | −7.930 |
| altri ingressi | 19 (10%) | — | 13 | 21.1% | −1.030 |

**Il 90% dei trade entra da un override mean-reversion esplicitamente permesso "nonostante bias" negativo. Di quei 178, ZERO ha score > +6.0.**

La soglia `+6.0` non ha mai autorizzato un trade. Il gate reale è l'override mean-reversion di `rsi_bollinger`, che scavalca l'intelligence.

Quindi la correlazione score↔PnL che ho misurato descrive **una variabile che non ha avuto un ruolo causale nel 90% dei campioni**. Non dimostra che lo score sia inutile: dimostra che **non esiste un test valido su questi dati**. La v1 confondeva misurazione e causalità.

*Nota di metodo:* Claude indica `strategies_considered` come campo da interrogare, ma quel campo è vuoto su tutti i trade. Il campo popolato è `strategy_rejection_reason`. La sostanza della critica è corretta, il campo indicato no.

---

## 1. TL;DR

1. **Il bot è quasi a zero lordo e perde solo di fee.** Su 197 trade: P&L netto **−8.96 €**, di cui **+7.32 €** di commissioni. Il **lordo è −1.12 €** (stima che include i 14 trade senza commissione registrata) cioè **−0.006 €/trade**. Non ha un edge negativo: ha **edge ≈ zero e paga 0.186% a ogni round trip**.

2. **Le fee sono 4.5× più grandi dell'edge lordo.** Netto −0.227% per trade, fee +0.186%, lordo −0.042%. Anche un edge lordo leggermente positivo verrebbe annullato dai costi.

3. **Il 62% dei trade muore a stop loss** (121/197). Su SL 0.5% / TP 0.8% un random walk darebbe ≈ 0.8/(0.5+0.8) = **62%**. Coincidenza suggestiva, **non è una prova** — i trailing/break-even rendono il modello di "primo tocco" non applicabile.

4. **`take_profit` scatta 4 volte su 197 (2%).** L'82% del P&L positivo viene da trailing stop e break-even, non dal TP. Il take profit è di fatto uno strumento inutilizzato.

5. **Lo score non è il gate** (§0.2). Qualsiasi lavoro su score, pesi, soglie o supervisor non tocca la causa della perdita.

**Conseguenza operativa:** la leva non è "selezionare meglio i trade", è **ridurre il costo per trade o aumentare il movimento catturato per trade**. Frequenza, timeframe, e costo di esecuzione. Non intelligenza.

---

## 2. I numeri, per intero

### 2.1 Lordo vs netto

```
pnl netto (DB, già dopo fee)      =  -8.960 EUR
fee osservate (183/197 trade)    =  +7.318 EUR    media 0.0371
fee stimate sui 14 mancanti      =  +0.519 EUR
─────────────────────────────────────────────────────
LORDO osservato                  =  -1.642 EUR
LORDO con stima completa         =  -1.122 EUR   <- bound superiore
```

Per trade, su notional 20 EUR:

| | €/trade | % del notional |
|---|---|---|
| netto | −0.0455 | −0.227% |
| fee | +0.0371 | +0.186% |
| **lordo** | **−0.0083** | **−0.042%** |

**Il rapporto fee/edge lordo è 4.5×.** Questo è il numero che riorganizza l'intero problema: il bot non sbaglia le entrate in modo sistematico, non genera abbastanza movimento favorevole da coprire il costo di esistere come trade.

### 2.2 Perché `pnl` è netto — verifica

`trade_executor.py:279` e `:383`: `pnl = gross_pnl - total_fees`. Il campo `pnl` nel DB **è già al netto delle commissioni**. Quindi il lordo si ottiene *sommando* le commissioni, non sottraendole.

*Nota:* l'analisi di Claude presenta "P&L −8.59 € di cui −6.96 € di fee → senza fee −0.79 €" su 188 trade tratti da HANDOFF. I miei numeri su 197 trade dal DB sono −8.96 / +7.32 / **−1.12**. La **conclusione è identica** (lordo ≈ zero, fee dominanti); i valori differiscono per il campione e per il fatto che 14 trade non hanno commissione registrata, che ho stimato invece di ignorare. Il mio lordo è il caso peggiore: se le fee fossero tutte registrate, il lordo sarebbe −1.64 €.

### 2.3 Motivi di uscita

| Motivo | n | % | win rate | P&L tot | P&L medio | % notional |
|---|---|---|---|---|---|---|
| `stop_loss` | **121** | 61.4% | 0.0% | **−11.950** | −0.0988 | −0.494% |
| `stop_loss_breakeven` | 36 | 18.3% | 75.0% | +0.870 | +0.0242 | +0.121% |
| `stop_loss_trailing` | 29 | 14.7% | 100% | +1.560 | +0.0538 | +0.269% |
| `take_profit` | **4** | **2.0%** | 100% | +0.490 | +0.1225 | +0.613% |
| `external_close` | 5 | 2.5% | 40.0% | −0.080 | −0.0160 | −0.080% |
| `session_stop` | 1 | 0.5% | 100% | +0.210 | +0.2100 | +1.050% |

Il P&L lordo positivo dei vincitori (1.560 + 0.870 + 0.490 + 0.210 = **+3.13 €**) è eroso da −11.95 € di stop loss. Le fee (−7.32 €) sono il secondo buco.

### 2.4 R:R

```
vincite: n=63   medio +0.0548 EUR   (+0.27% notional)
perdite: n=133  medio -0.0929 EUR   (-0.46% notional)
R:R reale = 0.59 : 1
win rate per pareggio (config attuale) = 62.9%
win rate reale = 31.8%
```

*Correzione rispetto alla v1:* presentavo il 62.9% come «servirebbe quasi il doppio, non è un edge». Claude ha ragione nel dire che è **descrittivo della configurazione di uscita attuale**, non una legge di natura: quegli avg win/avg loss sono a loro volta prodotti da trailing e break-even che chiudono i vincitori prima del TP. Riformulato: **non è il numero di trade a vincere che va corretto, è il fatto che i vincitori vengono chiusi a +0.27% mentre i perdenti a −0.46%.**

### 2.5 Nessun miglioramento temporale

| Mese | n | win rate | P&L tot | €/trade |
|---|---|---|---|---|
| 2026-07 | 25 | 20.0% | −1.420 | −0.0568 |
| 2026-08 | 91 | 39.6% | −3.510 | −0.0386 |
| 2026-09 | 80 | 27.5% | −3.970 | −0.0496 |

### 2.6 Cosa vedeva il supervisor

`signal_outcome_by_strategy_regime` (fonte di `historical_context.py:54`):

| Strategia | Regime | n | win rate | €/trade | P&L tot |
|---|---|---|---|---|---|
| rsi_bollinger | ranging | 184 | 35.3% | −0.0475 | −8.74 |
| ema_cross | ranging | 5 | 40.0% | −0.0300 | −0.15 |
| rsi_bollinger | altro | 5 | 60.0% | −0.0340 | −0.17 |
| ema_cross | altro | 2 | 100% | +0.0800 | +0.16 |

Ogni combinazione con campione significativo è negativa. Il supervisor conclude `no_action`: **è la diagnosi corretta.** Non va ritoccato.

---

## 3. Perché la v1 era sbagliata nel metodo

Sette task (1250 → 1262) hanno agito su **selezione**: filtro trend, guardie, soglie, pesi dello score, fee-awareness del supervisor. Tutte modificano *quali* trade si fanno. Nessuna modifica *cosa succede dopo l'ingresso* o *quanto si paga per farlo*.

E i dati mostrano che la selezione non era nemmeno il collo di bottiglia: il 90% degli ingressi è un override che la bypassa (§0.2). Quindi sette interventi hanno agito su una leva che (a) non era il problema e (b) non era nemmeno attiva.

**La leva giusta è economica:** costo per trade, frequenza, e movimento catturato per trade.

---

## 4. Il piano

### Fase 0 — Decisione operativa

L'opzione "calibrare lo score" è **scartata**: i dati mostrano che lo score non è il gate (§0.2), quindi calibrarlo non cambia quali trade si fanno.

| Opzione | Costo | Informazione |
|---|---|---|
| **A. Sospendere il live, misurare offline** | 0 € di rischio | Alta — backtest e simulazioni sono gratuiti |
| **B. Tenere il live a stake ridotto** | ~0.037 €/trade | Bassa — i dati post-fix del CVD sono 3 giorni, non sufficienti |

**Raccomandazione: A.** Con edge lordo −0.006 €/trade e fee 4.5× più grandi, ogni trade perso dal vivo è denaro perso per imparare qualcosa che si può imparare gratis su storico.

### 4.1 Random-entry test — il test decisivo

Su storico OKX BTC-EUR 1m, con le **stesse regole di uscita reali** (SL, TP, break-even, trailing, fee 0.1%/0.1%) e **entrate casuali** alla stessa frequenza del bot, migliaia di ripetizioni.

- **Il bot cade dentro la distribuzione** → le entrate non portano informazione. Nessun lavoro su score/collector/supervisor cambierà l'esito. Si passa alle leve strutturali di §4.3.
- **Il bot è chiaramente sopra** → esiste un segnale, e solo allora vale la pena calibrarlo, con la certezza di cosa si ottimizza.

`BacktestEngine` (TASK-808) è riusabile: serve un generatore di segnali casuali al posto della strategia.

**Nota:** dato §0.2, questo test è ancora più necessario di quanto sembrasse. Non sappiamo nemmeno se il gate dello score, se attivo, produrrebbe trade diversi da quelli attuali.

### 4.2 Benchmark

- **Buy & hold** BTC-EUR sullo stesso periodo e capitale.
- **Expectancy lorda** di `rsi_bollinger` su 1 anno, walk-forward.
- Soglia di sensatezza: l'edge lordo per trade deve superare **2× le fee** (≈ 0.4%) con margine per la varianza. Sotto, non è un timeframe praticabile.

### 4.3 Se il test conferma assenza di edge

Il problema è strutturale: fee 0.186% per round trip contro uno stop netto di 0.3%. In ordine di impatto atteso:

1. **Timeframe più lungo (15m / 1h / 4h).** Il movimento tipico diventa 10–20× le fee invece di 2–3×. Miglior rapporto costo/beneficio.
2. **Ridurre la frequenza per costruzione, non filtrando con lo score.** Un setup al giorno, solo breakout confermati. Meno trade → fee incidono meno.
3. **Verificare maker vs taker sul tier effettivo.** Solo se c'è un differenziale reale: sull'account attuale taker e maker sembrano entrambi 0.10%, quindi il vantaggio sarebbe zero.
4. **Rivedere il take profit.** 2% di hit rate significa che il movimento dopo l'ingresso è tipicamente più piccolo del TP nominale. O il TP è irraggiungibile, o la finestra di holding è troppo corta. Da chiarire *prima* di ricalibrare: è un problema di posizionamento, non di selezione.

### 4.4 Se il test mostra un segnale

Solo allora: ricalibrare soglia e pesi **su dati post-2026-09-29**, rimisurare la correlazione score→PnL su un campione in cui lo score ha effettivamente filtrato, e aumentare lo stake **solo** con expectancy netta positiva e statisticamente distinguibile da zero.

---

## 5. Criteri di successo

Da fissare **prima** di iniziare, per non ripetere sette task senza un metro comune.

| Metrica | Oggi | Soglia per considerare valida un'ipotesi |
|---|---|---|
| Expectancy **lorda** per trade | −0.0083 € | > 2× le fee (≈ +0.037 €) |
| Expectancy **netta** per trade | −0.0455 € | > 0, con CI che esclude lo zero |
| Posizione nel random-entry test | non misurata | sopra il 95° percentile |
| P&L netto vs buy & hold | non misurato | superiore, stesso periodo e capitale |
| Campione per la conclusione | — | 200–300 trade (varianza attuale) |

Nessuna di queste soglie è una previsione. Sono i criteri con cui decidere, *prima* di vedere i risultati.

---

## 6. Cose da non fare

- **Non abbassare la soglia dello score**: non è il gate (§0.2), e i trade a score medio-alto non rendono meglio.
- **Non aumentare lo stake**: scala il risultato di qualunque segno. Con edge ≈ zero, raddoppiare lo stake raddoppia la perdita.
- **Non aggiungere collector, pesi o logica al supervisor** prima del random-entry test.
- **Non modificare il supervisor**: dice `no_action` correttamente.
- **Non usare `pnl_pct` come se fosse corrotto** — è integro (§0.1). Usare `pnl` in assoluto per i calcoli di margine.
- **Non confrontare score storici pre-2026-09-29** col post-fix (bug CVD `+15`).

## 7. Anomalie residue (riviste)

| # | Anomalia | Stato |
|---|---|---|
| ~~6.1~~ `pnl_pct` corrotta | **Ritirata** — era un mio errore di calcolo (§0.1) | ✅ risolta, nessun lavoro |
| 6.2 Soglia 6.0 (DB) vs 15.0 (env) | Vera, innocua: vince il DB. Config morta da rimuovere per non confondere | aperta, bassa priorità |
| 6.3 Score pre-29/09 invalidato dal bug CVD +15 | Vera | aperta, dichiarata |
| 6.4 Peso morto nei collector (`whale`≈0, `open_interest`≈0, `sentiment`/`spread` a 0) | Vera, `COVERAGE total=0.88` | aperta, documentale |
| 6.5 Trade value 10 (config) vs 20 (effettivo) | **Ridimensionata**: i 20 € non sono un'anomalia, sono coerenti e sensati per l'arrotondamento. È la config a essere non allineata. Allineare a 20. | aperta, bassa |

---

## 8. Domande aperte per la prossima analisi

1. **Quanto si muove BTC-EUR in 0.7% (0.5% SL + 0.2% fee) nella direzione prevista, entro la finestra di holding?** Non mai misurato. È la domanda che decide se il timeframe giusto è 1m o no.
2. **Perché `take_profit` scatta nel 2% dei casi?** TP irraggiungibile, finestra troppo corta, o OCO non attivo? Potenzialmente più importante di tutto il resto.
3. **I trailing e break-even chiudono i vincitori a +0.27% quando il TP è a +0.6%.** È un difetto di configurazione o il mercato non arriva? Se è difetto, il R:R reale si può correggere da solo.
4. **Il random-entry test va fatto con quali parametri esatti?** Servono i valori vivi di SL/TP/trailing per strategia, non quelli documentati (che divergono).

## 9. Stato del documento

- **Diagnosi:** completa e verificata sui dati. Due errori della v1 corretti in §0.
- **Piano:** §4, in attesa della decisione di Fase 0 (A o B).
- **Prossimo passo:** scrivere lo script del random-entry test riusando `BacktestEngine`, dopo aver deciso A o B.

## 10. Riproduzione

Da dentro il container di produzione:

```python
from supabase import create_client
u = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
cl = [t for t in u.table("scalping_trades").select("*").execute().data if t["status"] == "closed"]

# §2.1 lordo vs netto   -> sum(pnl), sum(entry_commission + exit_commission)
# §0.2 bypass del gate  -> colonna strategy_rejection_reason (popolata su 197/197)
# §2.3 motivi di uscita  -> colonna signal_reason
# §2.6 vista supervisor -> u.table("signal_outcome_by_strategy_regime").select("*")
# §0.1 verifica pnl_pct -> ricalcolare pnl/(quantity*entry_price)*100 e confrontare
```

Calcolo lordo: `pnl` è già netto (`trade_executor.py:279`). Il lordo è `pnl + commissioni`.
14 trade su 197 non hanno commissione registrata: le loro fee (0.0371 €) sono **stimate**, non misurate.

*Stato LIVE al momento della stesura: sessione `running/live`, 1 posizione aperta.*
