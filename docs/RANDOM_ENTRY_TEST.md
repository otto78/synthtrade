# Random-entry test — gli entry del bot valgono qualcosa più di un orario casuale?

**Eseguito:** 2026-09-30 · **Dati:** 97.110 candele 1m BTC-EUR, 2026-07-24 → 2026-09-30 (OKX `/market/history-candles`) · **Script:** `scripts/random_entry_test.py`

## Domanda

Il 90% degli trade entra tramite override mean-reversion e nessuno di quelli ha score `>+6`.
Se le regole di uscita sono quelle che sono, l'entry conta o è solo rumore?

## Metodo

1. **Simulatore fedele.** Si riusano le funzioni di pricing di produzione
   (`app.scalping.pricing._exit_price_ratio`, `_expected_net_pct_at_exit`) e la stessa
   ladder break-even/trailing di `app.scalping.break_even`, con i guard di produzione
   (non si allenta mai lo stop, non si mette uno stop sopra il prezzo corrente).
   Nessuna logica di uscita è stata riscritta.

2. **Validazione prima del confronto.** Si rigiocano gli orari di entry reali e si
   confronta la distribuzione simulata con quella realmente realizzata in DB. Se il
   simulatore non riproduce i trade reali, il confronto con i random non significa
   niente. Questo passaggio è la condizione perché il test valga.

3. **Confronto.** Stessi orari reali contro orari casuali, stesso simulatore, stessa
   finestra. La differenza fra i due bracci è il test.

### Parametri, ricostruiti e verificati

I valori sono stati derivati dai trade reali e matchano al centesimo, il che conferma
che il modello è quello effettivamente in uso:

| | lordo | letto da |
|---|---|---|
| SL netto 0.50 (globale) | −0.3007% | `sl_price` misurato: −0.301% |
| SL netto 0.30 (override) | −0.1003% | `sl_price` misurato: −0.100% |
| TP netto 0.80 (globale) | +1.0019% | `tp_price` misurato: +1.002% |
| TP netto 0.55 (override) | +0.7514% | `tp_price` misurato: +0.751% |
| break-even lock 0.05 | +0.2504% | `sl_price` misurato: +0.250% |
| trailing step 1 / 2 / 3 | +0.4007 / +0.5510 / +0.7013% | misurati: +0.401 / +0.551 / +0.701% |

Fee 0.10% taker per lato (`entry_commission`/`exit_commission` misurati).
Break-even e trailing entrambi abilitati in `scalping_runtime_config`.

Il test gira due volte, una per bracket, così che la scelta del bracket non possa
influenzare la conclusione.

## 1. Validazione del simulatore

| bracket | simulato | realizzato in DB | differenza | p | motivi d'uscita concordanti |
|---|---|---|---|---|---|
| globale | −0.2140% | −0.2353% | +0.0213% | 0.595 | 148/186 (80%) |
| override | −0.2048% | −0.2353% | +0.0304% | 0.382 | 132/186 (71%) |

Il simulatore riproduce la realtà: la differenza è dentro il rumore e la mediana
coincide a −0.5000%. **Il test è valido.**

## 2. Confronto entry reali vs entry casuali (8000 sample)

### Bracket globale (usato dall'84% dei trade reali)

| | n | media/trade | mediana | win rate | P&L su 20 EUR |
|---|---|---|---|---|---|
| entry del bot | 186 | **−0.2140%** | −0.5000% | **40.9%** | −7.96 EUR |
| entry casuali | 7907 | −0.1729% | −0.5000% | 46.3% | −273.47 EUR |

**Differenza = −0.0410% per trade · CI95 [−0.0944%, +0.0148%] · p = 0.130**

### Bracket override

**Differenza = −0.0185% per trade · CI95 [−0.0471%, +0.0137%] · p = 0.242**

### Motivi d'uscita (bracket globale)

| motivo | bot | casuali |
|---|---|---|
| take_profit | 4 (2.2%) | 240 (**3.0%**) |
| stop_loss_trailing | 35 (18.8%) | 1617 (20.5%) |
| stop_loss_breakeven | 37 (19.9%) | 1806 (22.8%) |
| stop_loss | 110 (**59.1%**) | 4244 (53.7%) |

