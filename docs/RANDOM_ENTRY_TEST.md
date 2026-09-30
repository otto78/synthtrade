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

## Riproduzione

```bash
# dentro il container backend, dalla root del progetto
docker cp scripts/random_entry_test.py synthtrade_backend:/tmp/ret.py
docker exec -w /app synthtrade_backend python /tmp/ret.py --sample 8000
```

Le candele 1m vengono cachate in `/tmp/candles_1m_BTC-EUR.json`; la seconda esecuzione
non richiama OKX.
