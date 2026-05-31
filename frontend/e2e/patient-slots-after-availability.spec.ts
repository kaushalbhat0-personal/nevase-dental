import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

type Creds = {
  apiBaseUrl: string;
  doctorEmail: string;
  doctorPassword: string;
  patientEmail: string;
  patientPassword: string;
  doctorDisplayName: string;
  bookingDate?: string;
};

function loadCreds(): Creds {
  const p = path.join(__dirname, '.e2e-credentials.json');
  const raw = fs.readFileSync(p, 'utf-8');
  return JSON.parse(raw) as Creds;
}

/** Monday = 0 … Sunday = 6 (matches Python `date.weekday()` and API `day_of_week`). */
function pythonWeekdayFromIsoDate(ymd: string): number {
  const [y, m, d] = ymd.split('-').map(Number);
  const js = new Date(Date.UTC(y, m - 1, d, 12, 0, 0)).getUTCDay();
  return (js + 6) % 7;
}

async function loginDoctor(page: import('@playwright/test').Page, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/doctor\//, { timeout: 30_000 });
}

async function loginPatient(page: import('@playwright/test').Page, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/patient\//, { timeout: 30_000 });
}

async function doctorTokenAndId(
  page: import('@playwright/test').Page,
  request: import('@playwright/test').APIRequestContext,
  c: Creds
): Promise<{ token: string; doctorId: string }> {
  const token = await page.evaluate(() => localStorage.getItem('token'));
  expect(token, 'expected JWT in localStorage').toBeTruthy();
  const doctorsRes = await request.get(`${c.apiBaseUrl}/doctors?skip=0&limit=100`, {
    headers: { Authorization: `Bearer ${token!}` },
  });
  expect(doctorsRes.ok(), `doctors list ${doctorsRes.status()}`).toBeTruthy();
  const doctors = (await doctorsRes.json()) as { id: string; linked_user_email?: string }[];
  const selfDoctor = doctors.find((d) => d.linked_user_email === c.doctorEmail);
  const doctorId = selfDoctor ? String(selfDoctor.id) : String(doctors[0].id);
  return { token: token!, doctorId };
}

test.describe('Patient booking vs doctor availability', () => {
  test('patient sees more slot buttons after doctor shortens slot length (30 → 15 min)', async ({
    page,
    request,
  }) => {
    const c = loadCreds();
    const bookingDate = c.bookingDate ?? '2035-06-15';
    const dow = pythonWeekdayFromIsoDate(bookingDate);

    await loginDoctor(page, c.doctorEmail, c.doctorPassword);
    const { token, doctorId } = await doctorTokenAndId(page, request, c);

    const slotsBeforeRes = await request.get(`${c.apiBaseUrl}/doctors/${doctorId}/slots?date=${bookingDate}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(slotsBeforeRes.ok(), `slots GET before ${slotsBeforeRes.status()}`).toBeTruthy();
    const slotsBefore = (await slotsBeforeRes.json()) as unknown[];
    expect(slotsBefore.length, 'seeded doctor should have slots on booking date').toBeGreaterThan(0);

    await page.goto('/doctor/availability');
    await expect(page.getByTestId('doctor-availability-page')).toBeVisible({ timeout: 20_000 });

    await page.getByTestId(`availability-day-tab-${dow}`).click();

    const availList = page.getByLabel('Availability windows for selected day');
    const row = availList.getByRole('listitem').filter({ hasText: '10:00' }).filter({ hasText: '12:00' });
    await expect(row).toBeVisible({ timeout: 15_000 });
    await row.getByTitle('Edit').click();
    await expect(page.getByTestId('availability-modal')).toBeVisible();

    const slotInput = page.locator('#avail-slot');
    await expect(slotInput).toHaveValue('30');
    await slotInput.fill('15');

    const putWait = page.waitForResponse(
      (res) =>
        res.url().includes('/availability-windows/') && res.request().method() === 'PUT' && res.status() === 200
    );
    await page.getByRole('button', { name: 'Save changes' }).click();
    await putWait;
    await expect(page.getByTestId('availability-modal')).not.toBeVisible({ timeout: 10_000 });

    await page.getByRole('button', { name: 'Logout' }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });

    await loginPatient(page, c.patientEmail, c.patientPassword);

    await page.getByRole('link', { name: 'Doctors', exact: true }).click();
    await expect(page).toHaveURL(/\/patient\/doctors/, { timeout: 15_000 });

    await page.getByRole('button', { name: c.doctorDisplayName }).click();
    await expect(page.locator('#book-date')).toBeVisible({ timeout: 15_000 });

    const slotsResponse = page.waitForResponse(
      (res) => res.url().includes('/slots') && res.status() === 200
    );
    await page.locator('#book-date').fill(bookingDate);
    await slotsResponse;

    const afterCount = await page.getByTestId('slot-button').count();
    expect(afterCount).toBeGreaterThan(slotsBefore.length);

    // Restore seed duration so local reruns with a reused dev server stay consistent.
    await page.getByRole('button', { name: 'Logout' }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
    await loginDoctor(page, c.doctorEmail, c.doctorPassword);
    await page.goto('/doctor/availability');
    await expect(page.getByTestId('doctor-availability-page')).toBeVisible({ timeout: 20_000 });
    await page.getByTestId(`availability-day-tab-${dow}`).click();
    const rowAfter = availList
      .getByRole('listitem')
      .filter({ hasText: '10:00' })
      .filter({ hasText: '12:00' });
    await expect(rowAfter).toBeVisible({ timeout: 15_000 });
    await rowAfter.getByTitle('Edit').click();
    await expect(page.getByTestId('availability-modal')).toBeVisible();
    await page.locator('#avail-slot').fill('30');
    const restoreWait = page.waitForResponse(
      (res) =>
        res.url().includes('/availability-windows/') && res.request().method() === 'PUT' && res.status() === 200
    );
    await page.getByRole('button', { name: 'Save changes' }).click();
    await restoreWait;
  });
});
