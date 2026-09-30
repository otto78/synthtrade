# ANALISI — Il bot non ha un edge, e la classe di strategia non è quella giusta

> **Versione 3 — 2026-09-30.** Riscritta dopo: random-entry test (TASK-1273), controfattuali
> break-even/trailing e griglia SL/TP (TASK-1274), e ricerca web su edge AI-crypto.
>
> La v2 lasciava aperta una domanda operativa — *«se il test conferma assenza di edge, cosa
> facciamo?»* (§4.3 v2). Quel test è stato eseguito. La risposta è: **niente di ciò che la v2
> proponeva funziona**, e la ricerca esterna spiega perché la domanda era formulata sulla
> leva sbagliata.
>
> Tutte le cifre sono rimisurate sul DB di produzione. Le inferenze sono marcate.
> Riproduzione: §10.

---

## 0. Cosa cambia rispetto alla v2

### 0.1 Le correzioni della v2 restano valide

La v2 aveva corretto due propri errori. **Entrambi i errori erano reali e le correzioni
restano valide** — le ripeto qui perché questo documento le sovrascrive:

- **`pnl_pct` non era corrotta** (v2 §0.1). Avevo stampato `mean(pnl_pct) * 100` su un campo
  già in percentuale. Il difetto era nel calcolo, non nei dati. `pnl_pct` reale:
  min −1.060%, max +1.250%, media −0.230%.
- **Lo score non è mai stato il gate** (v2 §0.2). Il 90% degli ingressi (178/197) entrava da
  un override mean-reversion *esplicitamente permesso «nonostante bias negativo»*, e di quegli
  178 **zero** aveva score > +6.0. La soglia +6.0 non ha mai autorizzato un trade. Quindi la
  correlazione score↔PnL misurata nella v1 descriveva una variabile senza ruolo causale nel 90%
  del campione.

### 0.2 ❌ Errore della v2: «le fee sono il buco reale», e il piano di Fase 4.3 è scartato

La v2 concludeva:

> «Il bot è quasi a zero lordo e perde solo di fee… La leva non è "selezionare meglio i trade",
> è ridurre il costo per trade o aumentare il movimento catturato per trade.»

E proponeva (§4.3 v2): timeframe più lungo, riduzione frequenza, verifica maker vs taker,
ricalibrazione del take profit.

**Questa diagnosi era corretta ma insufficiente, e il piano che ne derivava è sbagliato.**
Se il bot ha edge lordo ≈ zero *perché non prevede niente*, allora ridurre le fee non crea un
edge: rende il drenaggio più lento, non positivo. Il test random-entry (§2) dimostra che
l'ingresso **non contiene informazione**: non è "quasi a zero", è *esattamente* la distribuzione
del caso. Su un segnale privo di informazione, tutte e quattro le leve della v2.3 sono
inattive:

| Leva proposta v2.3 | Perché non funziona ora |
|---|---|
| Timeframe più lungo | Meno round-trip per unità di tempo, ma **stessa expectancy per trade** ≈ 0 − fee. Si riduce la varianza e il bleed, non si crea il segno. |
| Ridurre la frequenza | Idem: meno scommesse perse, non meno scommesse perse *a rate peggiore*. |
| Maker vs taker | Il differenziale è **0.08% maker vs 0.10% taker** (rilevato live, v2 §11): 0.02% per lato. Reale ma minuscolo, e sposta solo il drenaggio. |
| Ricalibrare il TP | La griglia SL/TP l'ha già fatto (§4): 12 combinazioni, **nessuna** fora il drenaggio. |

La v2 era quindi un piano per rendere *meno-negative* le perdite, non per evitarle. È
un'interpretazione ottimistica del risultato corretto che avevo misurato.

### 0.3 Nuovo: la v2 non poteva sapere che il supervisor è fuori dal percorso di ingresso

La v2 scriveva «il supervisor dice `no_action`: è la diagnosi corretta. Non va riticcato»,
leggendo il supervisor come un agente che osserva e giudica i trade. Il codice mostra invece
che **non è un entry decider** (§5). Questo non invalida la v2 — la sua conclusione operativa
era la stessa — ma spiega perché sette task di tuning del supervisor (1250→1262) non potevano
muovere il P&L: non erano nel percorso che decide gli ingressi.

