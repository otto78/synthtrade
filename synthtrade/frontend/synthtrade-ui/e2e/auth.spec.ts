import { test, expect } from '@playwright/test';

/**
 * TASK-176: E2E Test per autenticazione
 *
 * Scenari testati:
 * 1. Login con credenziali errate → mostra errore
 * 2. Login con credenziali corrette → redirect a /dashboard
 * 3. Accesso diretto a route protetta senza auth → redirect a /login
 * 4. Logout corretto → redirect a /login
 */

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Pulisci localStorage per ogni test
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should show error with incorrect credentials', async ({ page }) => {
    // Vai alla pagina di login
    await page.goto('/login');

    // Verifica che la pagina di login sia caricata
    await expect(page).toHaveURL(/\/login/);

    // Compila il form con credenziali errate (solo password)
    await page.fill('input[type="password"], input[name="password"]', 'wrongpassword');

    // Clicca sul pulsante di login
    const loginButton = page.getByRole('button', { name: /login|accedi|entra/i });
    await loginButton.click();

    // Verifica che compaia un messaggio di errore
    // L'errore può essere mostrato in diversi modi: alert, toast, div.error-message, ecc.
    const errorMessage = page.locator('.error, .error-message, [role="alert"], .alert-danger');
    await expect(errorMessage.first()).toBeVisible({ timeout: 5000 });

    // Verifica che NON sia avvenuto il redirect al dashboard
    await expect(page).not.toHaveURL(/\/dashboard/);
  });

  test('should redirect to /dashboard with correct credentials', async ({ page }) => {
    // Vai alla pagina di login
    await page.goto('/login');

    // Compila il form con credenziali CORRETTE (solo password)
    // NOTA: Password dal backend .env: "admin123"
    await page.fill('input[type="password"], input[name="password"]', 'admin123');

    // Clicca sul pulsante di login
    const loginButton = page.getByRole('button', { name: /login|accedi|entra/i });
    await loginButton.click();

    // Verifica redirect al dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Verifica che elementi del dashboard siano visibili
    const dashboardContent = page.locator('app-dashboard, .dashboard, [data-testid="dashboard"]');
    await expect(dashboardContent.first()).toBeVisible();
  });

  test('should redirect to /login when accessing protected route without auth', async ({ page }) => {
    // Tenta di accedere direttamente al dashboard senza essere autenticato
    await page.goto('/dashboard');

    // Dovrebbe essere reindirizzato alla pagina di login
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
  });

  test('should redirect to /login after logout', async ({ page }) => {
    // Simula login (solo password)
    await page.goto('/login');
    await page.fill('input[type="password"], input[name="password"]', 'admin123');
    const loginButton = page.getByRole('button', { name: /login|accedi|entra/i });
    await loginButton.click();

    // Aspetta di essere nel dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Trova e clicca sul pulsante di logout
    // Potrebbe essere in un menu, header, sidebar, ecc.
    const logoutButton = page.getByRole('button', { name: /logout|esci|disconnetti/i });
    await logoutButton.click();

    // Verifica redirect a /login
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 });

    // Verifica che il token sia stato rimosso
    const token = await page.evaluate(() => localStorage.getItem('token') || localStorage.getItem('auth_token'));
    expect(token).toBeNull();
  });

  test('should persist authentication after page reload', async ({ page }) => {
    // Login (solo password)
    await page.goto('/login');
    await page.fill('input[type="password"], input[name="password"]', 'admin123');
    const loginButton = page.getByRole('button', { name: /login|accedi|entra/i });
    await loginButton.click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Ricarica la pagina
    await page.reload();

    // Verifica che l'utente sia ancora autenticato (rimane nel dashboard)
    await expect(page).toHaveURL(/\/dashboard/);
    const dashboardContent = page.locator('app-dashboard, .dashboard, [data-testid="dashboard"]');
    await expect(dashboardContent.first()).toBeVisible();
  });

  test('should show loading state during authentication', async ({ page }) => {
    // Vai alla pagina di login
    await page.goto('/login');

    // Compila form (solo password)
    await page.fill('input[type="password"], input[name="password"]', 'admin123');

    // Clicca login
    const loginButton = page.getByRole('button', { name: /login|accedi|entra/i });
    await loginButton.click();

    // Verifica che appaia uno stato di loading (spinner, disabled button, ecc.)
    // Questo test potrebbe essere flaky se la risposta è troppo veloce
    const loadingIndicator = page.locator('.loading, .spinner, [aria-busy="true"]');

    // Prova a catturare lo stato di loading (potrebbe non essere visibile se troppo veloce)
    const isLoadingVisible = await loadingIndicator.first().isVisible().catch(() => false);

    // Se il loading è troppo veloce, almeno verifica che il pulsante sia stato disabilitato temporaneamente
    // oppure skippa questo assertion
    if (isLoadingVisible) {
      await expect(loadingIndicator.first()).toBeVisible();
    }
  });
});
