import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadCreds() {
  const p = path.join(__dirname, '.e2e-credentials.json');
  const raw = fs.readFileSync(p, 'utf-8');
  return JSON.parse(raw) as {
    resetDoctorEmail: string;
    resetDoctorPassword: string;
    newDoctorPassword: string;
  };
}

test.describe('Doctor portal', () => {
  test('login with forced reset, then set new password', async ({ page }) => {
    const c = loadCreds();
    await page.goto('/login');

    await page.locator('input[type="email"]').fill(c.resetDoctorEmail);
    await page.locator('input[type="password"]').first().fill(c.resetDoctorPassword);
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page).toHaveURL(/\/reset-password/, { timeout: 20_000 });

    await page.getByPlaceholder('Enter your current password').fill(c.resetDoctorPassword);
    await page.getByPlaceholder('At least 8 characters').fill(c.newDoctorPassword);
    await page.getByPlaceholder('Re-enter new password').fill(c.newDoctorPassword);
    await page.getByRole('button', { name: 'Update password' }).click();

    await expect(page).toHaveURL(/\/doctor\/home/, { timeout: 20_000 });
  });
});
