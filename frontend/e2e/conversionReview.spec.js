import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'

for (const human of ['home', 'away']) {
  for (const result of ['good', 'failed']) {
    test(`two-point announcement and result precede automatic kickoff: ${human}, ${result}`, async ({ page }) => {
      const save = execFileSync('.venv/bin/python', ['-m', 'tests.conversion_fixtures',
        process.env.BB_E2E_SEASONS || '/tmp/bowl-bound-e2e-seasons', human, result],
      { cwd: '..', env: { ...process.env, PYTHONPATH: '.' } })
      await page.goto('/')
      await page.getByLabel('Control mode').selectOption(human)
      const loaded = page.waitForResponse((r) => r.url().includes('/api/games/load'))
      await page.getByLabel('Load saved game', { exact: true }).setInputFiles({ name: 'fictional-try.json', mimeType: 'application/json', buffer: save })
      const body = await (await loaded).json()
      await expect(page.getByTestId('session-status')).toContainText('is going for two. Choose your defense')
      await expect(page.getByTestId('log-entry').last()).toContainText('is going for two.')
      expect(body.turn.actions.offense).toEqual([])
      await page.getByTestId('defense-play-a').click()
      const review = page.getByRole('region', { name: 'Two-point result' })
      await expect(review).toBeVisible()
      await expect(review).toContainText(result === 'good' ? 'two-point conversion good' : 'two-point conversion no good')
      await page.waitForTimeout(500) // Longer than automatic scheduling, review must persist.
      await expect(page.getByTestId('log-entry')).toHaveCount(body.view.log.length + 1)
      await expect(review).toBeVisible()
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await expect(page.getByTestId('log-entry')).toHaveCount(body.view.log.length + 2)
      await expect(page.getByTestId('log-entry').nth(body.view.log.length - 1)).toContainText('is going for two.')
      await expect(page.getByTestId('log-entry').nth(body.view.log.length)).toContainText('two-point conversion')
      await expect(page.getByTestId('log-entry').nth(body.view.log.length + 1)).toContainText('kickoff')
      await expect(review).toHaveCount(0)
    })
  }
}
