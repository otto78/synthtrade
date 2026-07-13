# TASK-OKX-RECAL — Ricalibrazione SL/TP su fee OKX reali

> Data: 13 luglio 2026
> Priorità: ALTA — bloccante prima di qualunque nuova sessione live/demo
> Motivazione: la migrazione a Bybit si è fermata a TASK-1200.A (accesso API custom bloccato per account EU retail — solo "Connetti ad applicazioni di terze parti", nessuna chiave System-generated disponibile). Si resta su OKX. Lo SL a 0,3% non è mai stato ricalibrato sul fee reale (0,20% maker / 0,35% taker, confermato via screenshot "Il mio livello di commissioni"), nonostante fosse già documentato come matematicamente impossibile con questo fee.
> Nota importante: questo task **non tocca la logica di calcolo** (`_net_to_gross_pct`, direzione SL/TP per BUY/SELL) — quella è già stata corretta in TASK-1127 (sCode 51280) e TASK-1128/1129. Qui si ricalibrano solo i **valori target** in config, sul fee reale certificato.

---

## 0. Punto di partenza — perché lo SL 0,3% è insostenibile

Con la formula già in uso in `router.py` (`_net_to_gross_pct`), il costo di round-trip R con il flusso attuale (entry market + exit market al trigger, entrambi taker) è:

```
R = fee_taker_entry + fee_taker_exit = 0,35% + 0,35% = 0,70%
```

Anche a **zero movimento di prezzo**, chiudere una posizione costa -0,70% netto solo di fee. Qualunque target di SL netto con magnitudine inferiore a 0,70% è quindi geometricamente impossibile: il prezzo dovrebbe muoversi nella direzione opposta a quella di un vero stop loss per far quadrare i conti. È lo stesso fenomeno già osservato e documentato in memoria di progetto ("con round-trip fees ~0,55%, un SL netto di 0,30% su una posizione buy è matematicamente impossibile") — qui il numero reale (0,70%) è anche peggiore di quello storicamente stimato.

**SL attuale in `.env` (`SCALPING_STOP_LOSS_PCT=0.3`) è sotto questa soglia: va cambiato prima di riaprire qualunque sessione, demo o live.**

---

## 1. Verifica preliminare obbligatoria — fee tier certificato, non assunto

Prima di calcolare qualunque target, verificare che il fee usato a runtime sia quello **realmente certificato** dall'exchange, non il fallback hardcoded. Dall'analisi Supabase già fatta durante la valutazione Bybit: **63 trade reali su 69 avevano `fee_tier_maker/taker = 0.001/0.001`** (fallback non certificato), solo 1 trade aveva registrato il rebate demo — nessuno aveva il fee live reale (0,20%/0,35%) certificato correttamente. Questo significa che, oltre a ricalibrare i target, va controllato se `get_trade_fee()` sta davvero certificando il fee tier in modalità live oggi.

### 1.A — Audit `fee_tier_certified` sulle sessioni recenti

```sql
SELECT id, started_at, mode, fee_tier_certified, fee_tier_raw
FROM scalping_sessions
WHERE mode = 'live' AND started_at > now() - interval '14 days'
ORDER BY started_at DESC;
```

Se `fee_tier_certified = false` o `fee_tier_raw` è nullo/vuoto sulla maggioranza delle sessioni live recenti, il problema non è solo il valore di SL/TP in config ma il fatto che `get_trade_fee()` in `okx_exchange.py` sta silenziosamente fallendo e cadendo sul fallback (0,001/0,001) — un fee **quasi 3,5 volte più basso** di quello reale (0,0035 taker), che rende i target netti calcolati completamente sballati anche dopo questo task.

### 1.B — Se il fallback è ancora in uso: fix prerequisito

Verificare in `okx_exchange.py` che `get_trade_fee()`/`_direct_fetch_trade_fee()` (TASK-1116.E) venga effettivamente chiamato all'avvio di ogni sessione live e che il risultato popoli `_execution_state["fee_tier_certified"] = True` prima che qualunque calcolo SL/TP avvenga. Se questo non risulta vero dall'audit SQL, **questo è un bug da fixare prima di continuare con la ricalibrazione** — altrimenti si aggiornano i target in config ma il codice continuerà silenziosamente a usare 0,001/0,001 a runtime, vanificando il lavoro.

**Non procedere a §2 finché §1.A non mostra `fee_tier_certified=true` su almeno le ultime 3-5 sessioni live.**

---

## 2. Opzioni di ricalibrazione — R reale = 0,70% (taker+taker)

Stessa metodologia già applicata nell'analisi Bybit (§0.4 del piano di migrazione), riscalata sul fee OKX reale. Formula: `gross = (1+net)/((1-f_entry)(1-f_exit)) - 1`, con `f_entry=f_exit=0,0035` (taker/taker, coerente col flusso attuale market-entry + market-at-trigger).

| Opzione | SL netto | TP netto | Distanza gross SL | Distanza gross TP | R:R netto |
|---|---|---|---|---|---|
| A — minimo fattibile (sconsigliata, troppo vicina al rumore) | 0,85% | 1,00% | 0,15% | 1,71% | 1,18:1 |
| **B — consigliata per il primo test** | **1,05%** | **1,55%** | **0,35%** | **2,26%** | **1,48:1** |
| C — margine di sicurezza maggiore | 1,30% | 2,00% | 0,61% | 2,72% | 1,54:1 |

