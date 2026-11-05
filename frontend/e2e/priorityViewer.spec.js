import { expect, test } from '@playwright/test'

async function start(page) {
  await page.goto('/')
  await page.getByLabel('Control mode').selectOption('manual')
  const started = page.waitForResponse((response) => response.url().endsWith('/api/games') && response.request().method() === 'POST')
  await page.getByTestId('start-game').click()
  return (await started).json()
}

async function snapshot(request, path) {
  const saved = await (await request.get(`${path}/save`)).json()
  delete saved.saved_at
  delete saved.integrity
  return saved
}

for (const viewport of [{ width: 1440, height: 1120 }, { width: 1280, height: 1000 }]) {
  test(`complete CSV chart fits the desktop page at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport)
    const game = await start(page)
    const book = await (await page.request.get(`/api/games/${game.game_id}/charts?side=home`)).json()
    await page.getByRole('button', { name: 'Charts', exact: true }).click()
    const dialog = page.getByRole('dialog')
    for (const kind of ['offense', 'defense', 'special_teams']) {
      await dialog.getByRole('button', { name: { offense: 'Offense', defense: 'Defense', special_teams: 'Special Teams' }[kind], exact: true }).click()
      const table = book[kind]
      const groups = kind === 'offense' ? [table.column_groups.filter((g) => !g.separate), table.column_groups.filter((g) => g.separate)] : [null]
      for (const [index, columns] of groups.entries()) {
        const grid = dialog.locator('.chart-grid').nth(index)
        await expect(grid.locator('tbody tr')).toHaveCount(30)
        const expected = table.rows.flatMap((row) => (columns ? columns.flatMap((g) => row.cells.slice(g.start, g.start + g.count)) : row.cells).map((cell) => cell.label))
        expect(await grid.locator('tbody td > span:first-child').allTextContents()).toEqual(expected)
        const fit = await grid.evaluate((element) => {
          const scroll = element.parentElement
          const rows = element.querySelectorAll('tbody tr')
          return { first: rows[0].getBoundingClientRect().top, last: rows[29].getBoundingClientRect().bottom, scrollHeight: scroll.scrollHeight, clientHeight: scroll.clientHeight, font: parseFloat(getComputedStyle(rows[0].querySelector('td')).fontSize) }
        })
        expect(fit.first).toBeGreaterThanOrEqual(0)
        expect(fit.last).toBeLessThanOrEqual(viewport.height)
        expect(fit.scrollHeight).toBeLessThanOrEqual(fit.clientHeight)
        expect(fit.font).toBeGreaterThanOrEqual(12)
      }
      await expect(dialog.locator('.chart-key')).not.toHaveAttribute('open', '')
    }
  })
}

test('Priority is a shared read-only reference with closed help and phone scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 1000 })
  const game = await start(page)
  const path = `/api/games/${game.game_id}`
  const before = await snapshot(page.request, path)
  const posts = []
  page.on('request', (request) => { if (request.method() === 'POST') posts.push(request.url()) })
  await page.getByRole('button', { name: 'Charts', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Chart team').selectOption('away')
  await expect(dialog.getByRole('heading')).toContainText(game.view.away)
  await dialog.getByRole('button', { name: 'Priority', exact: true }).click()
  await expect(dialog.getByRole('table')).toHaveAccessibleName('Priority chart')
  await expect(dialog.locator('tbody tr')).toHaveCount(12)
  await expect(dialog.locator('tbody td')).toHaveCount(168)
  await expect(dialog.locator('.chart-key')).not.toHaveAttribute('open', '')
  await dialog.getByText('How to read Priority', { exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(dialog.locator('.chart-key')).toHaveAttribute('open', '')
  await expect(dialog.getByText(/signed comparison/)).toBeVisible()
  await dialog.getByText('How to read Priority', { exact: true }).click()
  const fit = await dialog.evaluate((element) => ({ width: element.clientWidth, scrollWidth: element.scrollWidth, gridWidth: element.querySelector('.chart-scroll').clientWidth, gridScroll: element.querySelector('.chart-scroll').scrollWidth }))
  expect(fit.scrollWidth).toBeLessThanOrEqual(fit.width)
  expect(fit.gridScroll).toBeGreaterThan(fit.gridWidth)
  await dialog.getByRole('button', { name: 'Defense', exact: true }).click()
  await expect(dialog.getByLabel('Chart team')).toHaveValue('away')
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Charts', exact: true })).toBeFocused()
  expect(posts).toEqual([])
  expect(await snapshot(page.request, path)).toEqual(before)
})

for (const launcher of ['Open in new tab', 'Open in separate window']) {
  test(`${launcher} keeps an independent read-only chart while the parent remains playable`, async ({ page, context }) => {
    const game = await start(page)
    const path = `/api/games/${game.game_id}`
    const before = await snapshot(page.request, path)
    const posts = []
    context.on('request', (request) => { if (request.method() === 'POST') posts.push(request.url()) })
    await page.getByRole('button', { name: 'Charts', exact: true }).click()
    const opened = context.waitForEvent('page')
    await page.getByRole(launcher === 'Open in new tab' ? 'link' : 'button', { name: launcher, exact: true }).click()
    const child = await opened
    await child.waitForLoadState()
    await expect(child.getByRole('table', { name: /^Offense/ })).toHaveAccessibleName(/Offense/)
    expect(await child.evaluate(() => window.opener)).toBeNull()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(page.getByTestId('opening-screen')).toBeVisible()
    await child.getByLabel('Chart team').selectOption('away')
    await expect(child.getByRole('heading')).toContainText(game.view.away)
    await child.getByRole('button', { name: 'Priority', exact: true }).click()
    await expect(child.getByRole('table')).toHaveAccessibleName('Priority chart')
    await page.getByRole('button', { name: 'Charts', exact: true }).click()
    await expect(page.getByRole('table', { name: /^Offense/ })).toHaveAccessibleName(/Offense/)
    await expect(page.getByLabel('Chart team')).toHaveValue('home')
    await expect(page.locator('.chart-key')).not.toHaveAttribute('open', '')
    await page.getByRole('button', { name: 'Close charts' }).click()
    expect(posts).toEqual([])
    expect(await snapshot(page.request, path)).toEqual(before)
    // This deliberate game action proves the detached chart does not block its parent.
    await page.getByTestId('penalty-choices').locator('button:enabled').first().click()
    await expect(page.getByTestId('playing-screen')).toBeVisible()
    await expect(child.getByRole('table')).toHaveAccessibleName('Priority chart')
    await child.close()
  })
}

test('an expired detached URL shows recovery controls without mounting game setup', async ({ page }) => {
  const posts = []
  page.on('request', (request) => { if (request.method() === 'POST') posts.push(request.url()) })
  await page.goto('/?charts=expired-game&side=home&view=priority')
  await expect(page.getByRole('alert')).toContainText('game is no longer available')
  await expect(page.getByRole('button', { name: 'Retry charts' })).toBeVisible()
  await expect(page.getByTestId('start-game')).toHaveCount(0)
  expect(posts).toEqual([])
})
