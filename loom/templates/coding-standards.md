# Coding Standards — loom

> Letto da tutti gli agenti AI prima di scrivere qualsiasi codice.
> Questi standard si applicano a tutto il codebase.

---

## Principi Generali

1. **Il codice è scritto per essere letto da umani**, non solo eseguito da macchine.
2. **Ogni file deve essere comprensibile senza contesto esterno** — chi lo apre per la prima volta capisce cosa fa in 30 secondi.
3. **Nessuna magia implicita** — se qualcosa non è ovvio, spiegalo con un commento.
4. **Fail loud, fail early** — errori espliciti e gestione chiara delle eccezioni.
5. **English First per il codice** — Tutti i nomi di variabili, le costanti, i metodi e **i commenti** nel codice DEVONO essere scritti in inglese. Altre lingue sono consentite **esclusivamente** per i testi rivolti all'utente (es. messaggi UI).

---

## Python

### Struttura file

Ogni file Python inizia con un header descrittivo:

```python
"""
nome_file.py
------------
Breve descrizione di cosa fa questo modulo (1-2 righe).

Responsabilità:
- cosa fa
- cosa non fa (se non è ovvio)

Dipendenze chiave: libreria_a, libreria_b
"""
```

### Type hints — sempre, ovunque

```python
# ✅ Corretto
def send_message(to: str, text: str, delay: float = 0.3) -> bool:
    ...

async def process_data(file_path: str) -> str:
    ...

# ❌ Vietato
def send_message(to, text, delay=0.3):
    ...
```

### Docstring per ogni funzione pubblica

```python
def split_text(text: str, max_chars: int = 400) -> list[str]:
    """
    Spezza il testo in chunk rispettando i confini naturali delle frasi.

    Priorità di splitting: fine frase (. ! ?) > spazio > hard cut.
    Non taglia mai a metà parola.

    Args:
        text: Il testo da dividere.
        max_chars: Lunghezza massima di ogni chunk (default 400).

    Returns:
        Lista di stringhe, ciascuna <= max_chars caratteri.

    Example:
        >>> split_text("Hello. How are you?", max_chars=10)
        ['Hello.', 'How are you?']
    """
```

### Commenti inline — solo quando necessario

```python
# ✅ Commento utile: spiega il perché, non il cosa
# API doesn't accept messages > 4096 chars, use 400 for mobile readability
MAX_CHUNK_CHARS = 400

# ✅ Commento utile: segnala un workaround o una limitazione esterna
# Library requires file in /tmp — doesn't support direct streams
file_path = f"/tmp/{file_id}.dat"

# ❌ Commento inutile: descrive solo il codice già leggibile
# Increment counter
counter += 1
```

### Costanti — sempre in maiuscolo, in cima al file, con commento

```python
# Maximum chunk length for mobile readability
MAX_CHUNK_CHARS = 400

# Pause between multiple chunks (seconds) — simulates human typing
CHUNK_DELAY = 0.4

# Initial delay before responding — avoids unnatural instant response
TYPING_DELAY_BASE = 0.3
```

### Gestione errori — esplicita e loggata

```python
# ✅ Corretto
async def process_file(file_path: str) -> str:
    """Process file. Returns empty string on error."""
    try:
        with open(file_path, "rb") as f:
            result = process(f)
        return result.strip()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return ""
    except Exception as e:
        logger.exception(f"Processing error for {file_path}: {e}")
        return ""

# ❌ Vietato
async def process_file(file_path):
    result = process(file_path)
    return result
```

### Naming conventions

| Tipo | Convenzione | Esempio |
|------|-------------|---------|
| Funzioni e variabili | snake_case | `send_message`, `user_id` |
| Classi | PascalCase | `SessionManager`, `DataService` |
| Costanti | UPPER_SNAKE_CASE | `MAX_CHUNK_CHARS` |
| Variabili private | underscore prefix | `_headers()`, `_safe_call()` |
| File | snake_case | `data_processor.py` |

### Struttura sezioni con separatori visivi

Per file lunghi, usa separatori chiari tra le sezioni logiche:

```python
# ─────────────────────────────────────────────
# SESSIONS
# ─────────────────────────────────────────────

def get_or_create_session(user_id: str) -> dict:
    ...


# ─────────────────────────────────────────────
# DATA PROCESSING
# ─────────────────────────────────────────────

def process_data(session: dict, data: str) -> str:
    ...
```

### Lunghezza funzioni
- Max ~40 righe per funzione. Se è più lunga, spezzala.
- Una funzione = una responsabilità.

---

## TypeScript / JavaScript

### Struttura file

```typescript
/**
 * component.ts
 * ------------
 * Brief description of what this component does.
 * Handles X, Y, Z.
 *
 * Does NOT handle: authentication (→ AuthService), API calls (→ DataService)
 */
```

### Interfacce — sempre tipizzate, mai `any`

```typescript
// ✅ Corretto
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status: 'sending' | 'delivered' | 'error';
}

// ❌ Vietato
const message: any = { ... };
```

### Commenti JSDoc per metodi pubblici

