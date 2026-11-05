import { expect, test } from '@playwright/test'
for (const width of [1280, 1440]) {
  test(`board groups, dice and aligned offense at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 1280 ? 1000 : 1120 })
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption('manual')
    await page.getByTestId('start-game').click()
    await page.getByRole('button', { name: 'Charts', exact: true }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog.locator('.chart-offense-layout')).toBeVisible()
    for (const section of ['main', 'supplemental']) {
      const grid = dialog.locator(`table[data-section="${section}"]`)
      await expect(grid.locator('tbody tr')).toHaveCount(30)
      expect(await grid.locator('.chart-die-face').allTextContents()).toEqual(Array.from({ length: 30 }, (_, i) => String(i + 10)))
    }
    const main = dialog.locator('table[data-section="main"]')
    await expect(main.getByRole('columnheader', { name: 'Running Plays', exact: true })).toHaveAttribute('colspan', '4')
    await expect(main.getByRole('columnheader', { name: 'Option', exact: true })).toHaveAttribute('colspan', '1')
    await expect(main.getByRole('columnheader', { name: 'Passing Plays', exact: true })).toHaveAttribute('colspan', '4')
    const aligned = await dialog.locator('.chart-offense-layout').evaluate((element) => {
      const tables = element.querySelectorAll('table')
      return [...tables[0].querySelectorAll('tbody tr')].every((row, i) => Math.abs(row.getBoundingClientRect().top - tables[1].querySelectorAll('tbody tr')[i].getBoundingClientRect().top) < 1)
    })
    expect(aligned).toBe(true)
    expect(await main.locator('.chart-play-headings th').first().evaluate((e) => getComputedStyle(e).top)).toBe('24px')
    await dialog.getByRole('button', { name: 'Defense', exact: true }).click()
    await expect(dialog.locator('tbody[data-formation]')).toHaveCount(6)
    for (const letter of 'ABCDEF') {
      const group = dialog.locator(`tbody[data-formation="${letter}"]`)
      await expect(group.locator('tr')).toHaveCount(5)
      await expect(group.locator('.chart-formation')).toHaveAttribute('rowspan', '5')
      await expect(group.locator('.chart-formation')).toHaveAttribute('scope', 'rowgroup')
      expect(await group.locator('.chart-die-face').allTextContents()).toEqual(['1', '2', '3', '4', '5'])
      expect(await group.locator('.chart-formation-letter').evaluate((e) => parseFloat(getComputedStyle(e).fontSize))).toBeGreaterThanOrEqual(36)
    }
    const colors = await dialog.evaluate((element) => {
      const style = (selector) => getComputedStyle(element.querySelector(selector))
      return { head: style('thead th').backgroundColor, green: style('.chart-cell-green').backgroundColor, line: style('td').borderBottomColor }
    })
    expect(colors).toEqual({ head: 'rgb(255, 255, 255)', green: 'rgb(0, 255, 0)', line: 'rgb(0, 0, 0)' })
  })
}
