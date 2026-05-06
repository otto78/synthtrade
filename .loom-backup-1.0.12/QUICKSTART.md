# ⚡ LOOM — Quick Start

> **5-minute setup guide**  
> **Guida di avvio rapido (5 minuti)**

---

## 🇬🇧 EN — English

### What You'll Need

- Any IDE (Windsurf, Cursor, Claude Code, VS Code, IntelliJ, loom, VS Code Insider)
- A project folder (new or existing)
- 2 minutes of your time

### Method 1: Quick Download (Easiest) 🚀

The fastest way to get started:

1. **Download** LOOM framework: [Get latest ZIP](https://github.com/otto78/loom-framework/releases/latest/download/loom-framework-latest.zip)
2. **Extract** the ZIP to your project folder
3. **Create PROJECT.md** (or let LOOM auto-detect)
4. **Open any IDE** and say: **"read loom"**
5. **Done!** LOOM auto-configures everything

That's it. LOOM handles the rest.

### Method 2: Clone from GitHub

```bash
# 1. Clone LOOM framework
git clone https://github.com/otto78/loom-framework.git
cd loom

# 2. Copy loom/ folder to your project
cp -r loom/ /path/to/your-project/

# 3. Add PROJECT.md to your project root
# See examples in docs/PROJECT-MD-GUIDE.md

# 4. Tell your IDE agent: "read loom"
```

### Method 3: One-Liner Install (Advanced)

**Windows (PowerShell)**:
```powershell
irm https://raw.githubusercontent.com/otto78/loom-framework/main/install.ps1 | iex
```

**Unix/Linux/macOS**:
```bash
curl -fsSL https://raw.githubusercontent.com/otto78/loom-framework/main/install.sh | bash
```

### What Gets Created in Your Project

After saying **"read loom"**, LOOM creates:

```
your-project/
├── PROJECT.md                # ⭐ Your project context (YOU create this)
├── loom/                     # Framework folder (from ZIP or clone)
├── LOOM.md                   # Framework config (auto-created)
├── AGENT.md                  # Project context for agents (auto-created)
├── CLAUDE.md                 # IDE config — Claude Code
├── GEMINI.md                 # IDE config — Antigravity
├── AGENTS.md                 # Cross-tool (Antigravity + Windsurf + VS Code)
├── .cursorrules              # Cursor (legacy fallback)
├── .cursor/rules/loom.mdc   # Cursor (modern)
├── .windsurfrules            # Windsurf (legacy fallback)
├── .windsurf/rules/loom.md  # Windsurf (modern)
├── .github/copilot-instructions.md  # VS Code / VS Code Insider
├── .aiassistant/rules/loom.md       # IntelliJ AI Assistant
└── docs/
    ├── TASKS.md              # ⭐ Active task tracking
    ├── BACKLOG.md            # Future ideas
    ├── STORY.md              # Operational history (auto-updated)
    ├── CHANGELOG.md          # Version changelog (auto-updated)
    └── HANDOFF.md            # Agent handoff protocol
```

### Next Steps

1. **Create PROJECT.md** — Describe your project
   - See template: `loom/templates/PROJECT.md.template`
   - See examples: `docs/PROJECT-MD-GUIDE.md`
   
2. **Tell agent**: `"read loom"` or `"setup loom"`
   
3. **Agent auto-configures** everything for your project

4. **Start task**: `"start task TASK-001 'implement feature X'"`

5. **Work with confidence** — agent follows YOUR rules from PROJECT.md

### Quick Commands

After setup, you can tell your agent:

```
"read loom"                    → Re-load framework context
"start task TASK-001 'title'" → Create new task
"list tasks"                   → Show active tasks
"complete task TASK-001"       → Mark task done (updates STORY.md)
"handoff to cursor"            → Switch IDE, keep context
"run tests"                    → Execute tests
"sync configs"                 → Update all IDE configs
```

### Need Help?

- **Setup help**: See `SETUP-INSTRUCTIONS.md`
- **Full docs**: See `README.md`
- **Natural language commands**: See `NATURAL-LANGUAGE-GUIDE.md`
- **TDD workflow**: See `TDD-WORKFLOW.md`
- **Using in monorepos**: See `MONOREPO-GUIDE.md`

---

## 🇮🇹 IT — Italiano

### Cosa Ti Serve

- Qualsiasi IDE (Windsurf, Cursor, Claude Code, VS Code, IntelliJ, loom, VS Code Insider)
- Una cartella di progetto (nuova o esistente)
- 2 minuti del tuo tempo

### Metodo 1: Download Rapido (Più Facile) 🚀

Il modo più veloce per iniziare:

1. **Scarica** framework LOOM: [Ottieni ultimo ZIP](https://github.com/otto78/loom-framework/releases/latest/download/loom-framework-latest.zip)
2. **Estrai** lo ZIP nella cartella del tuo progetto
3. **Crea PROJECT.md** (oppure lascia che LOOM lo rilevi automaticamente)
4. **Apri qualsiasi IDE** e di': **"leggi loom"**
5. **Fatto!** LOOM auto-configura tutto

Tutto qui. LOOM gestisce il resto.

### Metodo 2: Clone da GitHub

```bash
# 1. Clone repository LOOM
git clone https://github.com/otto78/loom-framework.git
cd loom

# 2. Copia cartella loom/ nel tuo progetto
cp -r loom/ /path/to/your-project/

# 3. Aggiungi PROJECT.md nella root del tuo progetto
# Vedi esempi in docs/PROJECT-MD-GUIDE.md

# 4. Di' al tuo agente IDE: "leggi loom"
```

### Metodo 3: Install One-Liner (Avanzato)

**Windows (PowerShell)**:
```powershell
irm https://raw.githubusercontent.com/otto78/loom-framework/main/install.ps1 | iex
```

**Unix/Linux/macOS**:
```bash
curl -fsSL https://raw.githubusercontent.com/otto78/loom-framework/main/install.sh | bash
```

### Cosa Viene Creato Nel Tuo Progetto

Dopo aver detto **"leggi loom"**, LOOM crea:

```
tuo-progetto/
├── PROJECT.md                # ⭐ Contesto del tuo progetto (TU lo crei)
├── loom/                     # Cartella framework (da ZIP o clone)
├── LOOM.md                   # Config framework (auto-creato)
├── AGENT.md                  # Contesto progetto per agenti (auto-creato)
├── CLAUDE.md                 # Config IDE — Claude Code
├── GEMINI.md                 # Config IDE — Antigravity
├── AGENTS.md                 # Cross-tool (Antigravity + Windsurf + VS Code)
├── .cursorrules              # Cursor (fallback legacy)
├── .cursor/rules/loom.mdc   # Cursor (moderno)
├── .windsurfrules            # Windsurf (fallback legacy)
├── .windsurf/rules/loom.md  # Windsurf (moderno)
├── .github/copilot-instructions.md  # VS Code / VS Code Insider
├── .aiassistant/rules/loom.md       # IntelliJ AI Assistant
└── docs/
    ├── TASKS.md              # ⭐ Tracciamento task attivi
    ├── BACKLOG.md            # Idee future
    ├── STORY.md              # Storia operativa (auto-aggiornato)
    ├── CHANGELOG.md          # Changelog versione (auto-aggiornato)
    └── HANDOFF.md            # Protocollo handoff agenti
```

### Prossimi Passi

1. **Crea PROJECT.md** — Descrivi il tuo progetto
   - Vedi template: `loom/templates/PROJECT.md.template`
   - Vedi esempi: `docs/PROJECT-MD-GUIDE.md`
   
2. **Di' all'agente**: `"leggi loom"` oppure `"configura loom"`
   
3. **Agente auto-configura** tutto per il tuo progetto

4. **Inizia task**: `"avvia task TASK-001 'implementa feature X'"`

5. **Lavora con fiducia** — agente segue le TUE regole da PROJECT.md

### Comandi Rapidi

Dopo il setup, puoi dire al tuo agente:

```
"leggi loom"                   → Ricarica contesto framework
"avvia task TASK-001 'titolo'" → Crea nuovo task
"mostra i task"                → Mostra task attivi
"completa task TASK-001"       → Segna task come completato (aggiorna STORY.md)
"handoff a cursor"             → Cambia IDE, mantieni contesto
"esegui test"                  → Esegui test suite
"sincronizza config"           → Aggiorna tutte le config IDE
```

### Hai Bisogno di Aiuto?

- **Aiuto setup**: Vedi `SETUP-INSTRUCTIONS.md`
- **Documentazione completa**: Vedi `README.md`
- **Comandi linguaggio naturale**: Vedi `NATURAL-LANGUAGE-GUIDE.md`
- **Workflow TDD**: Vedi `TDD-WORKFLOW.md`
- **Usare in monorepo**: Vedi `MONOREPO-GUIDE.md`

---

## 🎯 Next: Create PROJECT.md

**This is the most important step!**

Before saying "read loom", create `PROJECT.md` in your project root:

```markdown
# My Project Name

## Goal
[What does your project do? 2-3 sentences]

## Stack
- Backend: [Your backend]
- Frontend: [Your frontend or N/A]
- Database: [Your DB]
- [Other tech]

## Architecture
- [Key decision 1]
- [Key decision 2]

## Rules
- [Rule 1 - agent MUST follow this]
- [Rule 2]

## Notes
- [Constraint 1]
- [Constraint 2]
```

See `docs/PROJECT-MD-GUIDE.md` for detailed examples and guidance.

---

**Ready to start? Download the ZIP, create PROJECT.md, and tell your agent: "read loom"!** 🧵
