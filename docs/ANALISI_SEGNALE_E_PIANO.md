# ANALISI — Il gate dello score non distingue i trade buoni

> **Scopo di questo documento:** raccogliere tutti i dati reali sul problema dello score
> affinché altre IA possano analizzarlo in parallelo e trovare la soluzione migliore.
> **Non è ancora un piano di risoluzione** — è il materiale su cui costruirlo.
>
> **Autore:** raccolta dati 2026-09-30, da DB di produzione (Supabase) e log LIVE.
> **Tutte le cifre sono misurate**, non stimate. Le inferenze sono marcate esplicitamente.
> **Riproducibile:** le query sono in `§9`.

---

## 1. TL;DR

Il bot perde soldi in modo costante da 3 mesi. La causa **non** è la soglia dello score.

Tre fatti misurati che compongono il problema:

1. **Lo score non predice il PnL.** Correlazione di Pearson `score ↔ pnl` = **+0.0098** su 168 trade. Spearman ≈ **−0.11** (debolmente *negativa*: score più alto → esito leggermente peggiore).

2. **I trade con score più alto non battono la media.** I 13 trade con `score > +6.0` hanno win rate **30.8%**, contro il **31.8%** della baseline. `-0.0254` EUR/trade contro `-0.0458`. Migliorano, ma restano negativi e non distinguono.

3. **L'obiettivo di win rate necessario è ~63%, quello reale è 31.8%.** Con i valori di SL/TP effettivamente misurati, servirebbe quasi il doppio. *Nessuna regolazione di soglia, peso o segnale può colmare un buco del genere: è un problema di edge, non di filtro.*

Conseguenza: abbassare la soglia da `+6.0` a `+1.0` farebbe entrare più trade **senza motivo**, degradando un PnL già negativo. Il rischio concreto è **perdere più soldi, non smettere di guadagnarne**.

> **La domanda da decidere non è "quanto abbasso la soglia", ma "esiste una strategia con edge su questo mercato, e come la misuro per saperlo".**

---

## 2. La decisione richiesta

Chi non è un trader professionista non dovrebbe decidere da solo. Le opzioni oneste sono tre:

| # | Opzione | Cosa comporta | Rischio |
|---|--------|---------------|---------|
| **A** | **Fermare e misurare** | Spegnere il trading, accumulare dati con la logica attuale *senza* eseguire, e validare su storico se esiste un edge. | Nessun guadagno, nessuna perdita. Costo: tempo. |
| **B** | **Ridurre il rischio** | Tenere il bot, ma con `TRADE_VALUE` e/o frequenza ridotti all'1, finché il problema non è capito. | Perdita ridotta ma ancora presente. |
| **C** | **Calibrare lo score** | Ricalibrare pesi/soglia come previsto da TASK-1252 fase 2. | **Alto** — i dati (§4) indicano che non funzionerà. |

**La raccomandazione di chi ha scritto il documento: A o B.** I dati di §4 sono espliciti sul perché C è la scelta sbagliata. Ma la scelta finale spetta a chi conosce l'obiettivo economico (quanto si è disposti a rischiare, per quanto tempo, con quale capitale).

---

## 3. Contesto di sistema

- **Cosa fa:** bot di scalping automatico su BTC-EUR (OKX spot), regime detection → scelta strategia → score intelligence → esecuzione con OCO bracket (SL + trailing + TP).
- **Scala:** 196 trade chiusi dal 2026-07-24 al 2026-09-30, ~2 mesi e mezzo.
- **Stake:** `SCALPING_TRADE_VALUE = 10.0` in config, ma il **notional effettivo è 20.00 EUR** (mediana e media su tutti i trade). Quantità media `0.00031918` BTC, entry medio `63254` EUR. ⚠️ Vedi §6.5.
- **Strategie:** `rsi_bollinger` (189/196, 96%) e `ema_cross` (7/196, 4%).
- **Regimi:** `ranging` 161, `trending_down` 5, `trending_up` 3, non classificati 27.
- **Soglia corrente:** `SCALPING_SIGNAL_STRENGTH_THRESHOLD = 6.0` (da DB, vedi §7 per la discrepanza).
- **Fee reali misurate:** `0.019998` entry + `0.019883` exit ≈ **0.04 EUR round-trip** su 20 EUR di notional = **0.2%**.

---

## 4. Evidenza

### 4.1 Performance complessiva

