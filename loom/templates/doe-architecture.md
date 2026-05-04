# Architettura DOE — Architettura Operativa

> Separazione delle responsabilità per massimizzare affidabilità e ridurre errori LLM.

---

## 🎯 Problema

Gli LLM sono probabilistici. Ogni decisione ha ~90% di accuratezza.

**Matematica spietata:**
- 1 step: 90% successo
- 2 step: 81% successo (0.9 × 0.9)
- 3 step: 73% successo
- 5 step: 59% successo
- 10 step: 35% successo

**Conclusione:** Concatenare decisioni LLM porta a fallimenti frequenti.

---

## 💡 Soluzione

Spingere la complessità in codice deterministico. L'LLM si concentra solo sul decision-making.

```
┌─────────────────────────────────────────┐
│ Livello 1: DIRETTIVE (Cosa fare)       │
│ directives/*.md — SOP in linguaggio     │
│ naturale, obiettivi, input, output      │
├─────────────────────────────────────────┤
│ Livello 2: ORCHESTRAZIONE (Decisioni)  │
│ Routing intelligente tra direttive     │
│ e script di esecuzione                 │
├─────────────────────────────────────────┤
│ Livello 3: ESECUZIONE (Fare il lavoro) │
│ execution/*.py — Script deterministici │
│ Variabili d'ambiente in .env           │
└─────────────────────────────────────────┘
```

---

## 📚 Livello 1 — Direttive (Cosa fare)

### Cos'è

SOP (Standard Operating Procedures) scritte in Markdown che definiscono **cosa** fare.

### Dove vivono

`directives/*.md`

### Cosa contengono

1. **Obiettivo** — Cosa vogliamo ottenere
2. **Input** — Dati necessari
3. **Tool/Script** — Quale script di esecuzione usare
4. **Output** — Risultato atteso
5. **Casi limite** — Errori comuni e come gestirli
6. **Esempi** — Casi d'uso concreti

### Esempio: `directives/send-email.md`

```markdown
# Direttiva: Inviare Email

## Obiettivo
Inviare email transazionali agli utenti.

## Input
- `recipient_email` (string) — Email destinatario
- `subject` (string) — Oggetto email
- `body` (string) — Corpo email (HTML o plain text)
- `template_id` (optional string) — ID template predefinito

## Tool da usare
`execution/send_email.py`

## Output
- Successo: `{"status": "sent", "message_id": "abc123"}`
- Fallimento: `{"status": "error", "reason": "..."}`

## Casi limite
1. **Email invalida** → Validare con regex prima di chiamare script
2. **Rate limit** → Retry con backoff esponenziale (max 3 tentativi)
3. **Template non trovato** → Fallback su body plain text

## Esempi
- Email di benvenuto: `template_id="welcome"`
- Reset password: `template_id="password_reset"`
- Notifica generica: Usa `body` direttamente
```

### Principi

- **Linguaggio naturale** — Scrivi come parleresti a un collaboratore
- **Completo ma conciso** — Tutte le info necessarie, niente di più
- **Esempi concreti** — Casi d'uso reali
- **Casi limite documentati** — Errori comuni e soluzioni

---

## 🤖 Livello 2 — Orchestrazione (Decisioni)

### Cos'è

Il lavoro dell'agente AI: routing intelligente tra direttive e script.

### Responsabilità

1. **Interpretare l'intento** — Capire cosa vuole l'utente
2. **Scegliere la direttiva** — Quale SOP seguire
3. **Raccogliere input** — Chiedere dati mancanti
4. **Chiamare script** — Eseguire tool di Livello 3
5. **Gestire errori** — Retry, fallback, notifiche
6. **Rispondere all'utente** — Comunicare risultato

### Esempio: Flusso "Invia email di benvenuto"

