# TASK-1243 — Fase 3: Revisione struttura TP/SL (Trailing SL a Break-Even)

> **Stato**: PIANIFICATO (Attesa validazione statistica Fase 1 e 2 prima dell'esecuzione)
> **Data**: 3 Agosto 2026
> **Priorità**: MEDIA

## Il Problema
Nell'attuale configurazione (TP 0.80%, SL 0.50%), le commissioni round-trip reali (0.20%) erodono il 40% del margine dello Stop Loss.
Il Risk:Reward reale collassa, obbligando il sistema a un win rate molto alto per raggiungere il break-even.
Allargare i margini (Opzione A) trasformerebbe il bot in un sistema micro-swing e ridurrebbe la frequenza dei trade, invalidando le logiche del Supervisor.

## La Soluzione (Opzione B)
Introdurre un **Trailing Stop Loss a Break-Even**.
L'obiettivo è proteggere il capitale sui trade che partono nella giusta direzione ma invertono prima di colpire il TP a 0.80%.

- **Trigger di attivazione**: +0.35% (copre abbondantemente le fee dello 0.20%).
- **Azione**: Spostare lo Stop Loss interno al prezzo di Entry + fee.

## Sub-Tasks di Implementazione

1. **Aggiornamento Modello Posizione (`position_manager.py`)**
   - Aggiungere `break_even_triggered: bool = False`.
   - Aggiungere `break_even_price: Decimal`.
   - Implementare metodo `update_trailing_sl(current_price, fee_rate)` per verificare la soglia e aggiornare lo SL interno.

2. **Integrazione nel Loop Esecutivo (`candle_processor.py`)**
   - Richiamare `pm.update_trailing_sl` a ogni tick di prezzo/candela utile.
   - Generare evento websocket `trailing_sl_activated` per notifica frontend e log.

3. **Integrazione Ordini OKX (`okx_exchange.py`)**
   - Poiché i Bracket Order/OCO sono gestiti nativamente da OKX (come _algo orders_), useremo l'endpoint ufficiale **`POST /api/v5/trade/amend-algos`** per modificare al volo i parametri di Stop Loss senza cancellare l'ordine esistente.
   - **Dettagli API OKX v5**:
     - *Endpoint*: `/api/v5/trade/amend-algos`
     - *Metodo*: `POST`
     - *Formato Payload*: Singolo oggetto JSON `{}` (a differenza di `cancel-algos` che richiede un array `[{}]`).
     - *Parametri Obbligatori*: `instId` (es. `BTC-EUR`), `algoId` (ID univoco del bracket_id assegnato in fase di apertura).
     - *Parametri di Aggiornamento*:
       - `newSlTriggerPx`: Il nuovo prezzo trigger per far scattare lo Stop Loss (che diventerà il nostro Break-Even point + fee).
       - `newSlOrdPx`: Il nuovo prezzo limite a cui piazzare l'ordine di SL (se è -1 viene eseguito a mercato).
     - *Nota su TP*: Se volessimo cancellare il Take Profit, imposteremmo `newTpTriggerPx: "0"`, ma a noi interessa solo alzare il `newSlTriggerPx`.
   - Implementare `exchange.amend_oco_stop_loss(symbol, algo_id, new_sl_trigger, new_sl_order)` che esegua questa richiesta firmata.

4. **Testing e Validazione**
   - Unit test su `position_manager` simulando traiettoria Entry -> Pump +0.40% -> Dump -0.50%.
   - Validazione in paper trading.
