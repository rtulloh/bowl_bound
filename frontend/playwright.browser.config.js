import { defineConfig } from '@playwright/test'

const port = 8124
const origin = `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: './e2e-browser',
  timeout: 90_000,
  expect: { timeout: 45_000 },
  use: {
    baseURL: origin,
    browserName: 'chromium',
    channel: process.env.BB_E2E_CHANNEL || undefined,
  },
  webServer: {
    // Mount the static build below the root to exercise relocatable deployments.
    command: `python3 -m http.server ${port} --bind 127.0.0.1`,
    url: `${origin}/dist-browser/`,
    reuseExistingServer: false,
  },
})