```
1. Utente: "Invia email di benvenuto a mario@example.com"

2. Agente interpreta:
   - Intento: Inviare email
   - Tipo: Benvenuto
   - Destinatario: mario@example.com

3. Agente legge: directives/send-email.md

4. Agente raccoglie input:
   - recipient_email: "mario@example.com"
   - template_id: "welcome"
   - subject: (preso da template)
   - body: (preso da template)

5. Agente chiama: execution/send_email.py

6. Script ritorna: {"status": "sent", "message_id": "xyz789"}

7. Agente risponde: "✅ Email di benvenuto inviata a mario@example.com"
```

### Principi

- **Non fare lavoro complesso** — Delega a script deterministici
- **Gestisci errori gracefully** — Retry, fallback, notifiche chiare
- **Documenta decisioni** — Logga perché hai scelto quella direttiva
- **Chiedi se incerto** — Meglio chiedere che sbagliare

---

## ⚙️ Livello 3 — Esecuzione (Fare il lavoro)

### Cos'è

Script deterministici che fanno il lavoro concreto.

### Dove vivono

`execution/*.py` (o `.js`, `.rs`, etc.)

### Cosa fanno

1. **Chiamate API** — HTTP requests a servizi esterni
2. **Elaborazione dati** — Parsing, trasformazione, validazione
3. **Database operations** — CRUD su DB
4. **File operations** — Lettura/scrittura file
5. **Calcoli complessi** — Algoritmi deterministici

### Esempio: `execution/send_email.py`

```python
#!/usr/bin/env python3
"""
Script deterministico per invio email via SendGrid.

Input (CLI args):
  --recipient: Email destinatario
  --subject: Oggetto email
  --body: Corpo email (HTML o plain text)
  --template-id: (optional) ID template SendGrid

Output (JSON):
  Success: {"status": "sent", "message_id": "..."}
  Error: {"status": "error", "reason": "..."}

Env vars:
  SENDGRID_API_KEY: API key SendGrid
"""

import argparse
import json
import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(recipient, subject, body, template_id=None):
    """Invia email via SendGrid."""
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        return {"status": "error", "reason": "SENDGRID_API_KEY not set"}
    
    try:
        message = Mail(
            from_email="noreply@example.com",
            to_emails=recipient,
            subject=subject,
            html_content=body
        )
        
        if template_id:
            message.template_id = template_id
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        return {
            "status": "sent",
            "message_id": response.headers.get("X-Message-Id")
        }
    
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipient", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--template-id", default=None)
    args = parser.parse_args()
    
    result = send_email(
        args.recipient,
        args.subject,
        args.body,
        args.template_id
    )
    
    print(json.dumps(result))
    sys.exit(0 if result["status"] == "sent" else 1)

if __name__ == "__main__":
    main()
```

### Principi

- **Deterministico** — Stesso input = stesso output
- **Testabile** — Unit test facili da scrivere
- **Robusto** — Gestione errori completa
- **Documentato** — Docstring con input/output/env vars
- **JSON output** — Facile da parsare per l'agente
- **Exit code** — 0 = successo, 1+ = errore

---

## 🔄 Flusso Completo

### Esempio: "Invia report settimanale"