---

## 1. Conclusione

**Non esiste edge, e non è un problema di configurazione.** Il bot è equivalente a scommettere
su un orario casuale, e la ricerca esterna dice che questo è il risultato atteso per la
classe di strategia, non un fallimento dell'implementazione.

Tre fatti, in ordine di importanza:

1. **Il timing d'ingresso è indistinguibile dal caso** (p = 0.207, §2).
2. **Nessun sistema retail di AI trading direzionale su crypto con edge verificabile
   out-of-sample e netto di fee è mai stato documentato** in letteratura o in dati pubblici
   (§3). Non perché non lo si sia cercato: tre ricerche indipendenti convergono.
3. **L'edge dei professionisti è market-neutral e strutturale** — carry/funding, spread,
   prezzo di esecuzione — non "l'AI legge gli indicatori e sceglie quando entrare" (§4). E
   nessuna di esse è economicamente fattibile con **€22** di capitale (§6).

**Raccomandazione: chiudere lo scalping direzionale.** Non "provare altro": chiudere, perché
la ricerca indica che la prossima leva non esiste per questa classe di strumento, non che
non l'abbiamo ancora trovata.

---

## 2. Il test decisivo — random-entry (TASK-1273)

Full report: `docs/RANDOM_ENTRY_TEST.md`. Dati: 97.110 candele 1m BTC-EUR, 24 lug → 30 set 2026.

### 2.1 Protocollo

Stesse regole di uscita reali (SL, TP, break-even, trailing, fee), **ingressi casuali** alla
stessa frequenza del bot, migliaia di ripetizioni. Se il bot cade dentro la distribuzione
random, le sue entrate non portano informazione.

### 2.2 Correzione dell'era di confronto

L'override per-strategia è online dal **2026-09-25 15:16 UTC** (commit `87a8f03`): 185 trade
pre-override con bracket fisso, 13 post con override. Confrontarli insieme mescola due
configurazioni — la v2 non lo faceva, io l'avevo fatto male in una prima stesura.

Era confrontabile: **182 trade pre-override**, 180 agganciabili ai dati.
Esclusi: 3 outlier storici, 2 senza candele minute, 10 senza 24h di futuro.

### 2.3 Risultato

```
simulato    -0.2083% per trade
DB reale    -0.2333% per trade
p = 0.530                                    -> indistinguibili
144/180 motivi d'ingresso concordanti (80%)
```

Confronto diretto bot vs **7.907 orari casuali**:

```
differenza   -0.0354%
CI 95%      [ -0.0889% , +0.0191% ]
p = 0.207
```

**Il bot non è peggio del caso. È equivalente al caso.** Tutte e quattro le varianti di
override producono risultati indistinguibili tra loro — la scelta della strategia non conta
quando l'ingresso è casuale.

---

## 3. Ricerca web — cosa dice il mondo esterno

Tre linee indipendenti. Conflitti d'interesse dichiarati in §9.

### 3.1 Dati reali su agenti AI che tradano — l'evidenza più forte

**«Paper Agents, Paper Gains»** (Pantera Capital, Stanford, IC3, Ava Labs) — 11 piattaforme
di agenti AI su Solana, **925.323 wallet**:

| Metrica | Valore |
|---|---|
| P&L collettivo utenti | **−$191,7M** |
| "Paper gains" dichiarati dalle piattaforme | +$34,3M |
| Token, crollo medio dai massimi | −93% (Solana: −54%) |
| Partecipanti in perdita | **62,2%** (575.246 wallet) |
| Top 1% dei wallet in profitto (2.590 su 259.016) | **81,4% di tutti i guadagni** ($1,81B) |
| Mediana dei rendimenti | negativa su **quasi ogni** piattaforma |

E il dato strutturalmente rilevante: **dei 10 progetti analizzati, solo 3 eseguivano trade in
autonomia**. Gli altri restituivano consigli, facevano simulazioni, o richiedevano intervento
umano. Questo descrive il progetto corrente quasi letteralmente (§5).

**Alpha Arena** (Nof1) — 8 modelli frontier, $10k ciascuno, 2 settimane, 4 gare su azioni US:
portafoglio complessivo **−1/3 del capitale**; profitable in **6 casi su 32**. Sotto lo stesso
prompt il migliore fece 158 trade, il peggiore 1.418.

