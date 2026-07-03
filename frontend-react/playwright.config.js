import { defineConfig, devices } from "@playwright/test";

const frontendPort = process.env.E2E_FRONTEND_PORT || "4173";
const frontendHost = process.env.E2E_FRONTEND_HOST || "127.0.0.1";
const backendUrl =
  process.env.E2E_BACKEND_URL ||
  process.env.VITE_BACKEND_URL ||
  process.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: `http://${frontendHost}:${frontendPort}`,
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npm run dev -- --host ${frontendHost} --port ${frontendPort}`,
    url: `http://${frontendHost}:${frontendPort}/login`,
    reuseExistingServer: !process.env.CI,
    stdout: "ignore",
    stderr: "pipe",
    env: {
      ...process.env,
      VITE_BACKEND_URL: backendUrl,
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