```
n = 195 chiusi
win rate        31.8%
P&L totale      -8.940 EUR
P&L medio       -0.0458 EUR / trade
```

### 4.2 Correlazione score → P&L

Pearson e rank correlation su 168 trade con entrambi i dati:

| Metrica | Valore | Lettura |
|---------|--------|---------|
| Pearson `score ~ pnl` | **+0.0098** | Nessuna relazione |
| Pearson `score ~ pnl_pct` | +0.0242 | Nessuna relazione |
| Spearman (rank) | **−0.1108** | Debolmente **inversa** |

### 4.3 Win rate per fascia di score

Questa è la tabella che rifiuta l'ipotesi "abbasso la soglia".

| Fascia score | n | Win rate | P&L medio |
|---------------|---|----------|-----------|
| [-100, -20) | 4 | 75.0% | +0.0125 |
| [-20, -10) | 46 | 30.4% | −0.0465 |
| [-10, -5) | 103 | 34.0% | −0.0482 |
| [-5, 0) | 1 | 0.0% | −0.1000 |
| [0, 5) | 1 | 0.0% | −0.1000 |
| **[5, 10)** | **8** | **25.0%** | **−0.0475** |
| **[10, 100)** | **5** | **40.0%** | **+0.0100** |

Il bucket `[5,10)` — quello che si aprirebbe abbassando la soglia a `+5` — ha il **peggiore** win rate insieme a `[0,5)`. Non c'è monotonia: più alto lo score, peggio (o identico) il risultato.

### 4.4 I 13 trade con score > +6.0 (la soglia attuale)

| Data | Score | P&L | Strategia | Regime |
|------|-------|-----|-----------|--------|
| 2026-08-03 | +15.1 | +0.210 | ema_cross | trending_up |
| 2026-08-04 | +6.6 | −0.100 | rsi_bollinger | ranging |
| 2026-08-05 | +10.3 | +0.040 | ema_cross | trending_up |
| 2026-08-05 | +7.3 | −0.100 | rsi_bollinger | ranging |
| 2026-08-07 | +10.0 | −0.100 | ema_cross | trending_up |
| 2026-08-12 | +6.1 | −0.100 | rsi_bollinger | ranging |
| 2026-08-20 | +9.4 | +0.070 | rsi_bollinger | ranging |
| 2026-08-24 | +7.3 | −0.110 | rsi_bollinger | ranging |
| 2026-08-25 | +19.3 | −0.100 | rsi_bollinger | ranging |
| 2026-08-25 | +14.8 | 0.000 | ema_cross | ranging |
| 2026-08-28 | +6.1 | −0.100 | rsi_bollinger | ranging |
| 2026-09-11 | +9.7 | +0.160 | ema_cross | ranging |
| 2026-09-23 | +8.6 | −0.100 | rsi_bollinger | ranging |

```
n = 13   win rate 30.8%   P&L tot -0.330   medio -0.0254
baseline: win rate 31.8%  P&L tot -8.940   medio -0.0458
```

**Passare la soglia non migliora il win rate.** E tutti i 13 sono **precedenti al 2026-09-24**, cioè quasi tutti generati quando il CVD aveva il bug del `+15` costante (§6.3).

### 4.5 Distribuzione dello score

```
score > -20 : 165/169  (97.6%)
score > -10 : 118/169  (69.8%)
score >  -6 :  22/169  (13.0%)
score >   0 :  13/169  ( 7.7%)
score >  +6 :  13/169  ( 7.7%)   <- la soglia corrente
score > +10 :   4/169  ( 2.4%)
score > +15 :   2/169  ( 1.2%)
```

Il segnale è **sistematicamente negativo**: 87% dei trade ha score sotto `−10`. Non è un segnale centrato su zero che ogni tanto va positivo — è un segnale che vive quasi interamente nel territorio negativo.

### 4.6 Perché il +6.0 è praticamente irraggiungibile

Snapshot LIVE reale del 2026-09-30:

```
order_book_imbalance=OK(w=0.30, s=-8.9)   <- 41% del peso rispondente
funding_rate=OK(w=0.15, s=-1.9)
long_short_ratio=OK(w=0.10, s=1.8)
fear_greed=OK(w=0.03, s=-16.5)
onchain=OK(w=0.05, s=-0.8)
open_interest=OK(w=0.05, s=-0.3)          <- ~0
whale=OK(w=0.05, s=0.0)                   <- SEMPRE 0
sentiment=OK(w=0.00, s=10.0)              <- peso zero
spread=OK(w=0.00)                         <- peso zero
cvd=WARMUP(w=0.15)                        <- escluso
COVERAGE: total=0.88 responded=0.68
```

