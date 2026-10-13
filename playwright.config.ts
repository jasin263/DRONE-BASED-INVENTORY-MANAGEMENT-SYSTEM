import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  use: { baseURL: "http://frontend", screenshot: "only-on-failure", trace: "retain-on-failure" },
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
});
