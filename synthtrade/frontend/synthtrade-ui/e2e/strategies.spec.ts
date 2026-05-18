import { test, expect } from '@playwright/test';

test('loads in‑progress strategies page', async ({ page }) => {
  // Vai alla home (presupponendo che la home reindirizzi o abbia link)
  await page.goto('/');

  // Trova il bottone/tab per le strategie in corso (assumendo che sia presente)
  const tab = page.getByRole('button', { name: /In Corso/i });
  await expect(tab).toBeVisible();
  await tab.click();

  // Verifica che la pagina delle strategie sia caricata
  await expect(page).toHaveURL(/strategies/);
  // Controlla che la sezione "Strategie Candidate" o una lista sia presente
  const heading = page.getByRole('heading', { name: /Strategie Candidate/i });
  await expect(heading).toBeVisible();
});
