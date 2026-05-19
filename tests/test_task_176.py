"""
TASK-176: E2E auth.spec.ts (login errato → errore; login corretto → /dashboard)
TDD Documentation

Requirements:
- E2E test per autenticazione con Playwright
- Test login con credenziali errate → mostra errore
- Test login con credenziali corrette → redirect a /dashboard
- Test accesso a route protetta senza auth → redirect a /login
- Test logout → redirect a /login e token rimosso
- Test persistenza autenticazione dopo reload
- Test loading state durante autenticazione

Implementation:
- File: synthtrade/frontend/synthtrade-ui/e2e/auth.spec.ts
- 6 test scenarios implementati
- Password di test: "testpass" (dal backend config)
- Auth usa solo password (no email)

Notes:
- I test E2E richiedono backend in esecuzione su http://localhost:8008
- Frontend deve essere servito su http://localhost:4208
- Playwright usa Chromium headless per default

Test Execution:
Per eseguire i test:
1. Avvia backend: cd synthtrade/backend && uvicorn app.main:app --port 8008
2. Avvia frontend: cd synthtrade/frontend/synthtrade-ui && npm start
3. Run E2E: cd synthtrade/frontend/synthtrade-ui && npx playwright test e2e/auth.spec.ts

Status: ✅ Completato (TDD Green)
"""

# Questo file documenta che TASK-176 è stato completato con test E2E
# I test effettivi sono in: synthtrade/frontend/synthtrade-ui/e2e/auth.spec.ts