```typescript
/**
 * Send a message and update local session.
 *
 * @param text - Message text
 * @param sessionId - Current session ID
 * @returns Observable with response
 * @throws {HttpErrorResponse} if gateway is unreachable
 */
sendMessage(text: string, sessionId: string): Observable<Response> {
  ...
}
```

### Naming conventions TypeScript

| Tipo | Convenzione | Esempio |
|------|-------------|---------|
| Variabili e funzioni | camelCase | `sendMessage`, `userId` |
| Classi e interfacce | PascalCase | `DataService`, `Response` |
| Costanti | UPPER_SNAKE_CASE o camelCase const | `MAX_RETRIES` |
| File | kebab-case | `data-service.ts` |
| Enum | PascalCase | `Status` |

### Gestione errori

```typescript
// ✅ Corretto — errore gestito e loggato
sendMessage(text: string): Observable<Response> {
  return this.http.post<Response>('/api/message', { text }).pipe(
    catchError((error: HttpErrorResponse) => {
      console.error('Send message error:', error.message);
      return throwError(() => new Error('Cannot contact service. Retry.'));
    })
  );
}
```

---

## Regole Trasversali

### Mai hardcodare valori di configurazione

```python
# ✅
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))

# ❌
if len(session["history"]) > 20:
```

```typescript
// ✅
const apiUrl = environment.apiUrl;

// ❌
const apiUrl = "https://api.example.com";
```

### Logging strutturato (Python)

```python
# ✅ — include contesto
logger.info(f"Session created for user_id={user_id}")
logger.error(f"Processing failed for file_id={file_id}: {e}")
logger.warning(f"Chunk > {MAX_CHUNK_CHARS} chars, forced split")

# ❌ — nessun contesto
logger.info("Session created")
logger.error("Error")
```

### Sicurezza — regole non negoziabili

1. **Mai loggare credenziali, token o dati personali** — usa `[REDACTED]` se devi loggare una struttura che li contiene
2. **Mai passare credenziali in query string** — sempre header o body cifrato
3. **Mai committare file `.env`** — sempre in `.gitignore`
4. **Dati utente in log solo con ID anonimizzato** — `user_id` sì, nome/email no

### Struttura commit message

```
tipo(scope): descrizione breve

Esempi:
feat(api): add audio message handling
fix(processor): fix timeout error on large files
refactor(sessions): separate onboarding logic to dedicated module
docs(directives): update API integration directive
```

Tipi validi: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

---

## Checklist Prima di Consegnare Codice

- [ ] Ogni funzione pubblica ha docstring / JSDoc
- [ ] Type hints presenti in tutto il codice Python
- [ ] Interfacce TypeScript definite, nessun `any`
- [ ] Costanti in maiuscolo con commento esplicativo
- [ ] Gestione errori esplicita con log contestuale
- [ ] Nessuna credenziale o dato sensibile loggato
- [ ] Nessun valore hardcodato che dovrebbe stare in `.env`
- [ ] Il file è comprensibile senza contesto esterno (header descrittivo presente)

---

## Git Operations — Regole per Windows/PowerShell

> **ATTENZIONE**: In PowerShell (Windows PowerShell 5.1), `&&` **NON FUNZIONA**.
> `&&` è supportato solo in PowerShell 7+ (Core) e in Bash/Unix shell.

### Opzioni per comandi multipli

**1. Comandi separati (raccomandato per automazione)**
```powershell
# ❌ NON usare — fallisce in PowerShell 5.1
git add file.txt && git commit -m "fix" && git push

# ✅ Usa comandi separati — ognuno verificato singolarmente
git add file.txt
git commit -m "fix"
git push
```

**2. Usare WSL/Bash se disponibile**
```bash
# Se WSL è installato, puoi usare bash esplicitamente
bash -c "git add file.txt && git commit -m 'fix' && git push"
```

**3. PowerShell alternativa con `;`**
```powershell
# `;` esegue in sequenza MA ignora errori — non si ferma se uno fallisce
git add file.txt; git commit -m "fix"; git push
```

### Strategia per agenti AI

Quando esegui git operations su Windows:
1. **Preferisci comandi singoli** — più facili da debuggare
2. **Verifica l'exit code** dopo ogni comando se possibile
3. **Non assumere** che `&&` funzioni — controlla lo shell attivo

---

## Deploy Operations

### Post-Deploy Check (OBBLIGATORIO)

**Dopo OGNI deploy, l'agente DEVE:**

1. **Verificare lo stato del servizio** su dashboard o via API
2. **Controllare i log** per errori di startup (import errors, config errors, ecc.)
3. **Testare l'app è online**:
   - Verificare che l'endpoint principale risponda (HTTP 200)
   - Verificare che i servizi siano attivi
4. **Se ci sono problemi**:
   - Fixare immediatamente se è un errore semplice (import order, typo, ecc.)
   - Chiedere all'utente se è troppo complesso per intervento rapido
5. **Aggiornare il changelog** con eventuali hotfix

**Checklist post-deploy:**
- [ ] Servizio "Live" (non "Deploy Failed")
- [ ] Log di startup senza errori
- [ ] Endpoint `/health` o principale risponde
- [ ] Nessun `NameError`, `ImportError`, `SyntaxError` nei log

---

**Versione:** 1.0.0  
**Framework:** loom v1.0