**LA Times, 1 maggio 2026** — caso retail: agente addestrato sull'istinto del trader, $100k
paper su Alpaca. «Una buona decisione e una sequenza di sconfitte», −22% di drawdown. Il
trader stesso: «non sono pronto a consigliare a qualcuno di dargli soldi veri».

### 3.2 Il tasso di fallimento di base non si è mosso in 27 anni

Studio longitudinale citato da ZeroHedge / HedgeFundAlpha: 8M trader, 295M trade, 1998–2025.
**Il 74–89% perde in ogni evento di volatilità**, e il tasso non è cambiato né per educazione,
né per sophistication, né per piattaforma.

⚠️ **Conflitto d'interesse**: lo studio è di «PiP World», un lab che *vende* agenti AI, e
sostiene che i propri agenti hanno reso. **Non lo uso come carico probatorio.** Cito solo la
costante di fondo, che è coerente con 3.1.

### 3.3 AI che perde anche senza crypto

Bloomberg / Business Standard (6–7 maggio 2026), gare LLM su Wall Street: i modelli perdono
denaro, **trordano troppo**, e danno decisioni «wildly differenti» con prompt identici. Flat
Circle ha tracciato 11 arene finanziarie: in tutte almeno un modello ha guadagnato, ma in
**solo 2 la mediana era profittevole**.

---

## 4. Dove sta davvero l'edge dei professionisti

Questo è il punto che chiude la questione architetturale.

- **CoinDesk (28 ago 2026)**: i market maker incassano BTC da $62k a $77k **senza scommettere
  sulla direzione** — cash-and-carry, funding ~0,01%/8h. Nessuna previsione.
- **BitMEX**: «Il vero edge nell'arbitraggio non è trovare l'opportunità — i bot lo fanno in
  millisecondi. **È l'esecuzione.**» Con capitale pre-posizionato e fee note.
- **Polymarket** (Della Vedova / Bloomberg, 28 apr 2026): i bot hanno guadagnato $131M **non
  perché prevedessero meglio**, ma perché **entravano prima e a prezzi migliori**. I trader
  retail indovinavano l'esito corretto *più spesso* dei bot e ci perdevano comunque il denaro.
- **Funding arbitraggio** (Gate): 36–108% annuo ai picchi (2021), sceso al **7–9%** man mano
  che la competizione entrava. L'edge è stato arbitraggiato via.
- **Kraken** (CoinDesk, 2021): nel book la liquidità è migliorata per *più capacità di
  assorbimento del rischio*, non per più velocità. Colocation e FPGA sono barriere, non
  opzioni.

**Sintesi:** l'edge è **strutturale e market-neutral** (carry, spread, prezzo di esecuzione), o
richiede infrastruttura non accessibile. Nessuno dei due è «un modello che guarda i
grafici».

---

## 5. Perché l'architettura attuale non può essere corretta

### 5.1 Il supervisor non è un entry decider

Verificato sul codice:

- Azioni disponibili: `update_params | change_strategy | update_threshold | pause_trading |
  resume_trading | no_action`. **Nessun'azione di ingresso.**
- **Nessun riferimento** nel percorso di decisione (`api/pipeline.py`,
  `engine/execution_loop.py`).
- Gira su **timer**, non su segnale.
- Sessione corrente: 55 `no_action`, 2 `change_strategy`, 1 `update_threshold`.
- Tabella `supervisor_decisions`: **vuota** → nessuna ablation ricostruibile.

Il compito originale dell'utente — *«IA che analizzi storia e indicatori e decida quando
entrare»* — **non coincide con l'architettura**. Oggi un motore rule-based decide gli ingressi
e l'IA è un taratore di parametri e un interruttore. Il test random-entry ha misurato la
pipeline composta di ingressi, **non il supervisor isolato**: non gli si attribuisce un verdetto
che i dati non supportano.

### 5.2 La protezione dà win rate, non riduce le perdite

Controfattuali su ingressi casuali (TASK-1274):

```
                        senza protezioni    con BE+trailing
win rate                     21,1%               41,7%
media PERDENTI             -0,5000%            -0,5000%   <- invariata
media VINCITI              +0,80%              +0,20%
full vs none:  +0.0385%/trade,  CI95 [ +0.0240% , +0.0540% ],  p < 0.001
```