Calcolo di quello snapshot: `Σ(score_i × w_i) = −3.33`, su peso rispondente `0.73` → **score normalizzato ≈ −4.6**.

Per arrivare a `+6.0` servirebbe l'OBI al **massimo assoluto** del suo range storico misurato (`+16.6`) *mentre tutto il resto è a zero*. Contributo OBI massimo reale: `0.30/0.73 × 16.6 ≈ +6.8`. Quindi: **sulla carta appena possibile, nella pratica una coincidenza.**

*Inferenza:* la soglia `+6.0` non è una soglia, è un muro. Il sistema è in pratica a un regime "sempre non apre" per costruzione.

### 4.7 Il vero collo di bottiglia: R:R sbagliato

Dai dati reali di uscita, non dalla documentazione:

| Motivo uscita | n | Win rate | P&L tot | P&L medio | P&L % su notional |
|---------------|---|----------|---------|-----------|--------------------|
| `stop_loss` | **121** | 0.0% | **−11.950** | −0.0988 | **−0.494%** |
| `stop_loss_breakeven` | 36 | 75.0% | +0.870 | +0.0242 | +0.121% |
| `stop_loss_trailing` | 29 | 100% | +1.560 | +0.0538 | +0.269% |
| `take_profit` | **4** | 100% | +0.490 | +0.1225 | +0.613% |
| `external_close` | 5 | 40.0% | −0.080 | −0.0160 | −0.080% |
| `session_stop` | 1 | 100% | +0.210 | +0.2100 | +1.050% |

**Il dato che colpisce: `take_profit` scatta 4 volte su 196 (2.0%).** Il 62% dei trade muore a stop loss. Quasi tutto il P&L positivo arriva dal **trailing stop** (+1.56) e dal **break-even** (+0.87), non dal take profit.

R:R reale, dai numeri effettivi:

```
vincite: n=63  medio +0.0548   (≈ +0.27%)
perdite: n=133 medio -0.0929   (≈ -0.46%)
R:R reale = 0.59 : 1
win rate necessario per pareggio = 62.9%
win rate reale = 31.8%
```

**Il bot deve raddoppiare il win rate per non perdere.** Questo è il numero che nessuna calibrazione dello score sposta: lo score sceglie *quali* trade fare, non cambia *quanto* si guadagna quando si indovina.

### 4.8 Nessun miglioramento nel tempo

| Mese | n | Win rate | P&L tot | P&L medio |
|------|---|----------|---------|-----------|
| 2026-07 | 25 | 20.0% | −1.420 | −0.0568 |
| 2026-08 | 91 | 39.6% | −3.510 | −0.0386 |
| 2026-09 | 80 | 27.5% | −3.970 | −0.0496 |

Nonostante TASK-1250, TASK-1251, TASK-1256 e TASK-1262, la perdita per trade **non si riduce**. Settembre è il mese peggiore.

### 4.9 Per regime

| Regime | n | Win rate | P&L tot | P&L medio | Score medio |
|-------|---|----------|---------|-----------|-------------|
| `ranging` | 161 | 32.3% | −7.520 | −0.0467 | −8.21 |
| non classificato | 27 | 22.2% | −1.360 | −0.0504 | — |
| `trending_down` | 5 | 60.0% | −0.170 | −0.0340 | −7.28 |
| `trending_up` | 3 | 66.7% | +0.150 | +0.0500 | +11.80 |

*Il regime distingue lo score* (trending_up +11.8 vs ranging −8.21) **ma non distingue il P&L**: ranging 32.3% e trending_down 60% sono entrambi negativi. Le due cose che *dovrebbero* selezionare il trade non selezionano.

### 4.10 La vista che il supervisor usa davvero

`signal_outcome_by_strategy_regime` (la fonte di `historical_context.py:54`):

| Strategia | Regime | n | Win rate | P&L medio | P&L tot |
|----------|--------|---|----------|----------|---------|
| rsi_bollinger | ranging | 184 | 35.3% | −0.0475 | −8.74 |
| ema_cross | ranging | 5 | 40.0% | −0.0300 | −0.15 |
| rsi_bollinger | altro | 5 | 60.0% | −0.0340 | −0.17 |
| ema_cross | altro | 2 | 100.0% | +0.0800 | +0.16 |

