import { defineConfig, devices } from "@playwright/test";

const apiPort = 8765;
const webPort = 5174;

export default defineConfig({
  testDir: "./tests/e2e",
  globalSetup: "./tests/e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://localhost:${webPort}`,
    acceptDownloads: true,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "scripts/e2e_api.sh",
      url: `http://127.0.0.1:${apiPort}/health`,
      env: { SELECTIQ_E2E_API_PORT: String(apiPort), SELECTIQ_E2E_WEB_PORT: String(webPort) },
      reuseExistingServer: false,
      timeout: 300_000,
    },
    {
      command: `npm --prefix frontend run dev -- --port ${webPort} --strictPort`,
      url: `http://localhost:${webPort}`,
      env: { VITE_SELECTIQ_API_URL: `http://localhost:${apiPort}` },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
