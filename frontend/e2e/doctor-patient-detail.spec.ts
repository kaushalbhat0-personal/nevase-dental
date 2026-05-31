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
    doctorBEmail: string;
    doctorBPassword: string;
    doctorLinkedPatientId: string;
    doctorLinkedAppointmentId: string;
  };
}

async function loginAsDoctor(
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

test.describe('Doctor patient detail page', () => {
  test('navigates from list and shows patient with activity and bills', async ({ page }) => {
    const c = loadCreds();
    await loginAsDoctor(page, c.doctorEmail, c.doctorPassword);

    await page.goto('/doctor/patients');
    await expect(page).toHaveURL(/\/doctor\/patients/);

    await page.getByRole('link', { name: 'E2E Patient' }).first().click();
    await expect(page).toHaveURL(new RegExp(`/doctor/patients/${c.doctorLinkedPatientId}$`));
    await expect(page.getByRole('heading', { name: 'E2E Patient', level: 1 })).toBeVisible();

    await expect(page.getByText('Total visits').first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Activity' })).toBeVisible();
    await expect(page.getByText('Appointment', { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Bill', { exact: false }).first()).toBeVisible();

    await page.getByRole('button', { name: 'Bills' }).click();
    await expect(page.getByText('E2E seed bill', { exact: true })).toBeVisible();
    await expect(page.getByText(/500\.?00/)).toBeVisible();
  });

  test('RBAC: other doctor cannot open patient', async ({ page }) => {
    const c = loadCreds();
    await loginAsDoctor(page, c.doctorBEmail, c.doctorBPassword);

    await page.goto(`/doctor/patients/${c.doctorLinkedPatientId}`);
    await expect(page.getByText('Access denied').first()).toBeVisible({ timeout: 20_000 });
  });

  test('visit link from patient opens appointment detail route', async ({ page }) => {
    const c = loadCreds();
    await loginAsDoctor(page, c.doctorEmail, c.doctorPassword);

    await page.goto(`/doctor/patients/${c.doctorLinkedPatientId}`);

    await page.getByRole('link', { name: 'View visit' }).first().click();
    await expect(page).toHaveURL(
      new RegExp(`/doctor/appointments/${c.doctorLinkedAppointmentId}$`)
    );
    await expect(page.getByRole('heading', { name: 'Visit', level: 1 })).toBeVisible({
      timeout: 15_000,
    });
    const target = page.locator(`#appt-${c.doctorLinkedAppointmentId}`);
    await expect(target).toBeVisible();
  });
});