## Conclusione

**Gli entry del bot sono indistinguibili da un orario casuale, e la stima puntuale è
negativa in entrambi i bracket.**

Tre cose da mettere in fila:

1. **Il punto estimato è negativo** in entrambi i bracket: −0.041% e −0.019% per trade.
   Il bot perde *leggermente di più* del caso, non meno.
2. **Il win rate del bot è più basso** di quello casuale (40.9% vs 46.3%) e i suoi
   trade vanno più spesso a stop pieno (59.1% vs 53.7%).
3. **Gli entry casuali raggiungono il TP più spesso** del bot (3.0% vs 2.2%).

Il margine superiore dell'intervallo di confidenza è +0.0148% per trade: anche nella
migliore delle ipotesi, l'edge dell'entry logic vale al massimo +0.015% per trade, cioè
+0.003 EUR su 20 EUR di notional. Non è un edge, è rumore.

### Il vero dato che emerge: il TP è decorativo

Il TP viene centrato **3% delle volte** indipendentemente da come è stato scelto
l'entry. La scala break-even/trailing intercetta quasi tutto il movimento prima:
i due terzi delle uscite sono breakeven o trailing. In pratica l'esito è deciso dallo
stop iniziale, che scatta nel 54–59% dei casi, e la selezione dell'entry non cambia
quasi nulla.

Questo spiega anche perché il P&L lordo osservato sia ~0 a dispetto di 197 trade: non è
un edge annullato dalle fee, è un edge che **non esiste** e le fee si mangiano tutto
quello che si sarebbe potuto perdere. Il rischio con scelta casuale degli orari è
infinito, quindi il rendimento atteso è zero per costruzione, e il bot sta
effettivamente replicando quel rendimento con un rischio illimitato.

## Limiti dichiarati

- **12 trade su 198 esclusi**: 10 per orizzonte avanti <24h (dati non ancora disponibili),
  2 per un minuto assente nei dati OKX. Esclusi da entrambi i bracci, quindi il bias è
  lo stesso.
- **1m, long-only**: replica la produzione (100% dei trade reali è long). Non copre
  short.
- **1m non risolve il percorso intrabar**: se SL e TP cadono nella stessa candela si
  assume lo stop. Con SL a ~219 EUR su BTC è raro, e il trattamento è identico nei due
  bracci.
- **Nessun time-stop** in produzione, quindi i trade aperti oltre 24h sono censurati
  (93 su 7907 casuali, 0 sui 186 reali).

---

# Parte 2 — Break-even e trailing: bloccano le perdite o soltanto la percentuale di vittoria?

## Perché serve un'era a parte

L'override SL/TP per-strategia è online dal **2026-09-25 15:16 UTC** (commit `87a8f03`,
TASK-1256). Prima di allora il bracket era fisso e identico per tutti. Quindi:

| era | n | bracket iniziale | TP lordo |
|---|---|---|---|
| pre-override (≤ 25/09 15:16 UTC) | 185 | SL netto 0.50 | **+1.002% sempre** |
| post-override (≥ 25/09 15:16 UTC) | 13 | SL netto 0.30 | **+0.751% sempre** |

Il confronto entry-reali vs entry-casuali è stato rifatto **sui 182 trade dell'era a
bracket fisso** (esclusi 3 outlier con una coppia SL/TP diversa). La validazione tiene:
simulato −0.2083% vs realizzato −0.2333%, p=0.530, 144/180 motivi d'uscita concordanti.

> **Correzione rispetto alla Parte 1.** Nella Parte 1 ho riportato che l'override
> per-strategia "non è applicato nell'84% dei trade". Era sbagliato: avevo mescolato le
> due epoche, e i trade pre-override non hanno override per definizione. Nell'era
> post-override l'override funziona **13/13**. Non c'è nessun bug.

## Controfattuali: 2×2 su break-even e trailing

Il trailing in produzione è subordinato al break-even (Guard 1 di
`_check_and_apply_trailing`: senza `break_even_triggered` non fa nulla). "Solo trailing"
allunga quella guardia solo per isolare il contributo del trailing.

