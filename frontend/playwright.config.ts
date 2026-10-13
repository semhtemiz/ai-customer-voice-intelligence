import { defineConfig } from "playwright/test";
export default defineConfig({
  testDir: "./tests", workers: 1, timeout: 30000,
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000", headless: true, colorScheme: "light",
    launchOptions: { executablePath: process.env.CHROME_EXECUTABLE } },
  reporter: "list",
});