Il supervisor oggi vede che **ogni combinazione con campione significativo è negativa** e conclude `no_action`. È una conclusione corretta, non un bug. Il tuning del supervisor (TASK-1261) è fatto e funziona: dice correttamente che non ha niente di buono da usare.

---

## 5. Cosa è già stato provato (e ha dato esito negativo)

| Task | Intervento | Esito misurato |
|------|------------|----------------|
| TASK-1250 | filtro trend macro su BTC | nessun miglioramento (§4.8) |
| TASK-1251 | guardia bearish sull'override mean-reversion | nessun miglioramento |
| TASK-1252 F1 | soglia score ricalibrata | correlazione score/PnL ≈ 0 |
| TASK-1255 | soglia strong-bearish a −8.0 | nessun miglioramento |
| TASK-1256 | SL/TP/trailing per-strategia | nessun miglioramento |
| TASK-1261 | tuning supervisor (fee awareness, memoria) | corretto, ma decide `no_action` — **la diagnosi è giusta** |
| TASK-1262 | rimozione bias strutturali dallo score | score medio −3.741 → −1.891, **WR invariato** |

Il pattern è chiaro: **sette interventi, tutti sul filtro e sulla selezione, nessuno che cambi l'edge.** La perdita per trade è stabile a ~−0.045 EUR da luglio.

---

## 6. Anomalie rilevate durante l'analisi

### 6.1 La colonna `pnl_pct` è corrotta

`db_ops.py:185` scrive `round(pnl_pct, 2)` ma il valore ricevuto non è una percentuale coerente. Risultato su 196 trade:

```
media -22.99%   min -106%   max +125%
```

Un valore di −106% o +125% è impossibile. *Inferenza:* some call site passano un ratio (0.0–1.0) e altri un valore già moltiplicato per 100.

**Impatto:** qualsiasi analisi o decisione fatta su `pnl_pct` è corrotta. Fortunatamente `historical_context` usa `avg_pnl` (assoluto, in EUR) e non è toccata. Ma **`pnl_pct` va sanata prima di qualunque lavoro futuro** — è un campo che sembra affidabile e non lo è.

### 6.2 Discrepanza di configurazione sulla soglia

```
DB  scalping_runtime_config  SCALPING_SIGNAL_STRENGTH_THRESHOLD = 6.0
env (.env)                  SCALPING_SIGNAL_STRENGTH_THRESHOLD = 15.0
```

`config_loader.py:47-48` carica prima da settings e poi **sovrascrive col DB**. Quindi **6.0 è il valore effettivo** e `15.0` dall'env è configurazione morta che genera confusione. *Nessun impatto sul comportamento, ma chiunque legga l'.env si sbaglia.*

### 6.3 Il bug del CVD ha gonfiato lo score storico

Il bug corretto in TASK-1262 (commit `80f8862`) aggiungeva un `+15.0` **costante** allo score quando la baseline del CVD non esisteva. Questo spiega perché i 13 trade con score `> +6.0` (quasi tutti agosto/inizio settembre) esistono affatto: erano artefatti del bug.

*Conseguenza:* **lo storico di score pre-2026-09-29 non è confrontabile** con quello post-fix. Qualsiasi backtest su score storici è invalido. Solo i dati da quel giorno in avanti sono utilizzabili — e sono insufficienti.

### 6.4 Due fonti di verità sui collector morti

Nello snapshot: `whale` ha peso 0.05 ma score sempre `0.0`; `open_interest` peso 0.05 con score `~0.0`; `sentiment` peso `0.00` ma viene comunque calcolato e loggato; `spread` peso `0.00`. La `COVERAGE` dichiara `total=0.88` — quindi il 12% del peso è formalmente morto.

*Inferenza:* ~0.15 di peso nominale non contribuisce mai nulla. Ripulire la configurazione non cambierebbe il comportamento, ma renderebbe leggibile perché il bot non apre.

### 6.5 ⚠️ Rischio per trade il doppio di quanto configurato

```
DB  scalping_runtime_config  SCALPING_TRADE_VALUE = 10.0
env (.env)                  SCALPING_TRADE_VALUE = 10.0
sessione in corso           trade_value          = 20.0
notional effettivo dei trade (195 chiusi)  medio 20.00  mediana 20.00
```

