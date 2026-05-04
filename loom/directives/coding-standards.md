# Coding Standards — loom

> Letto da tutti gli agenti AI prima di scrivere qualsiasi codice.
> Questi standard si applicano a tutto il codebase.

---

**NOTA:** Questo file è una copia di `loom/templates/coding-standards.md` per comodità.
La fonte di verità è `loom/templates/coding-standards.md`.

Per il contenuto completo, vedi: [templates/coding-standards.md](../templates/coding-standards.md)

---

## Quick Reference

### Python
- Type hints sempre
- Docstring per funzioni pubbliche
- snake_case per funzioni/variabili
- PascalCase per classi
- UPPER_SNAKE_CASE per costanti

### TypeScript/JavaScript
- Interfacce sempre, mai `any`
- JSDoc per metodi pubblici
- camelCase per funzioni/variabili
- PascalCase per classi/interfacce
- kebab-case per file

### Generale
- Commenti solo quando necessario (spiega il perché, non il cosa)
- Gestione errori esplicita e loggata
- Mai hardcodare configurazioni
- Mai loggare credenziali
- Commit message: `tipo(scope): descrizione`

---

**Per dettagli completi, vedi:** [templates/coding-standards.md](../templates/coding-standards.md)

**Versione:** 1.0.0  
**Framework:** loom v1.0
