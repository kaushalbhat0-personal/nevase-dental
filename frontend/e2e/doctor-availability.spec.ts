import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

type Creds = {
  apiBaseUrl: string;
  doctorEmail: string;
  doctorPassword: string;
  hospitalDoctorEmail?: string;
  hospitalDoctorPassword?: string;
  bookingDate?: string;
};

function loadCreds(): Creds {
  const p = path.join(__dirname, '.e2e-credentials.json');
  const raw = fs.readFileSync(p, 'utf-8');
  return JSON.parse(raw) as Creds;
}

async function loginDoctor(page: import('@playwright/test').Page, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/doctor\//, { timeout: 30_000 });
}

test.describe('Doctor availability', () => {
  test('independent doctor: add, list, edit, delete window + API in sync', async ({ page, request }) => {
    const c = loadCreds();
    await loginDoctor(page, c.doctorEmail, c.doctorPassword);
    await page.goto('/doctor/availability');
    await expect(page.getByTestId('doctor-availability-page')).toBeVisible({ timeout: 20_000 });

    await page.getByTestId('availability-day-tab-0').click();
    await page.getByTestId('availability-add-window').click();
    await expect(page.getByTestId('availability-modal')).toBeVisible();
    await page.locator('#avail-dow').selectOption('0');
    await page.locator('#avail-start').fill('14:00');
    await page.locator('#avail-end').fill('15:00');
    await page.locator('#avail-slot').fill('20');
    const apiWait = page.waitForResponse(
      (res) => res.url().includes('/availability-windows') && res.request().method() === 'POST' && res.status() === 201
    );
    await page.getByTestId('availability-modal').getByRole('button', { name: 'Add window' }).click();
    await apiWait;
    await expect(page.getByTestId('availability-modal')).not.toBeVisible({ timeout: 10_000 });

    const availList = page.getByLabel('Availability windows for selected day');
    await expect(availList.getByRole('listitem').filter({ hasText: '14:00' }).filter({ hasText: '15:00' })).toBeVisible({
      timeout: 10_000,
    });

    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token, 'expected JWT in localStorage').toBeTruthy();
    const doctorsRes = await request.get(`${c.apiBaseUrl}/doctors?skip=0&limit=100`, {
      headers: { Authorization: `Bearer ${token!}` },
    });
    const doctors = (await doctorsRes.json()) as { id: string; linked_user_email?: string }[];
    const selfDoctor = doctors.find((d) => d.linked_user_email === c.doctorEmail);
    const doctorId = selfDoctor ? String(selfDoctor.id) : String(doctors[0].id);
    const winRes = await request.get(`${c.apiBaseUrl}/doctors/${doctorId}/availability-windows`, {
      headers: { Authorization: `Bearer ${token!}` },
    });
    expect(winRes.ok(), `windows GET failed: ${winRes.status()}`).toBeTruthy();
    const windows = (await winRes.json()) as { day_of_week: number; start_time: string; end_time: string }[];
    const match = windows.find(
      (w) => w.day_of_week === 0 && w.start_time.startsWith('14:00') && w.end_time.startsWith('15:00')
    );
    expect(match, 'API should return the new window').toBeTruthy();

    const rowWithEdit = availList.getByRole('listitem').filter({ hasText: '14:00' }).filter({ hasText: '15:00' });
    const editButton = rowWithEdit.getByTitle('Edit');
    await editButton.click();
    await expect(page.getByTestId('availability-modal')).toBeVisible();
    await page.locator('#avail-end').fill('16:00');
    const putWait = page.waitForResponse(
      (res) => res.url().includes('/availability-windows/') && res.request().method() === 'PUT' && res.status() === 200
    );
    await page.getByRole('button', { name: 'Save changes' }).click();
    await putWait;
    await expect(availList.getByRole('listitem').filter({ hasText: '14:00' }).filter({ hasText: '16:00' })).toBeVisible({
      timeout: 10_000,
    });

    page.on('dialog', (d) => d.accept());
    const delBtn = availList.getByRole('listitem').filter({ hasText: '14:00' }).filter({ hasText: '16:00' }).getByTitle('Delete');
    const delWait = page.waitForResponse(
      (res) => res.url().includes('/availability-windows/') && res.request().method() === 'DELETE' && res.status() === 204
    );
    await delBtn.click();
    await delWait;
    await expect(availList.getByRole('listitem').filter({ hasText: '14:00' }).filter({ hasText: '16:00' })).toHaveCount(0);
  });

  test('hospital (managed) doctor: read-only, no add', async ({ page }) => {
    const c = loadCreds();
    if (!c.hospitalDoctorEmail || !c.hospitalDoctorPassword) {
      test.skip();
    }
    await loginDoctor(page, c.hospitalDoctorEmail, c.hospitalDoctorPassword);
    await page.goto('/doctor/availability');
    await expect(page.getByTestId('availability-read-only-notice')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('availability-add-window')).toHaveCount(0);
  });

  test('slot count after availability: calendar shows bookable slots for seeded Friday', async ({ page, request }) => {
    const c = loadCreds();
    await loginDoctor(page, c.doctorEmail, c.doctorPassword);
    const booking = c.bookingDate ?? '2035-06-15';
    const dayScheduleWait = page.waitForResponse(
      (r) => r.url().includes('/schedule/day') && r.status() === 200
    );
    await page.goto(`/doctor/appointments?date=${booking}`);
    await dayScheduleWait;
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();
    const doctorsRes = await request.get(`${c.apiBaseUrl}/doctors?skip=0&limit=100`, {
      headers: { Authorization: `Bearer ${token!}` },
    });
    const doctors = (await doctorsRes.json()) as { id: string; linked_user_email?: string }[];
    const selfDoctor = doctors.find((d) => d.linked_user_email === c.doctorEmail);
    const doctorId = selfDoctor ? String(selfDoctor.id) : String(doctors[0].id);
    const slotsRes = await request.get(`${c.apiBaseUrl}/doctors/${doctorId}/slots?date=${booking}`, {
      headers: { Authorization: `Bearer ${token!}` },
    });
    expect(slotsRes.ok(), `slots API ${slotsRes.status()}`).toBeTruthy();
    const slots = (await slotsRes.json()) as unknown[];
    expect(Array.isArray(slots) && slots.length > 0, 'Seeded Friday window should generate slots').toBeTruthy();

    await expect(page.getByTestId('doctor-schedule-slot').first()).toBeVisible({ timeout: 30_000 });
  });
});
