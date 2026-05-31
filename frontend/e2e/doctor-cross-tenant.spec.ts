import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

type Creds = {
  doctorEmail: string;
  doctorPassword: string;
  doctorOtherTenantDisplayName: string;
};

function loadCreds(): Creds {
  const p = path.join(__dirname, '.e2e-credentials.json');
  const raw = fs.readFileSync(p, 'utf-8');
  return JSON.parse(raw) as Creds;
}

test.describe('Doctor cross-tenant isolation', () => {
  test('tenant A doctor directory does not list other-tenant doctor', async ({ page }) => {
    const c = loadCreds();
    await page.goto('/login');
    await page.locator('input[type="email"]').fill(c.doctorEmail);
    await page.locator('input[type="password"]').first().fill(c.doctorPassword);
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/doctor\/home/, { timeout: 25_000 });

    const doctorsList = page.waitForResponse(
      (r) => r.url().includes('/api/v1/doctors') && r.status() === 200
    );
    await page.getByRole('link', { name: 'Doctors', exact: true }).click();
    await doctorsList;
    await expect(page).toHaveURL(/\/doctor\/doctors/, { timeout: 15_000 });
    await expect(page.getByRole('heading', { name: 'Doctors' })).toBeVisible({ timeout: 15_000 });

    await expect(page.getByText(c.doctorOtherTenantDisplayName)).toHaveCount(0);
  });
});
