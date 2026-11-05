import { expect, test } from '@playwright/test'

const stableSave = async (request, path) => {
  const saved = await (await request.get(`${path}/save`)).json()
  delete saved.saved_at
  delete saved.integrity
  return saved
}

for (const width of [1280, 390]) {
  test(`chart inspection preserves a real game and fits ${width}px`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1000 })
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption('manual')
    const started = page.waitForResponse((response) => response.url().endsWith('/api/games') && response.request().method() === 'POST')
    await page.getByTestId('start-game').click()
    const game = await (await started).json()
    const path = `/api/games/${game.game_id}`
    const before = await stableSave(request, path)
    const posts = []
    page.on('request', (sent) => { if (sent.method() === 'POST') posts.push(sent.url()) })
    await page.getByRole('button', { name: 'Charts', exact: true }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('table', { name: /^Offense/ })).toHaveAccessibleName(/Offense/)
    await expect(dialog.locator('table[data-section=main] tbody tr')).toHaveCount(30)
    await expect(dialog.locator('tbody td')).toHaveCount(360)
    await expect(dialog.getByRole('button', { name: 'Close charts' })).toBeFocused()
    await expect(dialog.getByRole('columnheader', { name: '9 · Drop Back' })).toHaveCount(1)
    await dialog.getByRole('button', { name: 'Defense', exact: true }).click()
    await expect(dialog.getByRole('table')).toHaveAccessibleName(/Defense/)
    await expect(dialog.locator('tbody td')).toHaveCount(270)
    await expect(dialog.locator('.chart-formation-letter').last()).toHaveText('F')
    await expect(dialog.locator('.chart-die-face').last()).toHaveText('5')
    await dialog.getByLabel('Chart team').selectOption('away')
    await expect(dialog.getByRole('heading')).toContainText(game.view.away)
    const layout = await dialog.evaluate((element) => {
      const grid = element.querySelector('.chart-scroll')
      const rect = element.getBoundingClientRect()
      return {
        left: rect.left, right: rect.right, viewport: window.innerWidth,
        scrolls: grid.scrollWidth > grid.clientWidth,
        leaks: element.scrollWidth > element.clientWidth,
      }
    })
    expect(layout.left).toBeGreaterThanOrEqual(0)
    expect(layout.right).toBeLessThanOrEqual(layout.viewport)
    expect(layout.leaks, JSON.stringify(layout)).toBe(false)
    if (width === 390) expect(layout.scrolls).toBe(true)
    await dialog.getByRole('button', { name: 'Special Teams', exact: true }).click()
    await expect(dialog.getByRole('table')).toHaveAccessibleName(/Special Teams/)
    await expect(dialog.locator('tbody td')).toHaveCount(210)
    const help = dialog.locator('details')
    expect(await help.getAttribute('open')).toBeNull()
    await help.locator('summary').click()
    await expect(help).toContainText('BLACK marker; consult the applicable special-teams procedure.')
    await expect(help).not.toContainText('Incomplete pass')
    for (const launcher of [dialog.getByRole('link', { name: 'Open in new tab' }), dialog.getByRole('button', { name: 'Open in separate window' })]) {
      await expect(launcher).toBeVisible()
      expect(await launcher.evaluate((e) => parseFloat(getComputedStyle(e).borderTopWidth))).toBeGreaterThanOrEqual(1)
    }
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Charts', exact: true })).toBeFocused()
    expect(posts).toEqual([])
    expect(await stableSave(request, path)).toEqual(before)
  })
}
