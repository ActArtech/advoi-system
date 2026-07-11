import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.ADVOI_WEB_URL || "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "logic",
      testMatch: /agents-orchestrator\.spec\.ts/,
    },
  ],
});