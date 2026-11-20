import { defineConfig, devices } from "@playwright/test";

import { DJANGO_URL, FRONTEND_URL } from "./e2e/helpers/urls.ts";

/**
 * End-to-end tests (see e2e/). Spins up a dedicated Django (:8100, settings
 * `config.settings.e2e`, fresh SQLite DB seeded by `seed_e2e`) and a frontend dev
 * server (:3100) so it never collides with `make dev`.
 *
 * Requires: Mailpit on :1025/:8025 (`make e2e-mailpit`) and Stripe test keys in the
 * environment (STRIPE_TEST_SECRET_KEY, VITE_STRIPE_PUBLISHABLE_KEY via .envrc/.env).
 */

const djangoEnv =
  "DJANGO_SETTINGS_MODULE=config.settings.e2e DJANGO_LOGLEVEL=warning";

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: FRONTEND_URL,
    locale: "de-DE",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Reset + seed the DB, write the seeded IDs for the tests, then serve.
      command:
        `rm -f e2e.sqlite3 && ` +
        `${djangoEnv} uv run manage.py migrate -v0 && ` +
        `${djangoEnv} uv run manage.py seed_e2e > ../frontend/e2e/.state.json && ` +
        `${djangoEnv} uv run manage.py runserver 8100 --noreload`,
      cwd: "../backend",
      url: `${DJANGO_URL}/shows/`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "pnpm exec vite dev --port 3100 --strictPort",
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        API_URL: DJANGO_URL,
        VITE_API_URL: DJANGO_URL,
      },
    },
  ],
});
