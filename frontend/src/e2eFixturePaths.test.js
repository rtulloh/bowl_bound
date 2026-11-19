// @vitest-environment node
import { execFileSync } from 'node:child_process'
import { mkdtempSync, realpathSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { expect, test } from 'vitest'

for (const override of [false, true]) {
  test(`E2E backend and workers share the fixture destination (override=${override})`, () => {
    const temporary = realpathSync(mkdtempSync(join(tmpdir(), "bb fixture ' space ")))
    try {
      const destination = join(temporary, 'explicit fixture root')
      const env = { ...process.env, TMPDIR: temporary, TEMP: temporary, TMP: temporary }
      delete env.BB_E2E_SEASONS
      if (override) env.BB_E2E_SEASONS = destination
      const result = execFileSync(process.execPath, ['--input-type=module', '-e',
        "import config from './playwright.config.js'; " +
        'console.log(JSON.stringify({worker: process.env.BB_E2E_SEASONS, ' +
        'command: config.webServer.command, server: config.webServer.env}))',
      ], { env, encoding: 'utf8' })
      const actual = JSON.parse(result)
      const expected = override ? destination : join(temporary, 'bowl-bound-e2e-seasons')
      expect(actual.worker).toBe(expected)
      expect(actual.command).toBe('../.venv/bin/python e2e/serve_backend.py')
      expect(actual.server).toEqual({ BB_E2E_SEASONS: expected, BB_E2E_PORT: '8123' })
    } finally {
      rmSync(temporary, { recursive: true, force: true })
    }
  })
}
