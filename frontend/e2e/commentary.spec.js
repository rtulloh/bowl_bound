import { test, expect } from '@playwright/test'

for (const arrangement of ['named', 'reversed', 'missing']) {
  test('engine roster narration, mobile wrapping and save/load: ' + arrangement, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.route('**/api/games', async (route) => {
      await route.continue({ postData: JSON.stringify({ ...route.request().postDataJSON(), seed: 7 }) })
    })
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption('manual')
    const home = arrangement === 'missing' ? 'alpha-tech' : arrangement === 'named' ? 'roster-home' : 'roster-away'
    const away = arrangement === 'missing' ? 'beta-state' : arrangement === 'named' ? 'roster-away' : 'roster-home'
    await page.getByTestId('home-select').selectOption('2002/' + home)
    await page.getByTestId('away-select').selectOption('2002/' + away)
    await page.getByTestId('start-game').click()
    await page.getByTestId('penalty-choice-toss:kick').click()
    await page.getByTestId('special-play-kickoff').click()
    await page.getByTestId('offense-play-1').click()
    const snapped = page.waitForResponse((r) => r.url().endsWith('/snap'))
    await page.getByTestId('defense-play-a').click()
    const body = await (await snapped).json()
    const text = body.report.commentary
    expect(text.includes('Illustrative players')).toBe(arrangement !== 'missing')
    if (arrangement !== 'missing') expect(text).toContain(arrangement === 'named' ? 'Home Fictional' : 'Away Fictional')
    await expect(page.getByTestId("result-description")).toHaveText(text, { useInnerText: false })
    await expect(page.getByTestId('play-log')).toContainText(text)
    const assertFits = async () => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
      const narration = page.getByTestId("log-entry").last().locator(":scope > div").first()
      await expect(narration).toBeVisible()
      expect(await narration.evaluate((el) => el.clientWidth)).toBeGreaterThan(0)
      expect(await narration.textContent()).toBe(body.report.number + ". " + text)
      expect(await narration.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true)
    }
    await assertFits()
    const download = page.waitForEvent('download')
    await page.getByText('Game', { exact: true }).click()
    await page.getByRole('button', { name: 'Save game', exact: true }).click()
    const file = await download
    const savedPath = await file.path()
    await page.reload()
    await page.getByLabel('Control mode').selectOption('manual')
    const loaded = page.waitForResponse((r) => r.url().endsWith('/api/games/load'))
    await page.getByLabel('Load saved game', { exact: true }).setInputFiles(savedPath)
    const resumed = await (await loaded).json()
    expect(resumed.view.log.at(-1).commentary).toBe(text)
    await expect(page.getByTestId("play-log")).toContainText(text)
    await assertFits()
  })
}