### Entry del bot (180 trade, era a bracket fisso)

| variante | media/trade | win % | media vincitori | media perdenti | P&L su 20 EUR |
|---|---|---|---|---|---|
| full (produzione) | −0.2083% | **41.7%** | +0.2000% | **−0.5000%** | −7.50 |
| solo break-even | −0.2208% | 41.7% | +0.1700% | −0.5000% | −7.95 |
| solo trailing | **−0.1820%** | 36.5% | +0.3708% | −0.5000% | −6.48 |
| nessuno | −0.2263% | 21.1% | +0.8000% | −0.5000% | −7.74 |

### Entry casuali (7907)

| variante | media/trade | win % | media vincitori | media perdenti |
|---|---|---|---|---|
| full (produzione) | −0.1729% | **46.3%** | +0.2060% | **−0.5000%** |
| solo break-even | −0.1817% | 46.1% | +0.1903% | −0.5000% |
| solo trailing | −0.1734% | 38.2% | +0.3555% | −0.5000% |
| nessuno | −0.2115% | 22.2% | +0.8000% | −0.5000% |

### Mix dei motivi d'uscita (braccio bot)

| variante | take_profit | trailing | break-even | stop_loss |
|---|---|---|---|---|
| full (produzione) | **2.2%** | 18.9% | 20.6% | 58.3% |
| solo break-even | 6.7% | 0.0% | 35.0% | 58.3% |
| solo trailing | 5.6% | 30.9% | 0.0% | 63.5% |
| nessuno | **21.1%** | 0.0% | 0.0% | 78.9% |

## Risposta: no, non scambiano vittorie con perdite

L'ipotesi era che i due blocchi di sicurezza abbassassero la percentuale di vittoria per
ridurre le perdite. I dati dicono il contrario, su entrambi i punti.

**1. Non riducono la percentuale di vittoria — la raddoppiano.**

| | nessuno | full |
|---|---|---|
| entry del bot | 21.1% | **41.7%** |
| entry casuali | 22.2% | **46.3%** |

**2. Non riducono le perdite. Mai.** La media dei perdenti è **−0.5000% in tutte e quattro
le varianti**, senza eccezioni. Non è una coincidenza: i due blocchi spostano lo SL solo
**verso l'alto**, mai verso il basso. Un trade che non raggiunge mai +0.15% netto perde
esattamente lo SL iniziale, sempre e allo stesso modo. **Il lato delle perdite è
strutturalmente congelato**: nessuna configurazione di break-even o trailing può
ridurlo.

**3. Quello che riducono è la vincita media**: da +0.80% a +0.20%. E il take profit
centrato crolla dal 21.1% al 2.2%, un fattore dieci.

Quindi scambiano **dimensione della vittoria per frequenza della vittoria**, non vittorie
per perdite.

**4. Lo scambio è favorevole.** Confronto appaiato sugli stessi entry (braccio casuale,
n=7498, potenza statistica reale):

| confronto | delta | CI95 | p |
|---|---|---|---|
| full − nessuno | **+0.0385%** | [+0.0240%, +0.0540%] | **<0.001** |
| solo trailing − full | +0.0001% | [−0.0121%, +0.0125%] | 0.996 |
| solo trailing − nessuno | +0.0386% | [+0.0236%, +0.0545%] | <0.001 |

I blocchi di sicurezza valgono **+0.0385% per trade** rispetto a non averli: sono
redditizi e vanno tenuti. Sul braccio bot (n=180) la potenza non basta a confermarlo
(+0.0225%, p=0.676) ma punta nella stessa direzione.

**5. Il break-even aggiunge zero.** `solo trailing − full = +0.0001%, p=0.996`. Il
trailing da solo fa tutto il lavoro; il lock a +0.05% netto è inerte. È una semplificazione
possibile, non un guadagno.

## La conseguenza che conta: il vero pulsante è lo SL iniziale

Il lato perdenti non si tocca con break-even né con trailing. Si tocca spostando lo SL
iniziale — che è esattamente ciò che fa l'override per-strategia, online da 5 giorni.

Config attuale (override: SL netto 0.30, TP netto 0.55) simulata su 8000 entry casuali:

| variante | media/trade | win % | media vincitori | media perdenti |
|---|---|---|---|---|
| full (produzione) | −0.1870% | 22.9% | +0.194% | **−0.3000%** |
| solo break-even | −0.1885% | 22.8% | +0.188% | −0.3000% |
| solo trailing | −0.1898% | 17.2% | +0.340% | −0.3000% |
| nessuno | −0.1944% | 12.4% | +0.550% | −0.3000% |

Due cose:

- **La perdita per perdente scende a −0.30%** dal −0.50%: il −40% è reale e immediato.
- **Ma le varianti si appiattiscono**: lo scarto fra full e nessuno è 0.007%, contro
  0.039% col bracket globale. Con SL a −0.30% serve +0.35% lordo per armare il
  break-even, quindi quasi tutta la macchina di sicurezza **non si attiva più**.

I 13 trade reali dell'era post-override dicono la stessa cosa: **10 su 13 sono `stop_loss`
puro**, 1 break-even, 1 trailing, 1 solo take profit. P&L −0.1769% per trade, −0.46 EUR.
Meglio del −0.2333% dell'era precedente, ma con 13 trade non è conclusivo.

## Sintesi

- La selezione dell'entry non aggiunge niente: indistinguibile dal caso in tutte le
  varianti, con stima puntuale sempre negativa.
- Break-even e trailing **non** funzionano come pensato: non riducono le perdite (non
  possono, per costruzione) e non riducono la vittoria. Raddoppiano il win rate e
  troncano la vincita media, e lo scambio è redditizio (+0.0385%/trade, p<0.001).
- Il vero collo di bottiglia è il **TP a +0.80% netto, centrato il 2–3% delle volte**,
  e il **lato perdenti fermo allo SL iniziale**. L'unica leva reale sulle perdite è
  avvicinare lo SL, e l'override appena entrato lo fa — ma con l'effetto collaterale di
  disattivare quasi del tutto la protezione.

---

# Parte 3 — Griglia SL/TP: accorciare o allungare il TP?

Domanda posta durante la stesura: la combinazione "SL stretto con TP lontano" è davvero
la peggiore, e serve accorciare il TP? **No, e la seconda parte era sbagliata.** La
griglia lo mostra.

6000 entry casuali, blocchi di sicurezza attivi, long. `step` = quanti scalini della
ladder trailing sopravvivono (`cap = TP netto − 0.10`).

| SL netto | TP netto | step | media/trade | win % | TP centrato % | media + | media − |
|---|---|---|---|---|---|---|---|
| 0.20 | 0.30 | 0 | −0.1880% | 3.0% | 1.8% | +0.200% | −0.200% |
| 0.20 | 0.40 | 1 | −0.1879% | 3.0% | 1.1% | +0.204% | −0.200% |
| 0.20 | 0.55 | 2 | −0.1880% | 3.0% | 0.6% | +0.206% | −0.200% |
| 0.20 | 0.80 | 3 | −0.1874% | 3.0% | **0.3%** | +0.225% | −0.200% |
| 0.30 | 0.30 | 0 | −0.1861% | 23.2% | **13.0%** | +0.190% | −0.300% |
| 0.30 | 0.40 | 1 | −0.1842% | 23.2% | 8.4% | +0.199% | −0.300% |
| 0.30 | 0.55 | 2 | −0.1838% | 23.2% | 4.1% | +0.202% | −0.300% |
| 0.30 | 0.80 | 3 | −0.1832% | 23.2% | 1.5% | +0.204% | −0.300% |
| 0.50 | 0.30 | 0 | −0.1742% | 47.1% | **26.7%** | +0.192% | −0.500% |
| 0.50 | 0.40 | 1 | −0.1709% | 47.0% | 17.3% | +0.201% | −0.500% |
| 0.50 | 0.55 | 2 | −0.1698% | 46.9% | 8.4% | +0.204% | −0.500% |
| 0.50 | 0.80 | 3 | −0.1687% | 46.9% | 3.1% | +0.206% | −0.500% |

## Cosa dice la griglia

