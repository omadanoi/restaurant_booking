import { defineConfig } from "@playwright/test";

// Backend command: local default targets the Windows venv; CI overrides via
// E2E_BACKEND_COMMAND ("python -m uvicorn app.main:app --port 8000").
const backendCommand =
  process.env.E2E_BACKEND_COMMAND ??
  ".venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 1,
  // Single worker: specs share the seeded demo restaurant, so parallel
  // bookings could race each other.
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    // Pin the browser to the demo restaurant's timezone so "18:00" in the
    // UI is 18:00 restaurant-local — keeps opening-hours logic deterministic.
    timezoneId: "America/New_York",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: backendCommand,
      cwd: "../backend",
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
