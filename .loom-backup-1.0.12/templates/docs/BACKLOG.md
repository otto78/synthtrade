# Project Backlog — [NOME_PROGETTO]

Questo file contiene idee, feature future, esperimenti e miglioramenti non ancora strutturati come task.

## 📋 Regola d'oro

**Quando un'idea è matura (requisiti chiari, effort stimato), convertila in task in TASKS.md e rimuovila da qui.**

---

## 🔥 Idee Prioritarie

Idee quasi pronte per diventare task. Servono solo piccoli chiarimenti.

### [IDEA-001] — Titolo Idea

**Descrizione:** Cosa vogliamo fare

**Valore:** Perché è importante

**Requisiti da chiarire:**
- [ ] Requisito 1
- [ ] Requisito 2

**Effort stimato:** 2-4 ore

**Dipendenze:** TASK-XXX deve essere completato prima

---

## 💡 Idee da Esplorare

Idee interessanti ma servono ricerca/validazione prima di procedere.

### [IDEA-002] — Altra Idea

**Descrizione:** Cosa potremmo fare

**Domande aperte:**
- Domanda 1?
- Domanda 2?

**Ricerca necessaria:**
- [ ] Ricerca 1
- [ ] Ricerca 2

---

## 🧪 Esperimenti

Proof of concept senza commitment. Possono fallire.

### [EXP-001] — Esperimento X

**Ipotesi:** Cosa vogliamo testare

**Successo se:** Criteri di successo

**Fallimento se:** Criteri di fallimento

**Tempo massimo:** 2 ore

---

## 🎨 Miglioramenti UX/Performance

Ottimizzazioni future che non bloccano il lavoro corrente.

### [UX-001] — Miglioramento UI

**Problema attuale:** Cosa non va bene

**Soluzione proposta:** Come migliorare

**Impatto:** Alto / Medio / Basso

---

## 🔧 Debito Tecnico

Refactoring, pulizia codice, aggiornamenti dipendenze.

### [TECH-001] — Refactoring Modulo X

**Problema:** Codice duplicato / complesso / obsoleto

**Soluzione:** Come refactorare

**Urgenza:** Alta / Media / Bassa

**Rischio:** Cosa potrebbe rompersi

---

## 🗑️ Idee Scartate

Idee che abbiamo deciso di non implementare (con motivazione).

### [SCARTATA-001] — Idea Scartata

**Motivo:** Perché non la facciamo

**Data decisione:** 2025-01-15

---

## 🔄 Conversione Backlog → Task

Quando un'idea è pronta:

```bash
# 1. Crea task
python scripts/task.py start TASK-XXX "Descrizione"

# 2. Rimuovi idea da questo file

# 3. Commit
git add docs/BACKLOG.md docs/TASKS.md
git commit -m "chore: convert IDEA-XXX to TASK-XXX"
git push
```

---

**Ultima modifica:** [DATA] da [AGENTE]
