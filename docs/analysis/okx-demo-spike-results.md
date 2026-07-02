# OKX Demo Spike Results — TASK-1100

> Data primo run: 2026-07-02  
> Script: `scripts/test_okx_demo.py`  
> Modalita': read-only, nessun ordine piazzato

---

## Stato Sintetico

| Area | Stato | Evidenza |
|---|---|---|
| Credenziali presenti in `.env` | OK | Lo script carica API key, secret e passphrase demo dal `.env` locale gitignored |
| Public time OKX | OK | `GET /api/v5/public/time` risponde `code=0` |
| Public instruments Demo | OK parziale | `GET /api/v5/public/instruments?instType=SPOT` con header demo risponde `code=0`, 529 strumenti spot |
| `OKB-EUR` in Demo | FAIL | `code=51001`, "Instrument ID ... doesn't exist" |
| `BNB-USDC` in Demo | FAIL | `code=51001`, "Instrument ID ... doesn't exist" |
| IP whitelist | OK | IP pubblico verificato da questa macchina: `77.32.127.105`, coerente con whitelist comunicata |
| Private balance | BLOCKED | HTTP 401, `code=50119`, "API key doesn't exist" |
| Fee tier | BLOCKED | Dipende da private auth, stesso `50119` |
| Market order demo | NON ESEGUITO | Script read-only; ordine richiede flag esplicito |

---

## Dettaglio Strumenti

La lista pubblica live verificata prima mostrava `OKB-EUR` e `BNB-USDC`, ma la lista con header Demo Trading non li espone.

Esempi di strumenti EUR live disponibili nel contesto Demo al primo run:

- `SOL-EUR`
- `BCH-EUR`
- `BTC-EUR`
- `ETH-EUR`
- `AAVE-EUR`
- `AGIX-EUR`
- `APT-EUR`
- `ATOM-EUR`
- `FET-EUR`
- `GRASS-EUR`
- `ICP-EUR`
- `IMX-EUR`
- `PUMP-EUR`
- `USDC-EUR`
- `USDT-EUR`
- `XRP-EUR`

Decisione provvisoria:

- Default live candidato resta `OKB-EUR`, ma va validato runtime.
- Default demo non puo' essere `OKB-EUR` se il risultato resta questo.
- Per Demo Trading usare fallback automatico: preferire `SOL-EUR`, `BTC-EUR`, `ETH-EUR`, poi primo strumento EUR live restituito dall'endpoint.

---

## Blocco Private Auth

Endpoint:

```text
GET /api/v5/account/balance
```

Risultato:

```json
{
  "code": "50119",
  "msg": "API key doesn't exist",
  "_http_status": 401
}
```

Interpretazione probabile:

La schermata OKX condivisa mostra una key `synthtrade_demo` sotto Trading demo, con permessi `Leggi` e `Trading`, creata dal pannello `API e connessioni` Demo Trading. L'IP pubblico verificato dal terminale e' `77.32.127.105`, uguale alla whitelist comunicata.

Cause residue piu' probabili:

1. API key completa copiata nel `.env` diversa dalla riga mostrata in UI, anche se il prefisso coincide.
2. API key non ancora propagata lato OKX.
3. Passphrase o secret copiati con differenze non visibili.
4. Key generata/visualizzata sul conto principale Demo, ma private endpoint agganciato da OKX a un contesto diverso.

Azioni richieste prima di proseguire con ordini:

- Verificare in OKX: Trade -> Demo Trading -> Personal Center -> Demo Trading API.
- Confermare che la key demo sia attiva e abbia permessi Read/Trade.
- Verificare nella schermata dettaglio/modifica che API key completa, secret e passphrase coincidano esattamente con il `.env`.
- Rigenerare la key demo se il problema persiste.

---

## Implicazioni sui Task

- TASK-1100 resta bloccato sulla private auth prima di market order, fee tier e WS private/business.
- TASK-1103 deve implementare fallback strumenti demo/live, non hardcodare `OKB-EUR`.
- TASK-1109 deve selezionare default da lista strumenti runtime.
- TASK-1114 non puo' partire finche' `trade-fee` non risponde con credenziali valide.

---

## Prossimo Run

Comando read-only:

```bash
python scripts/test_okx_demo.py
```

Comando ordine demo, solo dopo auth privata OK:

```bash
python scripts/test_okx_demo.py --symbols SOL/EUR --place-market-order --market-quote-amount 10
```
