# Fix Chart Reset + Mode Consistency on Mode Switch

## Problema 1: Chart si azzera quando si esce/rientra dallo scalping
- `LiveChartComponent` viene distrutto/ricreato quando si naviga tra route
- Il WS si disconnette/riconnette, ma le candele storiche non vengono sempre ricaricate correttamente
- Fix: Forzare ricarica candele storiche dopo riconnessione WS + su init con sessione attiva

## Problema 2: Cambiando modalità (test↔live) la sessione scalping rimane attiva
- `POST /api/config/mode { mode: 'test' }` cambia solo TRADING_MODE
- La sessione scalping in `_execution_state` rimane `running` con la vecchia modalità
- Quando si torna allo scalping, `GET /session` restituisce ancora la sessione attiva
- Fix: Quando la modalità cambia, fermare automaticamente le sessioni scalping con modalità diversa