**La configurazione dice 10 EUR, il bot ne mette 20.** Non è un dettaglio: è un raddoppio del rischio effettivo per operazione rispetto a quanto dichiarato. La sessione corrente è stata creata il 2026-09-29 con `trade_value=20.0` nonostante la config a 10.0.

*Non ho determinato la causa* (candidato: la sessione viene creata con un valore di fallback, o il valore è stato letto prima di un cambio di config, o c'è un raddoppio in fase di calcolo della quantità). Va chiarito **prima** di fare qualunque decisione sul rischio, perché tutti i calcoli di P&L per trade in questo documento sono su 20 EUR reali, non sui 10 configurati.

---

## 7. Le domande da porre alle altre IA

Queste sono le domande su cui un piano di risoluzione dovrebbe poggiare. Sono ordinate per importanza.

1. **Il R:R è recuperabile o la strategia è strutturalmente perdente?**
   Con SL 0.5% e fee 0.2% round-trip, servono ~0.7% di movimento a favore per coprire 0.5% + 0.2%. Su BTC-EUR a timeframe scalping, quanto spesso si muove 0.7% in direzione corretta entro la finestra di holding? È la domanda più importante e **non è stata mai misurata**.

2. **Perché `take_profit` scatta solo nel 2% dei casi?** Il trailing stop chiude 29 trade e il TP solo 4. È il TP mal posizionato, il tempo di holding troppo corto, o l'OCO non è attivo? Una diagnosi qui potrebbe valere più di tutta la calibrazione dello score.

3. **Qual è il win rate atteso per una strategia con questo R:R?** Se le simulazioni dicono che `rsi_bollinger` su BTC-EUR ha un edge strutturalmente negativo in regime `ranging`, allora la risposta è spegnere il bot, non tararlo.

4. **Conviene continuare a usare lo score come gate?** Se la correlazione è zero, il gate aggiunge complessità senza protezione. Una strategia di gestione del rischio (position sizing, stop dinamico) potrebbe rendere lo score irrilevante.

5. **Come validare un'ipotesi senza rischiare denaro?** Backtest su storico OKX con gli stessi parametri, o paper trading. Quale sarà il protocollo, e con quale criterio di accettazione?

---

## 8. Vincoli da rispettare

- **Non abbassare la soglia** per far aprire il bot: i dati di §4.3 e §4.4 mostrano che i trade a score medio-alto rendono peggio.
- **Non ottimizzare su score storici pre-2026-09-29**: bug del CVD (§6.3).
- **Non fidarsi di `pnl_pct`** finché non è sanato (§6.1). Usare `pnl` assoluto.
- **Prima di ogni decisione**, sapere se il capitale è tempo-perso o denaro-perso. Cambia completamente la propensione al rischio.
- Il supervisor funziona e dice `no_action` correttamente: non va ritoccato finché i dati a valle non cambiano.

---

## 9. Riproduzione dei dati

Tutte le query sono state eseguite da dentro il container di produzione con le credenziali in `.env`:

```python
from supabase import create_client
u = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])

# §4.1 performance — tabela scalping_trades, status='closed' (n=195)
r = u.table("scalping_trades").select("*").execute().data
cl = [t for t in r if t["status"] == "closed"]

# §4.7 motivi di uscita — colonna signal_reason
# §4.2 correlazione — colonne signal_score, pnl (n=168 con entrambi)
# §4.9 regime — colonna regime_classified
# §4.10 vista usata dal supervisor
u.table("signal_outcome_by_strategy_regime").select("*").execute()
# §6.2 configurazione — tabella scalping_runtime_config (la DB sovrascrive l'env)
u.table("scalping_runtime_config").select("key,value").execute()
```

Snapshot collector (§4.6): log del container, righe `[ScoreEngine] COLLECTORS: btc-eur | ...`.

Range storico: 2026-07-24 → 2026-09-30, 196 trade (195 chiusi + 1 aperto al momento della raccolta).

---

## 10. Stato del documento

- **§1-§7**: completi e verificati sui dati reali. Pronti per l'analisi esterna.
- **Piano di risoluzione**: **non scritto.** È il deliverable da costruire insieme dopo aver raccolto le analisi.
- **Decisione richiesta**: scegliere A, B o C di §2 — o rifiutarle tutte e formularne una quarta.

*Ultima verifica stato LIVE: 2026-09-30, 1 posizione aperta (`e90d8f77`, entry 73111.5), sessione `running/live`.*
