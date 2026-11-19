import { realpathSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { defineConfig } from '@playwright/test'

// Resolve the real temp directory: on macOS /tmp and $TMPDIR are symlinks, and
// the sample installer refuses symlinked destinations.
const SEASONS = process.env.BB_E2E_SEASONS
  || join(realpathSync(tmpdir()), 'bowl-bound-e2e-seasons')
// Workers and their Python fixture subprocesses inherit the backend destination.
process.env.BB_E2E_SEASONS = SEASONS
const PORT = 8123
// Optional: BB_E2E_CHANNEL=chrome uses an installed Google Chrome instead of Playwright's Chromium.
const CHANNEL = process.env.BB_E2E_CHANNEL || undefined

// The real FastAPI server and the real engine serve the production build over synthetic teams.
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.js',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    browserName: 'chromium',
    channel: CHANNEL,
    viewport: { width: 1280, height: 1000 },
  },
  webServer: {
    command: '../.venv/bin/python e2e/serve_backend.py',
    env: { BB_E2E_SEASONS: SEASONS, BB_E2E_PORT: String(PORT) },
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