Confronto con l'analisi già fatta per Bybit (R=0,50%): l'opzione B qui (SL 1,05% / TP 1,55%) è esattamente 1,4x più larga della opzione B Bybit (SL 0,75% / TP 1,10%) — coerente col fatto che R_okx (0,70%) è 1,4x R_bybit (0,50%). Nessuna sorpresa nei numeri, solo la conferma che restando su OKX il costo fisso per trade è strutturalmente più alto.

**Raccomandazione: partire con l'opzione B.** L'opzione A è tecnicamente valida ma la distanza gross SL di 0,15% è così stretta da essere probabilmente dentro il rumore di mercato normale su timeframe 1m — rischio concreto di stop-out immediati senza che il mercato si sia davvero mosso contro la posizione (lo stesso tipo di problema già osservato con SL troppo stretti nelle sessioni precedenti).

---

## 3. Modifiche da applicare

### 3.A — `.env` / `config.py`

```bash
# PRIMA (insostenibile con fee reali OKX):
SCALPING_STOP_LOSS_PCT=0.3
SCALPING_TAKE_PROFIT_PCT=0.5

# DOPO (opzione B, ricalibrata su fee reale 0,20%/0,35%):
SCALPING_STOP_LOSS_PCT=1.05
SCALPING_TAKE_PROFIT_PCT=1.55
```

Se il progetto usa anche `scalping_runtime_config` per override a runtime (introdotto nel piano supervisor, TASK-B3), aggiornare **entrambi** — `.env` come default di partenza, la riga DB se esiste già un valore precedente salvato lì che altrimenti continuerebbe a sovrascrivere il nuovo default:

```sql
UPDATE scalping_runtime_config
SET value = '1.05', updated_at = now()
WHERE key = 'SCALPING_STOP_LOSS_PCT';

UPDATE scalping_runtime_config
SET value = '1.55', updated_at = now()
WHERE key = 'SCALPING_TAKE_PROFIT_PCT';
```

### 3.B — Verifica limiti hardcoded del Supervisor

Il Supervisor AI ha un meccanismo di `update_threshold` con bound min/max già cablati per la vecchia soglia (`signal_strength_threshold`, non SL/TP direttamente — nessun conflitto atteso). Verificare comunque che non esista altrove un clamp implicito su SL/TP (es. un vecchio limite "SL max 0,5%" residuo di quando il valore era 0,3%) che tronchi silenziosamente il nuovo target a 1,05%. Grep mirato:

```bash
grep -rn "STOP_LOSS_PCT\|stop_loss_pct" synthtrade/backend/app/scalping/ | grep -i "max\|clamp\|limit"
```

---

## 4. Test da aggiungere prima del deploy

Riusare lo stesso pattern già presente in `test_okx_integration.py` (test 1111.F, fee/net pricing), con i nuovi valori:

```python
def test_sl_tp_recalibrated_okx_real_fees():
    """
    Con fee OKX reali (maker=0.0020, taker=0.0035) e target netti
    ricalibrati (SL=1.05%, TP=1.55%), verifica che:
    - il segno di sl_price sia coerente con la direzione (BUY: sotto entry)
    - la distanza gross calcolata corrisponda alla tabella §2 (tolleranza 0.01%)
    """
    entry_price = 100.0
    fee_taker = 0.0035

    sl_gross = abs(_net_to_gross_pct(1.05, fee_taker, fee_taker)) / 100
    tp_gross = abs(_net_to_gross_pct(1.55, fee_taker, fee_taker)) / 100

    sl_price = _sl_price_from_entry(entry_price, sl_gross, side="buy")
    tp_price = entry_price * (1 + tp_gross)

    assert sl_price < entry_price, "SL deve essere sotto entry per BUY"
    assert abs(sl_gross - 0.0035) < 0.0001   # ~0.35% gross, da tabella
    assert abs(tp_gross - 0.0226) < 0.0005   # ~2.26% gross, da tabella
```

Verificare che `_sl_price_from_entry` (helper già introdotto in TASK-1127/v1.4.13) sia effettivamente riusato qui invece di reintrodurre un calcolo inline — è il punto in cui il bug sCode 51280 era nato la prima volta.

---

## 5. Sequenza di verifica end-to-end

1. Applicare §3.A (config).
2. Eseguire il test §4 — deve passare senza modificare la logica esistente, solo con i nuovi input numerici.
3. Avviare una sessione **paper** (non demo, non live) e controllare nei log `[NET_PRICING]` che i valori mostrati corrispondano alla tabella §2, opzione B.
4. Solo se §1.A conferma `fee_tier_certified=true` sulle sessioni recenti: avviare una sessione **demo** OKX con un trade minimo, verificare che il bracket TP/SL venga accettato da OKX senza sCode 51280/51020/51008 (stessa checklist già usata nei fix precedenti).
5. Solo dopo una sessione demo pulita: valutare se procedere a una sessione live con capitale minimo, con conferma manuale esplicita — stessa procedura già in uso (`okx-live-runbook.md`).

---

## 6. Nota di chiusura sul confronto economico

Con questi target, il win rate storico noto (34,3% su 70 trade, periodo giugno-luglio) va riletto: quei trade erano quasi tutti su SL/TP da 0,3%/0,5%, geometricamente incoerenti con le fee reali — quindi quel numero **non è un baseline affidabile** per giudicare se i nuovi target funzionano meglio o peggio. Serve un nuovo campione di sessioni con i target ricalibrati prima di trarre qualunque conclusione quantitativa, esattamente come si sarebbe dovuto fare per Bybit (TASK-1212 del piano sospeso). Non confrontare le prossime sessioni con lo storico vecchio come se fosse comparabile.
