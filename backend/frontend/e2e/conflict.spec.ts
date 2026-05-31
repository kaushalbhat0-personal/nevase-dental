import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

type Creds = {
  apiBaseUrl: string;
  patientEmail: string;
  patientPassword: string;
  patientBEmail: string;
  patientBPassword: string;
  bookingDate?: string;
  doctorDisplayName: string;
};

function loadCreds(): Creds {
  const p = path.join(__dirname, '.e2e-credentials.json');
  const raw = fs.readFileSync(p, 'utf-8');
  return JSON.parse(raw) as Creds;
}

async function loginPatient(
  page: import('@playwright/test').Page,
  email: string,
  password: string
): Promise<void> {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/patient\/home/, { timeout: 25_000 });
}

async function openBookingForDoctor(
  page: import('@playwright/test').Page,
  doctorDisplayName: string,
  bookingDate: string
): Promise<void> {
  await page.getByRole('link', { name: 'Doctors', exact: true }).click();
  await expect(page).toHaveURL(/\/patient\/doctors/, { timeout: 15_000 });

  const card = page
    .locator('div.rounded-2xl.border')
    .filter({
      has: page.getByRole('heading', { level: 3, name: doctorDisplayName, exact: true }),
    });
  const bookBtn = card.getByRole('button', { name: 'Select' });
  await expect(bookBtn).toBeEnabled({ timeout: 15_000 });
  await bookBtn.click();
  await expect(page.getByRole('dialog')).toBeVisible();

  const slotsResponse = page.waitForResponse(
    (res) => res.url().includes('/slots') && res.status() === 200
  );
  await page.locator('#book-date').fill(bookingDate);
  await slotsResponse;

  const firstSlot = page.getByTestId('slot-button').first();
  await expect(firstSlot).toBeEnabled({ timeout: 20_000 });
  await firstSlot.click();
}

async function appointmentListLength(
  page: import('@playwright/test').Page,
  apiBaseUrl: string
): Promise<number> {
  const token = await page.evaluate(() => localStorage.getItem('token'));
  if (!token) {
    throw new Error('Expected patient JWT in localStorage');
  }
  const res = await page.request.get(`${apiBaseUrl}/appointments`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(res.ok(), `appointments GET failed: ${res.status()}`).toBeTruthy();
  const data = (await res.json()) as unknown[];
  return data.length;
}

test.describe('Booking conflict', () => {
  /**
   * Patient B loads slots and selects the first open slot, then Patient A books that instant.
   * Patient B's client state is still pre-booking until /slots refetches (poll is slow), so Confirm
   * sends the same ISO and the API rejects — matching double-book prevention without changing APIs.
   */
  test('second patient cannot take the same slot (stale selection then reject)', async ({ browser }) => {
    const c = loadCreds();
    const bookingDate = c.bookingDate ?? '2035-06-15';
    const apiBaseUrl = c.apiBaseUrl;

    const ctxB = await browser.newContext();
    const ctxA = await browser.newContext();
    const pageB = await ctxB.newPage();
    const pageA = await ctxA.newPage();

    try {
      await loginPatient(pageB, c.patientBEmail, c.patientBPassword);
      await openBookingForDoctor(pageB, c.doctorDisplayName, bookingDate);

      await loginPatient(pageA, c.patientEmail, c.patientPassword);
      await openBookingForDoctor(pageA, c.doctorDisplayName, bookingDate);

      const countBeforeA = await appointmentListLength(pageA, apiBaseUrl);
      const countBeforeB = await appointmentListLength(pageB, apiBaseUrl);

      const createAppt = pageA.waitForResponse(
        (r) =>
          r.url().includes('/appointments') &&
          r.request().method() === 'POST' &&
          (r.status() === 201 || r.status() === 200)
      );
      await Promise.all([createAppt, pageA.getByRole('button', { name: 'Confirm' }).click()]);

      await expect(pageA).toHaveURL(/\/patient\/appointments/, { timeout: 25_000 });

      const countAfterA = await appointmentListLength(pageA, apiBaseUrl);
      expect(countAfterA).toBe(countBeforeA + 1);

      await pageB.getByRole('button', { name: 'Confirm' }).click();

      await expect(pageB.getByText(/slot|booked|taken|failed/i)).toBeVisible({ timeout: 15_000 });
      await expect(pageB).not.toHaveURL(/\/patient\/appointments/);

      const countAfterB = await appointmentListLength(pageB, apiBaseUrl);
      expect(countAfterB).toBe(countBeforeB);
    } finally {
      await ctxB.close();
      await ctxA.close();
    }
  });
});