Break-even e trailing **aiutano in termini relativi** (+0.0385%/trade) ma **non riducono la
perdita media**: le perdite restano esattamente −0,5000% perché è lo stop. Trasformano
sconfitte in pareggi, non in vincite. È il profilo del grid bot con **93,3% di win rate che
perde il 95% del capitale**: alto win rate + payoff asimmetrico = bulldozer.

### 5.3 La griglia SL/TP non apre nessuna porta

12 combinazioni, medio range `−0.1687% .. −0.1880%`. Accorciare o allungare il TP cambia il
TP-hit rate e la forma del vincitore, **non il reddito**. Ritirata la precedente affermazione
«serve accorciare il TP».

### 5.4 Il win rate non è informazione sul reddito

Da mettere per iscritto, perché è l'errore più probabile di chi legge i numeri da fuori:
**aumento del win rate ≠ riduzione della perdita.** Qui i due valori si muovono in direzioni
opposte, e il secondo è quello che conta.

---

## 6. Perché €22 chiude ogni alternativa

Le alternative strutturali della §4 sono tutte **market-neutral**, e nessuna è economicamente
fattibile a questo capitale:

| Strategia | Rendimento reale | Perché non fattibile con €22 |
|---|---|---|
| Funding / basis arb | 7–9% annui | Richiede posizioni spot+perp di migliaia di €; la fee di un round trip mangia il rendimento |
| Market making passivo | spread, ~0,02–0,08% per lato | 0,02–0,08% su €22 è rumore; serve inventario e range continuo |
| Accumulation DCA BTC-EUR | espone a beta, non edge | non confrontabile: è buy & hold con friction |

**Il capitale è la condizione che chiude la discussione.** Non è un parametro da ottimizzare:
a €22 nessuna strategia market-negative sopravvive alle fee. Ogni euro di P&L che il sistema
produce è un artefatto di rounding.

---

## 7. Criteri di successo — chiusi, e perché

La v2 fissava soglie per validare un'ipotesi (§5 v2). Sono **superate**: il random-entry test le
ha smentite sulla metrica principale. Le conservo come **metodo** — è la parte che ha retto.

| Metrica | Soglia v2 | Esito misurato |
|---|---|---|
| Posizione nel random-entry test | sopra il 95° percentile | **p = 0.207 — dentro la distribuzione** |
| Expectancy netta per trade | > 0, CI che esclude lo zero | −0.2083% (sim) |
| Campione per la conclusione | 200–300 trade | 180 — sufficiente per **confutare**, non per confermare (§8) |

---

## 8. Onestà statistica — cosa il test poteva e non poteva mostrare

Da mettere per iscritto perché altrimenti la prossima lettura dei dati sbaglia nel verso
opposto.

Con 180 trade e la varianza osservata, il SEM della differenza è ~0,0276% per trade; la
deviazione standard per trade ~0,370%. Per rilevare un edge vero di **+0,02%/trade** servono
**~5.400 trade indipendenti** — non 180. E quei 180 non sono indipendenti (regimi sovrapposti,
stesso mercato, stessa settimana macro), quindi il numero reale è **più alto**.

Conseguenze, entrambe vere:

- L'esperimento era dimensionato per **confutare un edge grande**. L'ha fatto.
- **Non può né confermare né smentire un edge piccolo.** Ma un edge al di sotto di `+0,019%/trade`
  (estremo superiore della CI) è **più piccolo del costo di round-trip che il sistema già paga**
  (0,186% nella v2 §2.1, 0,16–0,20% con maker/taker reali). Quindi **non è sfruttabile da
  questa architettura comunque**.

Non abbiamo dimostrato «l'edge è esattamente zero». Abbiamo dimostrato: **l'edge è troppo piccolo
per coprire i costi.** È la stessa cosa, per una decisione operativa.

---

## 9. Fonti e conflitti d'interesse