```
┌─────────────────────────────────────────────────────────────┐
│ UTENTE                                                      │
│ "Invia il report settimanale a tutti gli admin"            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LIVELLO 2: ORCHESTRAZIONE (Agente AI)                      │
│                                                             │
│ 1. Interpreta intento: "Inviare report settimanale"        │
│ 2. Legge: directives/weekly-report.md                      │
│ 3. Identifica step:                                         │
│    a) Recuperare lista admin                                │
│    b) Generare report                                       │
│    c) Inviare email a ciascun admin                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LIVELLO 3: ESECUZIONE (Script deterministici)              │
│                                                             │
│ Step a) execution/get_admins.py                             │
│   → Output: ["admin1@ex.com", "admin2@ex.com"]             │
│                                                             │
│ Step b) execution/generate_report.py --period=week         │
│   → Output: {"html": "...", "stats": {...}}                │
│                                                             │
│ Step c) execution/send_email.py (loop per ogni admin)      │
│   → Output: {"status": "sent", "message_id": "..."}        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LIVELLO 2: ORCHESTRAZIONE (Agente AI)                      │
│                                                             │
│ 4. Verifica risultati:                                      │
│    - 2 admin trovati ✅                                     │
│    - Report generato ✅                                     │
│    - 2 email inviate ✅                                     │
│                                                             │
│ 5. Risponde all'utente                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ UTENTE                                                      │
│ "✅ Report settimanale inviato a 2 admin"                  │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Vantaggi

### 1. Affidabilità

- Script deterministici = 100% accuratezza
- LLM solo per decisioni = meno errori
- Testabilità completa

### 2. Manutenibilità

- Direttive facili da aggiornare
- Script riutilizzabili
- Separazione delle responsabilità

### 3. Debuggabilità

- Errori isolati per livello
- Log chiari
- Facile identificare dove fallisce

### 4. Scalabilità

- Nuove feature = nuova direttiva + nuovo script
- Riuso di script esistenti
- Parallelizzazione facile

---

## ⚠️ Anti-Pattern

### ❌ LLM fa tutto

```
Utente: "Invia email"
LLM: Genera codice Python → Esegue → Gestisce errori → Risponde
```

**Problema:** Ogni step può fallire. Debugging impossibile.

### ❌ Script fa decisioni

```python
# execution/send_email.py
if user_type == "premium":
    template = "premium_welcome"
elif user_type == "free":
    template = "free_welcome"
else:
    # Cosa fare? Script non sa decidere
```

**Problema:** Logica di business in script deterministico.

### ❌ Direttive troppo vaghe

```markdown
# Direttiva: Gestire utenti

Fai cose con gli utenti.
```

**Problema:** Agente non sa cosa fare.

---

## ✅ Best Practices

### 1. Direttive

- **Una direttiva = un obiettivo** — Non mescolare responsabilità
- **Esempi concreti** — Almeno 2-3 casi d'uso
- **Casi limite documentati** — Errori comuni e soluzioni
- **Riferimenti a script** — Quale tool usare

### 2. Orchestrazione

- **Delega sempre** — Non fare lavoro complesso
- **Gestisci errori** — Retry, fallback, notifiche
- **Logga decisioni** — Perché hai scelto quella direttiva
- **Chiedi se incerto** — Meglio chiedere che sbagliare

### 3. Esecuzione

- **Deterministico** — Stesso input = stesso output
- **JSON output** — Facile da parsare
- **Exit code** — 0 = successo, 1+ = errore
- **Env vars** — Credenziali in `.env`
- **Documentato** — Docstring completo

---

## 📊 Metriche di Successo

### Prima del Framework

- **Accuratezza end-to-end:** 35% (10 step LLM)
- **Debugging:** Difficile (errore dove?)
- **Manutenzione:** Complessa (tutto in prompt)

### Dopo il Framework

- **Accuratezza end-to-end:** 90% (1 decisione LLM + 9 script deterministici)
- **Debugging:** Facile (errore isolato per livello)
- **Manutenzione:** Semplice (direttive + script separati)

---

## 🎓 Quando Usare Questo Framework

### ✅ Usa quando

- Hai task complessi multi-step
- Serve affidabilità alta (>90%)
- Lavori con più agenti AI
- Serve manutenibilità a lungo termine

### ❌ Non usare quando

- Task semplici (1-2 step)
- Prototipo rapido (overkill)
- Nessuna necessità di affidabilità

---

## 📚 Risorse

- **Template direttiva:** `directives/_template.md`
- **Template script:** `execution/_template.py`
- **Esempi completi:** Vedi progetto MAYA

---

**Versione:** 1.0.0  
**Ultima modifica:** 2025-01-XX
