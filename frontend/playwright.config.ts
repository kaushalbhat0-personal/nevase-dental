import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const backendRoot = path.resolve(__dirname, '..');
const dbRelative = path.join(backendRoot, '.playwright_e2e.sqlite3');
const dbUrl = `sqlite+pysqlite:///${dbRelative.replace(/\\/g, '/')}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      // Seed SQLite and credentials first so the file is not locked by a previous uvicorn (Windows).
      command: `${process.env.PYTHON ?? 'python'} -m tests.e2e_prepare && ${process.env.PYTHON ?? 'python'} -m uvicorn app.main:app --host 127.0.0.1 --port 9777`,
      cwd: backendRoot,
      url: 'http://127.0.0.1:9777/api/v1/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        DATABASE_URL: dbUrl,
        SECRET_KEY: 'playwright-e2e-secret-key-0000000001',
        ALLOWED_ORIGINS: 'http://127.0.0.1:5173',
        ENVIRONMENT: 'development',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
      cwd: __dirname,
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        VITE_API_URL: 'http://127.0.0.1:9777/api/v1',
      },
    },
  ],
});
