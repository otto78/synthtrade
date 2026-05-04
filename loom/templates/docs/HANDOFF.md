# Handoff Protocol — [NOME_PROGETTO]

Questo file documenta il passaggio di consegne tra agenti AI o tra sessioni di lavoro.

## 📋 Regola d'oro

**Aggiorna questo file ogni volta che passi il lavoro a un altro agente o termini una sessione importante.**

---

## 🔄 Ultimo Handoff

### Da: [AGENTE_USCENTE] → A: [AGENTE_ENTRANTE]

**Data:** 2025-01-15 14:30

**Contesto:** Breve descrizione del contesto attuale

---

### 📊 Stato Attuale

**Task in corso:** TASK-001 — Descrizione task

**Progresso:** 60% completato

**Ultimo commit:** `abc1234` — "feat: implementato X"

**Branch:** `feature/task-001`

---

### 📁 File Modificati

File su cui si sta lavorando:

- `src/module1.py` — Implementazione feature X (80% completo)
- `tests/test_module1.py` — Test per feature X (50% completo)
- `docs/api.md` — Documentazione API (da aggiornare)

File da NON modificare (altri agenti ci stanno lavorando):

- `src/module2.py` — In lavorazione da [ALTRO_AGENTE]

---

### 🎯 Prossimi Step

1. **Step 1** — Completare implementazione funzione `process_data()`
   - File: `src/module1.py` linea 45
   - Riferimento: Vedi direttiva `directives/data-processing.md`
   - Stima: 1 ora

2. **Step 2** — Aggiungere test per edge cases
   - File: `tests/test_module1.py`
   - Casi da testare: input vuoto, input malformato, timeout
   - Stima: 30 minuti

3. **Step 3** — Aggiornare documentazione
   - File: `docs/api.md`
   - Aggiungere esempi d'uso
   - Stima: 15 minuti

---

### 🚧 Blocchi e Problemi

**Blocco 1:** API esterna non risponde

- **Descrizione:** L'API di terze parti ritorna 503
- **Workaround temporaneo:** Usare mock nei test
- **Azione necessaria:** Contattare supporto API
- **Urgenza:** Media

**Problema 1:** Test fallisce su Windows

- **Descrizione:** `test_file_path()` fallisce per path separator
- **Causa:** Hardcoded `/` invece di `os.path.sep`
- **Fix proposto:** Usare `pathlib.Path`
- **Urgenza:** Bassa

---

### 💡 Decisioni Prese

**Decisione 1:** Usare PostgreSQL invece di MySQL

- **Data:** 2025-01-15
- **Motivazione:** Migliore supporto JSON e performance
- **Impatto:** Modificare script di setup DB
- **Documentato in:** `docs/STORY.md`

**Decisione 2:** Rimandare feature Y a v0.2.0

- **Data:** 2025-01-15
- **Motivazione:** Troppo complessa per MVP
- **Impatto:** Spostata in BACKLOG.md
- **Approvato da:** [NOME]

---

### 📝 Note Importanti

- **Nota 1:** Il test suite richiede 5 minuti per eseguire (API calls reali)
- **Nota 2:** Credenziali di test in `.env.test` (non committare!)
- **Nota 3:** Deploy automatico su push a `main` (CI/CD attivo)

---

### 🔗 Riferimenti Utili

- **Direttiva principale:** `directives/feature-x.md`
- **Issue GitHub:** #123
- **Documentazione API:** https://api.example.com/docs
- **Slack thread:** [Link]

---

## 📚 Storico Handoff

### 2025-01-14 — [AGENTE_1] → [AGENTE_2]

**Contesto:** Completato setup iniziale

**Risultato:** Task TASK-000 completato, progetto inizializzato

---

### 2025-01-13 — [AGENTE_0] → [AGENTE_1]

**Contesto:** Primo setup progetto

**Risultato:** Repository creato, framework installato

---

## 🔄 Workflow Handoff

### Agente Uscente

1. Completa il commit corrente (se possibile)
2. Aggiorna `docs/TASKS.md` con stato dettagliato
3. Compila questo file con tutte le informazioni
4. Push su repository
5. Notifica agente entrante (se necessario)

### Agente Entrante

1. Pull ultime modifiche
2. Leggi `docs/TASKS.md` per contesto generale
3. Leggi questo file per dettagli specifici
4. Verifica file modificati e prossimi step
5. Chiedi chiarimenti se necessario
6. Inizia a lavorare

---

**Ultima modifica:** [DATA] da [AGENTE]
