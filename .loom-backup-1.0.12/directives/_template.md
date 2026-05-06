# Direttiva: [Nome Direttiva]

> Breve descrizione (1 frase) di cosa fa questa direttiva.

---

## 🎯 Obiettivo

[Descrizione dettagliata dell'obiettivo. Cosa vogliamo ottenere?]

---

## 📥 Input

Parametri necessari per eseguire questa direttiva:

- `param1` (string) — Descrizione parametro 1
- `param2` (integer) — Descrizione parametro 2
- `param3` (boolean, optional) — Descrizione parametro 3 (default: false)

---

## 🛠️ Tool da Usare

### Script Principale

`execution/script_name.py`

### Chiamata

```bash
python execution/script_name.py \
  --param1="value1" \
  --param2=123 \
  --param3
```

### Alternativa (se multi-step)

1. **Step 1:** `execution/step1.py` — Descrizione step 1
2. **Step 2:** `execution/step2.py` — Descrizione step 2
3. **Step 3:** `execution/step3.py` — Descrizione step 3

---

## 📤 Output

### Successo

```json
{
  "status": "success",
  "data": {
    "field1": "value1",
    "field2": 123
  }
}
```

### Fallimento

```json
{
  "status": "error",
  "reason": "Descrizione errore",
  "code": "ERROR_CODE"
}
```

---

## ⚠️ Casi Limite

### 1. [Nome Caso Limite 1]

**Problema:** Descrizione del problema

**Soluzione:** Come gestirlo

**Esempio:**
```
Input: ...
Errore: ...
Azione: ...
```

### 2. [Nome Caso Limite 2]

**Problema:** Descrizione del problema

**Soluzione:** Come gestirlo

**Esempio:**
```
Input: ...
Errore: ...
Azione: ...
```

### 3. [Nome Caso Limite 3]

**Problema:** Descrizione del problema

**Soluzione:** Come gestirlo

**Esempio:**
```
Input: ...
Errore: ...
Azione: ...
```

---

## 📚 Esempi

### Esempio 1: [Descrizione Caso d'Uso 1]

**Contesto:** Descrizione del contesto

**Input:**
```json
{
  "param1": "value1",
  "param2": 123
}
```

**Esecuzione:**
```bash
python execution/script_name.py --param1="value1" --param2=123
```

**Output:**
```json
{
  "status": "success",
  "data": {...}
}
```

**Risultato:** Descrizione del risultato

---

### Esempio 2: [Descrizione Caso d'Uso 2]

**Contesto:** Descrizione del contesto

**Input:**
```json
{
  "param1": "value2",
  "param2": 456,
  "param3": true
}
```

**Esecuzione:**
```bash
python execution/script_name.py --param1="value2" --param2=456 --param3
```

**Output:**
```json
{
  "status": "success",
  "data": {...}
}
```

**Risultato:** Descrizione del risultato

---

### Esempio 3: [Descrizione Caso d'Uso 3 - Errore]

**Contesto:** Descrizione del contesto (caso di errore)

**Input:**
```json
{
  "param1": "invalid_value",
  "param2": -1
}
```

**Esecuzione:**
```bash
python execution/script_name.py --param1="invalid_value" --param2=-1
```

**Output:**
```json
{
  "status": "error",
  "reason": "Invalid param2: must be positive",
  "code": "INVALID_PARAM"
}
```

**Azione:** Validare param2 prima di chiamare lo script

---

## 🔗 Dipendenze

### Script

- `execution/script_name.py` — Script principale

### Variabili d'Ambiente

- `ENV_VAR_1` — Descrizione variabile 1
- `ENV_VAR_2` — Descrizione variabile 2

### Servizi Esterni

- **Servizio 1** — Descrizione e link documentazione
- **Servizio 2** — Descrizione e link documentazione

---

## 📝 Note

- **Nota 1:** Informazione importante da ricordare
- **Nota 2:** Altra informazione importante
- **Nota 3:** Limitazioni note

---

## 🔄 Changelog

### v1.0.0 — 2025-01-XX

- Creazione direttiva iniziale

---

**Versione:** 1.0.0  
**Autore:** [Nome]  
**Ultima modifica:** 2025-01-XX
