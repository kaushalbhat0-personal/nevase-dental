import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadCreds() {
  const p = path.join(__dirname, '.e2e-credentials.json');
  const raw = fs.readFileSync(p, 'utf-8');
  return JSON.parse(raw) as {
    doctorEmail: string;
    doctorPassword: string;
    doctorLinkedPatientId: string;
  };
}

async function loginAsIndependentDoctor(
  page: import('@playwright/test').Page,
  email: string,
  password: string
) {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/doctor\//, { timeout: 25_000 });
}

test.describe('Patient quick actions (independent doctor)', () => {
  test('Book appointment and Create bill pass patient context into modals', async ({ page }) => {
    const c = loadCreds();
    await loginAsIndependentDoctor(page, c.doctorEmail, c.doctorPassword);

    const patientUrl = `/doctor/patients/${c.doctorLinkedPatientId}`;
    await page.goto(patientUrl);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 20_000 });

    await page.getByRole('button', { name: 'Book appointment' }).click();
    await expect(page).toHaveURL(/\/doctor\/appointments/);

    const firstSlot = page.getByTestId('doctor-schedule-slot').first();
    await expect(firstSlot).toBeVisible({ timeout: 20_000 });
    await firstSlot.click();

    await expect(page.getByRole('heading', { name: 'Book appointment' })).toBeVisible();
    const patientField = page.locator('#day-cal-patient');
    await expect(patientField).toBeVisible();
    await expect(patientField).toHaveValue(/E2E Patient/i);

    await page.getByRole('dialog', { name: 'Book appointment' }).getByRole('button', { name: 'Cancel' }).click();

    await page.goto(patientUrl);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 15_000 });

    await page.getByRole('button', { name: 'Create bill' }).click();
    await expect(page).toHaveURL(/\/doctor\/bills/);

    await expect(page.getByRole('heading', { name: 'New bill' })).toBeVisible({ timeout: 15_000 });
    const visitSelect = page.locator('#bill-appt');
    await expect(visitSelect).toBeVisible();
    const optionWithPatient = visitSelect.locator('option', { hasText: /E2E Patient/ });
    await expect(optionWithPatient.first()).toBeAttached();
  });
});