**1. Il P&L è praticamente costante.** Su tutte e 12 le combinazioni la media sta fra
−0.1687% e −0.1880%: un'escursione di **0.019%**, che è il rumore e il drag delle fee.
Nessuna combinazione crea un edge.

**2. Lo SL, non il TP, determina il win rate.** A SL fissato il win rate è identico
qualunque sia il TP: 3.0% con SL 0.20, 23.2% con SL 0.30, 47% con SL 0.50. Non cambia
di una virgola passando da TP 0.30 a TP 0.80.

Il motivo è la meccanica: il break-even si arma a +0.15% netto, cioè +0.35% lordo. Con
SL a −0.10% lordo la probabilità di arrivarci prima dello stop è ≈ 0.10/0.45 = 22%, e i
22.9% osservati lo confermano. Con SL a −0.30% è 0.30/0.65 = 46%, contro 47% osservati.
Il win rate è interamente determinato da dove sta lo stop.

**3. Il TP determina solo quanto spesso arrivi al pieno obiettivo**, e il trailing lo
tronc comunque. Accorciare il TP da 0.80 a 0.30 fa salire il TP centrato da 1.5% a 13.0%
a SL 0.30 — e il P&L si muove di **0.003%**. È cosmetico.

**4. Perché è invariato.** Su un prezzo che si comporta come una passeggiata casuale, la
coppia (SL, TP) non crea né distrugge valore: il risultato atteso è il drag delle fee,
qualunque sia la coppia. Il bracket ridistribuisce la distribuzione, non il rendimento.
Questo è esattamente ciò che la Parte 1 aveva mostrato misurando l'entry contro il caso:
dato che l'entry non ha skill, non esiste una combinazione di uscita che la faccia
guadagnare.

**5. L'unica leva che muove il P&L è lo SL, e va verso il largo.** Da SL 0.20 a SL 0.50
il P&L migliora di 0.019% (−0.1880% → −0.1687%), con un win rate che sale dal 3% al 47%
e una perdita per perdente che raddoppia. Con uno stop stretto si paga il drag delle fee
molte volte su micro-movimenti che non coprono il costo di transazione.

Questo è l'opposto di quanto ha fatto l'override per-strategia, che ha spostato lo SL
dal netto 0.50 al 0.30.

## Ritiro

Nella Parte 2 avevo scritto "per tornare produttivo serve accorciare il TP, non stringere
lo SL". **È ritirato.** Accorciare il TP non migliora il P&L: cambia la percentuale di
vittoria e la frequenza con cui si chiude al TP pieno, lasciando il rendimento
invariato. Una configurazione con il 13% di TP centrati e una con l'1.5% perdono
esattamente la stessa somma.

Avevo anche scritto che "SL stretto con TP lontano è la combinazione peggiore". È vero
solo nel senso di **caratteristiche osservabili** — 3.0% di vittoria e 0.3% di TP
centrato sono l'aspetto peggiore possibile, e ogni trade diventa un lancio di moneta che
perde quasi sempre — ma non in senso di **denaro**: −0.1874% contro i −0.1687% della
config migliore. La formulazione mescolava le due cose.

## Cosa ne segue

Il ciclo di tuning SL/TP è chiuso, e non per un giudizio estetico ma perché la griglia
mostra che non c'è nulla da ottimizzare: il P&L è bloccato al drag delle fee. Le uniche
mosse che cambiano qualcosa sono fuori da questo ciclo:

1. **Avere un edge sull'entry** — che la Parte 1 ha escluso misurandolo contro il caso.
2. **Non pagare le fee** — maker invece che taker, o meno round-trip per unità di tempo.
   Su 0.20% a lato è il drag dominante e l'unica leva che resta.
3. **Non fare trading** — l'unica alternativa con rendimento atteso non negativo.

## Riproduzione

```bash
# dentro il container backend, dalla root del progetto
docker cp scripts/random_entry_test.py synthtrade_backend:/tmp/ret.py
docker exec -w /app synthtrade_backend python /tmp/ret.py --sample 8000
```

Le candele 1m vengono cachate in `/tmp/candles_1m_BTC-EUR.json`; la seconda esecuzione
non richiama OKX. `--all-eras` include i trade successivi all'override per-strategia.

