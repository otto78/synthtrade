/**
 * TASK-177: E2E Test per attivazione e disattivazione strategie
 *
 * Scenari testati:
 * 1. Caricamento pagina strategie
 * 2. Navigazione tra tab (GENERAZIONE, APPROVATE, ATTIVE, COMPLETATE)
 * 3. Approvazione strategia PENDING → passa ad APPROVATE
 * 4. Attivazione strategia APPROVED → passa ad ATTIVE
 * 5. Disattivazione strategia ACTIVE → passa a COMPLETATE
 * 6. Verifica P&L real-time su strategia attiva
 */

import { test, expect } from '@playwright/test';

test.describe('Strategies Management E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Pulisci localStorage e fai login
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());

    // Login (solo password)
    await page.goto('/login');
    await page.fill('input[type="password"], input[name="password"]', 'admin123');
    const loginButton = page.getByRole('button', { name: /login|accedi|entra/i });
    await loginButton.click();

    // Aspetta di essere nel dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
  });

  test('should load strategies page and show tabs', async ({ page }) => {
    // Naviga alla pagina strategie
    await page.goto('/strategies');

    // Verifica che la pagina sia caricata
    await expect(page).toHaveURL(/\/strategies/);

    // Verifica che tutti i tab siano visibili
    await expect(page.getByRole('button', { name: /GENERAZIONE/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /APPROVATE/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /ATTIVE/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /COMPLETATE/i })).toBeVisible();
  });

  test('should navigate between tabs', async ({ page }) => {
    await page.goto('/strategies');

    // Click sul tab APPROVATE
    const approvedTab = page.getByRole('button', { name: /APPROVATE/i });
    await approvedTab.click();

    // Verifica che il tab sia attivo (ha classe tab--active)
    await expect(approvedTab).toHaveClass(/tab--active/);

    // Click sul tab ATTIVE
    const activeTab = page.getByRole('button', { name: /ATTIVE/i });
    await activeTab.click();
    await expect(activeTab).toHaveClass(/tab--active/);

    // Click sul tab COMPLETATE
    const completedTab = page.getByRole('button', { name: /COMPLETATE/i });
    await completedTab.click();
    await expect(completedTab).toHaveClass(/tab--active/);
  });

  test('should approve a PENDING strategy and move to APPROVATE', async ({ page }) => {
    await page.goto('/strategies');

    // Verifica che il tab GENERAZIONE sia attivo
    const generationTab = page.getByRole('button', { name: /GENERAZIONE/i });
    await expect(generationTab).toHaveClass(/tab--active/);

    // Cerca una strategia PENDING (card con bottone "Approva")
    const approveButton = page.getByRole('button', { name: /Approva/i }).first();

    // Se esiste una strategia PENDING, approvala
    if (await approveButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await approveButton.click();

      // Aspetta che il tab APPROVATE diventi attivo automaticamente
      await expect(page.getByRole('button', { name: /APPROVATE/i })).toHaveClass(/tab--active/, { timeout: 5000 });

      // Verifica che la strategia sia nella lista APPROVATE
      const startButton = page.getByRole('button', { name: /Avvia Esecuzione/i }).first();
      await expect(startButton).toBeVisible({ timeout: 5000 });
    }
  });

  test('should activate an APPROVED strategy and move to ATTIVE', async ({ page }) => {
    await page.goto('/strategies');

    // Vai al tab APPROVATE
    await page.getByRole('button', { name: /APPROVATE/i }).click();

    // Cerca il bottone "Avvia Esecuzione"
    const startButton = page.getByRole('button', { name: /Avvia Esecuzione/i }).first();

    // Se esiste una strategia APPROVED, attivala
    if (await startButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await startButton.click();

      // Aspetta che il tab ATTIVE diventi attivo automaticamente
      await expect(page.getByRole('button', { name: /ATTIVE/i })).toHaveClass(/tab--active/, { timeout: 5000 });

      // Verifica che la strategia sia nella lista ATTIVE
      const stopButton = page.getByRole('button', { name: /Stop/i }).first();
      await expect(stopButton).toBeVisible({ timeout: 5000 });

      // Verifica che il badge LIVE sia visibile
      const liveBadge = page.locator('.live-badge').first();
      await expect(liveBadge).toBeVisible();
      await expect(liveBadge).toHaveText('LIVE');
    }
  });

  test('should stop an ACTIVE strategy and move to COMPLETATE', async ({ page }) => {
    await page.goto('/strategies');

    // Vai al tab ATTIVE
    await page.getByRole('button', { name: /ATTIVE/i }).click();

    // Cerca il bottone "Stop"
    const stopButton = page.getByRole('button', { name: /Stop/i }).first();

    // Se esiste una strategia ACTIVE, fermala
    if (await stopButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await stopButton.click();

      // Conferma il dialog di stop
      const confirmButton = page.getByRole('button', { name: /conferma|ok|sì|yes/i });
      await confirmButton.click({ timeout: 3000 });

      // Aspetta che la strategia sia spostata (potrebbe richiedere qualche secondo)
      await page.waitForTimeout(2000);

      // Vai al tab COMPLETATE
      await page.getByRole('button', { name: /COMPLETATE/i }).click();

      // Verifica che ci sia almeno una strategia completata
      const completedItem = page.locator('.accordion-item').first();
      await expect(completedItem).toBeVisible({ timeout: 5000 });
    }
  });

  test('should display real-time P&L for ACTIVE strategies', async ({ page }) => {
    await page.goto('/strategies');

    // Vai al tab ATTIVE
    await page.getByRole('button', { name: /ATTIVE/i }).click();

    // Cerca una riga attiva con P&L
    const pnlLabel = page.locator('.pnl-label').first();

    // Se esiste una strategia ACTIVE, verifica che il P&L sia mostrato
    if (await pnlLabel.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(pnlLabel).toBeVisible();
      await expect(pnlLabel).toHaveText('P&L Live');

      // Verifica che il valore P&L sia presente (numero con % o formato percentuale)
      const pnlValue = page.locator('.pnl-value').first();
      await expect(pnlValue).toBeVisible();

      // Il valore deve avere classe positive o negative
      const hasPositiveOrNegativeClass = await pnlValue.evaluate((el) => {
        return el.classList.contains('positive') || el.classList.contains('negative');
      });
      expect(hasPositiveOrNegativeClass).toBe(true);
    }
  });

  test('should show empty state when no strategies in tab', async ({ page }) => {
    await page.goto('/strategies');

    // Vai al tab COMPLETATE (probabilmente vuoto su sistema pulito)
    await page.getByRole('button', { name: /COMPLETATE/i }).click();

    // Verifica che venga mostrato empty state o accordion items
    const emptyState = page.locator('app-empty-state');
    const accordionItems = page.locator('.accordion-item');

    // Almeno uno dei due dovrebbe essere visibile
    const emptyStateVisible = await emptyState.isVisible({ timeout: 2000 }).catch(() => false);
    const accordionVisible = await accordionItems.first().isVisible({ timeout: 2000 }).catch(() => false);

    expect(emptyStateVisible || accordionVisible).toBe(true);
  });

  test('should reject an APPROVED strategy', async ({ page }) => {
    await page.goto('/strategies');

    // Vai al tab APPROVATE
    await page.getByRole('button', { name: /APPROVATE/i }).click();

    // Cerca il bottone "Rifiuta"
    const rejectButton = page.getByRole('button', { name: /Rifiuta/i }).first();

    // Se esiste una strategia APPROVED, rifiutala
    if (await rejectButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Conta le strategie prima del reject
      const countBefore = await page.locator('.strategy-card.approved').count();

      await rejectButton.click();

      // Conferma il dialog di reject
      const confirmButton = page.getByRole('button', { name: /conferma|ok|sì|yes/i });
      await confirmButton.click({ timeout: 3000 });

      // Aspetta che la UI si aggiorni
      await page.waitForTimeout(1000);

      // Verifica che il conteggio sia diminuito
      const countAfter = await page.locator('.strategy-card.approved').count();
      expect(countAfter).toBeLessThan(countBefore);
    }
  });
});
