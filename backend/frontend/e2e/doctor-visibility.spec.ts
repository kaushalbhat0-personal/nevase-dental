import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

type Creds = {
  doctorEmail: string;
  doctorPassword: string;
  doctorDisplayName: string;
  doctorBDisplayName: string;
  patientOnlyDoctorBName: string;
};

function loadCreds(): Creds {
  const p = path.join(__dirname, '.e2e-credentials.json');
  const raw = fs.readFileSync(p, 'utf-8');
  return JSON.parse(raw) as Creds;
}

test.describe('Doctor RBAC visibility', () => {
  test('tenant directory, scoped appointments and patients', async ({ page }) => {
    const c = loadCreds();
    await page.goto('/login');
    await page.locator('input[type="email"]').fill(c.doctorEmail);
    await page.locator('input[type="password"]').first().fill(c.doctorPassword);
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/doctor\/home/, { timeout: 25_000 });

    const apptList = page.waitForResponse(
      (r) =>
        r.url().includes('/appointments') &&
        r.request().method() === 'GET' &&
        r.status() === 200
    );
    await page.getByRole('link', { name: 'Appointments', exact: true }).click();
    await apptList;
    await expect(page.getByRole('heading', { name: 'Appointments' })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText('11:30')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText('11:00')).not.toBeVisible();

    await page.getByRole('link', { name: 'Patients', exact: true }).click();
    await expect(page).toHaveURL(/\/doctor\/patients/, { timeout: 15_000 });
    await expect(page.getByRole('heading', { name: 'Patients' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('E2E Patient')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(c.patientOnlyDoctorBName)).toHaveCount(0);

    await page.getByRole('link', { name: 'Doctors', exact: true }).click();
    await expect(page).toHaveURL(/\/doctor\/doctors/, { timeout: 15_000 });
    await expect(page.getByRole('heading', { name: 'Doctors' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(c.doctorDisplayName).first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(c.doctorBDisplayName).first()).toBeVisible();
  });
});