| Fonte | Tipo | Uso |
|---|---|---|
| Paper Agents, Paper Gains (Pantera/Stanford/IC3/Ava Labs) | accademico + VC, peer-adjacent | **carico probatorio primario** |
| Alpha Arena / Bloomberg / Business Standard | giornalistica su esperimento controllato | corroborazione |
| LA Times, 1 mag 2026 | giornalistica, caso individuale | aneddotico |
| Studio 8M trader 1998–2025 (PiP World) | **conflitto d'interesse: il venditore** | solo la costante di fondo |
| AriseAlpha, comunicato "81% soffre la velocità" | **marketing puro** | **escluso** |
| CoinDesk / BitMEX / Gate / Kraken | provider, su un prodotto o un mercato specifico | il pattern meccanico, non le percentuali |
| MQL5, "Why AI Trading Bots Lose Money" | blog di settore | solo come check dei meccanismi, già coperti dalle fonti migliori |

**Nessuna fonte di questa sezione è usata per quantificare il P&L del nostro bot.** Servono solo
per stabilire se l'ipotesi «esiste un edge direzionale retail verificabile» sia falsa in
letteratura — e lo è. I numeri del bot vengono solo dal DB di produzione.

---

## 10. Riproduzione

```python
from supabase import create_client
u = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
cl = [t for t in u.table("scalping_trades").select("*").execute().data if t["status"] == "closed"]

# §2.3 random-entry  -> scripts/random_entry_test.py (non dal DB: serve lo storico 1m)
# §2.1 lordo vs netto -> sum(pnl), sum(entry_commission + exit_commission)
# §0.1 bypass del gate -> colonna strategy_rejection_reason
# §2.3 motivi di uscita  -> colonna signal_reason  (NON exit_reason)
# §5.1 vista supervisor -> u.table("supervisor_decisions").select("*")  -> vuota
```

Random-entry test completo e riproducibile: `scripts/random_entry_test.py`, report
`docs/RANDOM_ENTRY_TEST.md`. Cache candele: `/tmp/candles_1m_BTC-EUR.json` (97.110 candele).

`pnl` è già netto (`trade_executor.py:279`); il lordo è `pnl + commissioni`.
14 trade su 197 non hanno commissione registrata: le loro fee sono **stimate**, non misurate.

*Stato LIVE al momento della stesura: sessione `running/live`, **0 posizioni aperte**,
balance 21,94 EUR, `hold_pnl_pct 1.77` (benchmark buy&hold su trade chiusi, **non** una
posizione aperta — calcolato in `rest/performance.py:127`).
Fee tier live: **maker 0,08% / taker 0,10%** (rilevato da `okx_exchange.py`).
Risk config: TP 0,8% / SL 0,5%.*

---

## 11. Cose da non fare, riviste

Restano valide dalla v2:

- **Non abbassare la soglia dello score**: non è mai stato il gate.
- **Non aumentare lo stake**: con edge ≈ zero, raddoppiare lo stake raddoppia la perdita.
- **Non usare `pnl_pct` come se fosse corrotto**: è integro.
- **Non confrontare score pre-2026-09-29 col post-fix** (bug CVD `+15`).

Nuove:

- **Non presentare la riduzione delle fee come soluzione.** Su un ingresso privo di
  informazione, le fee rendono il drenaggio più lento, non positivo. Era la leva centrale
  della v2 ed è sbagliata.
- **Non citare lo studio di PiP World come prova.** Vende agenti AI.
- **Non aggiungere logica al supervisor** per "migliorare le entrate": non è nel percorso
  di decisione (§5.1).
- **Non inseguire il win rate.** Alza il win rate, non il reddito (§5.4).
- **Non riaprire il tuning SL/TTP.** La griglia l'ha già escluso (§5.3).

---

## 12. Stato del documento

- **Diagnosi:** chiusa. Test decisivo eseguito (§2), ricerca esterna convergente (§3),
  meccanica dell'edge dei professionisti identificata (§4), vincolo di capitale (§6).
- **Piano:** non ce n'è. La v2 ne aveva uno (§4.3) e quel piano è stato **eseguito e
  superato** — non ne resta uno di successivo, perché la ricerca non ne indica uno per questa
  classe di strumento.
- **Decisione:** chiudere lo scalping direzionale, in attesa di conferma dell'utente su
  capitale e orizzonte temporale prima di qualunque progetto futuro.
- **Aperto:** nessuna domanda tecnica bloccante. §8 è l'unico caveat e non cambia la
  decisione.
