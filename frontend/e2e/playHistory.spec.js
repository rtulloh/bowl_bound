import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`complete scoring history is readable without losing older position, width=${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const save = execFileSync('.venv/bin/python', ['-m', 'tests.history_fixtures',
      process.env.BB_E2E_SEASONS || '/tmp/bowl-bound-e2e-seasons'], { cwd: '..', env: { ...process.env, PYTHONPATH: '.' } })
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption('manual')
    const loaded = page.waitForResponse((r) => r.url().includes('/api/games/load'))
    await page.getByLabel('Load saved game', { exact: true }).setInputFiles({
      name: 'fictional-scoring-history.json', mimeType: 'application/json', buffer: save,
    })
    const response = await loaded
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    const region = page.getByRole('region', { name: 'Play history entries' })
    await expect(page.getByTestId('log-entry')).toHaveCount(43)
    expect(await region.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true)
    await region.evaluate((el) => { el.scrollTop = 100; el.dispatchEvent(new Event('scroll', { bubbles: true })) })
    await page.getByTestId('offense-play-1').click()
    await page.getByTestId('defense-play-a').click()
    await expect(page.getByTestId('log-entry')).toHaveCount(44)
    expect(await region.evaluate((el) => el.scrollTop)).toBeCloseTo(100, 0)
    await expect(page.getByRole('button', { name: 'Show latest plays' })).toBeVisible()
    await page.getByRole('button', { name: 'Show complete history' }).click()
    expect(await region.evaluate((el) => el.scrollHeight <= el.clientHeight + 1)).toBe(true)
    for (const [index, entry] of body.view.log.entries()) {
      await expect(page.getByTestId('log-entry').nth(index)).toContainText(entry.commentary)
    }
    expect(body.view.log.filter((r) => r.outcome.startsWith('pat_')).length).toBe(14)
    expect(body.view.log.filter((r) => r.outcome === 'kickoff_return').length).toBe(15)
    await page.getByTestId('log-entry').nth(2).scrollIntoViewIfNeeded()
    await expect(page.getByTestId('log-entry').nth(2)).toBeInViewport()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
  })
}
