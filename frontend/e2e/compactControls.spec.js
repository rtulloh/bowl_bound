import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`game menu overlays without moving the play controls, width=${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/games', async (route) => {
      await route.continue({ postData: JSON.stringify({ ...route.request().postDataJSON(), seed: 7 }) })
    })
    await page.goto('/')
    await expect(page.getByLabel('Control mode')).toHaveValue('home')
    await page.getByLabel('Control mode').selectOption('manual')
    await page.getByTestId('home-select').selectOption('2002/alpha-tech')
    await page.getByTestId('away-select').selectOption('2002/beta-state')
    await page.getByTestId('start-game').click()
    await page.getByTestId('penalty-choice-toss:kick').click()
    await page.getByTestId('special-play-kickoff').click()
    const plays = page.getByTestId('offense-plays')
    await expect(plays).toBeVisible()
    await expect(plays.getByTestId('special-play-punt').locator('span')).toHaveText(['P', 'Punt'])
    await expect(plays.getByTestId('special-play-field_goal').locator('span')).toHaveText(['F', 'FG'])
    await expect(plays.getByTestId('game-play-kneel').locator('span')).toHaveText(['K', 'Kneel'])
    await expect(plays.getByTestId('special-play-field_goal')).toHaveAccessibleName('F: Field goal attempt')
    await expect(page.getByTestId('special-plays')).toHaveCount(0)
    await expect(page.getByTestId('game-plays')).toHaveCount(0)
    for (const [key, name] of [
      ['a', 'Standard'], ['b', 'Short yardage (gaps)'], ['c', 'Short yardage (wide)'],
      ['d', 'Pass prevent (short)'], ['e', 'Pass prevent (long)'], ['f', 'Blitz'],
    ]) {
      const defense = page.getByTestId('defense-play-' + key)
      await expect(defense.locator('span')).toHaveText([key.toUpperCase(), name])
      await expect(defense).toHaveAttribute('title', name)
    }
    const modifiers = page.getByRole('region', { name: 'Play modifiers' })
    const hurry = modifiers.getByRole('checkbox', { name: 'Hurry-up mode' })
    await expect(hurry).toBeVisible()
    for (const name of ['Timeout', 'Spike', 'OOB', 'IB']) {
      const modifier = modifiers.getByRole('button', { name, exact: true })
      await expect(modifier).toBeVisible()
      await expect(modifier).toBeDisabled()
      if (width === 1280) {
        const box = await modifier.boundingBox()
        const mode = await hurry.boundingBox()
        expect(Math.abs((box.y + box.height / 2) - (mode.y + mode.height / 2))).toBeLessThan(3)
      }
    }
    await expect(page.getByLabel('Control mode')).toHaveCount(0)
    await expect(page.getByTestId('snap')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Pause computer|Resume computer/ })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Save game' })).toBeHidden()
    await expect(page.getByTestId('new-drive')).toBeHidden()
    await expect(page.getByLabel('Load saved game')).toBeHidden()
    const summary = page.locator('header summary')
    await summary.focus()
    const before = await plays.boundingBox()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('button', { name: 'Save game' })).toBeVisible()
    await expect(page.getByLabel('Load saved game')).toBeVisible()
    const after = await plays.boundingBox()
    expect(after.y).toBe(before.y)
    expect(after.height).toBe(before.height)
    const menu = await page.locator('header details > div').boundingBox()
    expect(menu.x).toBeGreaterThanOrEqual(0)
    expect(menu.x + menu.width).toBeLessThanOrEqual(width)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    await page.getByRole('button', { name: 'Save game' }).focus()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('button', { name: 'Save game' })).toBeHidden()
    await expect(summary).toBeFocused()
    await page.getByTestId('offense-play-1').click()
    await page.getByTestId('defense-play-a').click()
    const timeout = modifiers.locator('input[value="clock:timeout:home"]')
    await expect(timeout).toBeVisible()
    await expect(timeout).toBeEnabled()
    await expect(modifiers.getByRole('radio', { name: 'Spike', exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    if (width === 1280) {
      const box = await timeout.boundingBox()
      const mode = await hurry.boundingBox()
      expect(Math.abs((box.y + box.height / 2) - (mode.y + mode.height / 2))).toBeLessThan(3)
    }
    await summary.focus()
    await page.keyboard.press('Enter')
    await page.getByTestId('new-drive').click()
    await expect(page.getByTestId('team-select')).toBeVisible()
    await expect(page.getByLabel('Control mode')).toBeVisible()
  })
}
