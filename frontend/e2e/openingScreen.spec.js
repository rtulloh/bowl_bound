import { expect, test } from '@playwright/test'

for (const [width, height, decision] of [[1280, 720, 'kick'], [390, 700, 'receive']]) {
  test('opening toss precedes play with visible choices and kickoff, width=' + width, async ({ page }) => {
    await page.setViewportSize({ width, height })
    await page.route('**/api/games', async (route) => {
      await route.continue({ postData: JSON.stringify({ ...route.request().postDataJSON(), seed: 7 }) })
    })
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption('manual')
    await page.getByTestId('home-select').selectOption('2002/alpha-tech')
    await page.getByTestId('away-select').selectOption('2002/beta-state')
    const created = page.waitForResponse((r) => r.url().endsWith('/api/games') && r.request().method() === 'POST')
    await page.getByTestId('start-game').click()
    const original = await (await created).json()
    await expect(page.getByTestId('opening-screen')).toBeVisible()
    await expect(page.getByTestId('toss-flipping')).toBeVisible()
    await expect(page.getByTestId('coin')).toHaveCSS('animation-name', 'coin-reveal')
    for (const id of ['scoreboard', 'football-field', 'result-empty', 'offense-plays', 'defense-plays', 'team-statistics']) {
      await expect(page.getByTestId(id)).toHaveCount(0)
    }
    await expect(page.getByRole('region', { name: 'Play modifiers' })).toHaveCount(0)
    const firstChoice = original.view.pending.choices.find((choice) => choice.enabled)
    await expect(page.getByTestId('penalty-choice-' + firstChoice.id)).toBeFocused()
    for (const choice of ['kick', 'receive']) {
      const button = page.getByTestId('penalty-choice-toss:' + choice)
      await expect(button).toBeVisible()
      const box = await button.boundingBox()
      expect(box.y).toBeGreaterThanOrEqual(0)
      expect(box.y + box.height).toBeLessThanOrEqual(height)
    }
    expect(await page.evaluate(() => window.scrollY)).toBe(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    const audit = page.getByTestId('coin-toss').locator('details')
    await expect(audit).not.toHaveAttribute('open', '')
    await audit.locator('summary').click()
    await expect(audit.getByRole('img')).not.toHaveCount(0)
    await audit.locator('summary').click()
    const resolved = page.waitForResponse((r) => r.url().endsWith('/decision') && r.request().method() === 'POST')
    await page.getByTestId('penalty-choice-toss:' + decision).click()
    const result = await (await resolved).json()
    expect(result.view.phase).toBe('kickoff')
    expect(result.view.clock).toEqual(original.view.clock)
    expect(result.view.toss_dice).toEqual(original.view.toss_dice)
    await expect(page.getByTestId('opening-screen')).toHaveCount(0)
    await expect(page.getByTestId('playing-screen')).toBeVisible()
    const kickoff = page.getByTestId('special-play-kickoff')
    await expect(kickoff).toBeVisible()
    const box = await kickoff.boundingBox()
    expect(box.y).toBeGreaterThanOrEqual(0)
    expect(box.y + box.height).toBeLessThanOrEqual(height)
  })
}
