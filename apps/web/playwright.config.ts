import { defineConfig, devices } from "@playwright/test";

/**
 * E2E against a running stack: API on :8000 (VAIBHAV_OTP_DEBUG_ECHO=true) and web on :3000.
 * Locally: start both (see README), then `pnpm --filter @vaibhav/web test:e2e`.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "off",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
