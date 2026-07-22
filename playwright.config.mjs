import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.mjs',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:48173',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure'
  },
  webServer: {
    command: 'python3 -m http.server 48173 --bind 127.0.0.1 --directory site',
    url: 'http://127.0.0.1:48173',
    reuseExistingServer: false
  }
});
