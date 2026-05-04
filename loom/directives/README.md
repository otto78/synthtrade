# Directives — Standard Operating Procedures

Questa cartella contiene le SOP (Standard Operating Procedures) del progetto.

---

## 🎯 Cos'è una Direttiva

Una direttiva è un documento Markdown che definisce **cosa** fare per un obiettivo specifico.

**Non è codice** — È una guida in linguaggio naturale per l'agente AI.

---

## 📝 Struttura di una Direttiva

Ogni direttiva deve contenere:

### 1. Titolo e Obiettivo

```markdown
# Direttiva: [Nome Direttiva]

## Obiettivo
[Cosa vogliamo ottenere con questa direttiva]
```

### 2. Input

```markdown
## Input
- `param1` (type) — Descrizione
- `param2` (type, optional) — Descrizione
```

### 3. Tool da Usare

```markdown
## Tool da usare
`execution/script_name.py`

Oppure:
- Step 1: `execution/script1.py`
- Step 2: `execution/script2.py`
```

### 4. Output

```markdown
## Output
- Successo: `{"status": "ok", "data": ...}`
- Fallimento: `{"status": "error", "reason": "..."}`
```

### 5. Casi Limite

```markdown
## Casi limite
1. **Caso 1** → Soluzione
2. **Caso 2** → Soluzione
```

### 6. Esempi

```markdown
## Esempi

### Esempio 1: [Descrizione]
Input: ...
Output: ...

### Esempio 2: [Descrizione]
Input: ...
Output: ...
```

---

## ✅ Esempio Completo

Vedi `_template.md` per un template completo.

---

## 🎓 Best Practices

### 1. Una direttiva = un obiettivo

❌ **Male:**
```markdown
# Direttiva: Gestire utenti e inviare email
```

✅ **Bene:**
```markdown
# Direttiva: Creare nuovo utente
# Direttiva: Inviare email di benvenuto
```

### 2. Linguaggio naturale

Scrivi come parleresti a un collaboratore di medio livello.

❌ **Male:**
```markdown
Esegui query SQL SELECT * FROM users WHERE id = ?
```

✅ **Bene:**
```markdown
Recupera l'utente dal database usando il suo ID.
Usa lo script `execution/get_user.py --user-id=123`
```

### 3. Esempi concreti

Almeno 2-3 casi d'uso reali.

### 4. Casi limite documentati

Errori comuni e come gestirli.

### 5. Riferimenti a script

Quale tool di Livello 3 usare.

---

## 📚 Direttive Speciali

### `coding-standards.md`

Standard di codice del progetto. **Deve essere letto prima di scrivere qualsiasi codice.**

---

## 🔄 Workflow

### Creare una nuova direttiva

1. Copia `_template.md` → `nome-direttiva.md`
2. Compila tutte le sezioni
3. Aggiungi esempi concreti
4. Documenta casi limite
5. Testa con l'agente AI

### Aggiornare una direttiva esistente

1. Leggi la direttiva corrente
2. Identifica cosa manca o è obsoleto
3. Aggiorna la sezione pertinente
4. Aggiungi nota di changelog in fondo
5. Commit con messaggio descrittivo

---

## 📊 Checklist Qualità Direttiva

- [ ] Titolo chiaro e descrittivo
- [ ] Obiettivo ben definito
- [ ] Input completi con tipi
- [ ] Tool/script specificati
- [ ] Output formato definito
- [ ] Almeno 3 casi limite documentati
- [ ] Almeno 2 esempi concreti
- [ ] Linguaggio naturale (non codice)
- [ ] Testata con agente AI

---

## 🎯 Quando Creare una Nuova Direttiva

### ✅ Crea quando

- Hai un obiettivo ripetibile
- Serve documentazione per l'agente
- Ci sono casi limite da gestire
- Vuoi standardizzare un processo

### ❌ Non creare quando

- Task una-tantum
- Troppo semplice (1 comando)
- Già coperto da direttiva esistente

---

**Versione:** 1.0.0  
**Ultima modifica:** 2025-01-XX
