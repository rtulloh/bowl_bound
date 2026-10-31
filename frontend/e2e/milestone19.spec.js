import { expect, test } from '@playwright/test'

async function select(page, home = '2002/alpha-tech', away = '2002/beta-state') {
  await page.route('**/api/games', async (route) => {
    await route.continue({ postData: JSON.stringify({ ...route.request().postDataJSON(), seed: 39 }) })
  })
  await page.goto('/')
  await page.getByLabel('Control mode').selectOption('manual')
  await page.getByTestId('home-select').selectOption(home)
  await page.getByTestId('away-select').selectOption(away)
  const created = page.waitForResponse((r) => r.url().endsWith('/api/games') && r.request().method() === 'POST')
  await page.getByTestId('start-game').click()
  return '/api/games/' + (await (await created).json()).game_id
}

for (const reverse of [false, true]) {
  test('original selectable samples finish with reconciled state and fresh selections, reversed=' + reverse, async ({ page }) => {
    test.setTimeout(180_000)
    const ids = ['2007/cedar-valley', '2007/harbor-tech']
    if (reverse) ids.reverse()
    const path = await select(page, ...ids)
    const phases = new Set()
    for (let step = 0; step < 1200; step++) {
      const view = (await (await page.request.get(path)).json()).view
      phases.add(view.phase)
      if (view.phase === 'opening_choice') {
        await expect(page.getByTestId('opening-screen')).toBeVisible()
        await expect(page.getByTestId('scoreboard')).toHaveCount(0)
        expect(view.clock.remaining).toBe(900)
      } else {
        await expect(page.getByTestId('game-clock')).toHaveText(view.clock.label)
      }
      if (view.finished) {
        expect(phases.has('halftime_choice')).toBe(true)
        expect(view.score.home).toBe(view.scoring.filter((e) => e.team === view.home).reduce((sum, e) => sum + e.points, 0))
        expect(view.score.away).toBe(view.scoring.filter((e) => e.team === view.away).reduce((sum, e) => sum + e.points, 0))
        await page.getByTestId('team-statistics').locator('summary').click()
        for (const row of view.statistics.rows) {
          const shown = page.getByTestId('team-statistics').getByRole('row').filter({ has: page.getByRole('rowheader', { name: row.label, exact: true }) })
          await expect(shown.getByRole('cell')).toHaveText([row.home, row.away])
        }
        await expect(page.getByTestId('snap')).toHaveCount(0)
        await expect(page.locator('[data-testid^=offense-play-]:enabled, [data-testid^=defense-play-]:enabled')).toHaveCount(0)
        return
      }
      let button
      if (view.pending && !view.clock_optional) {
        const panel = page.getByTestId(view.phase === "clock_choice" ? "clock-controls" : "penalty-choices")
        await expect(panel).toContainText(view.pending.chooser)
        if (view.phase !== "clock_choice") await expect(panel.locator("button:not(:disabled)").first()).toBeFocused()
        const enabled = view.pending.choices.filter((c) => c.enabled)
        const choice = ['half:receive', 'ot:offense', 'conversion:kick', 'kick:touchback']
          .map((id) => enabled.find((c) => c.id === id)).find(Boolean) || enabled[0]
        button = page.getByTestId('penalty-choice-' + choice.id)
      } else if (view.phase === 'kickoff') {
        button = page.getByTestId('special-play-kickoff')
      } else {
        await expect(page.getByTestId("offense-plays")).toContainText(view.state.possession_name)
        await expect(page.getByTestId("defense-plays")).toContainText(view.state.possession === "home" ? view.away : view.home)
        await expect(page.locator('[aria-pressed=true][data-testid*=play-]')).toHaveCount(0)
        await page.getByTestId('offense-play-' + (step % 9 + 1)).click()
        button = page.getByTestId('defense-play-' + 'abcdef'[step % 6])
      }
      await Promise.all([
        page.waitForResponse((r) => r.url().startsWith('http://127.0.0.1:8123' + path + '/') && r.request().method() === 'POST'),
        button.click(),
      ])
      await expect(page.getByRole('alert')).toHaveCount(0)
    }
    throw new Error('Original samples did not finish')
  })
}

test('coin, keyboard focus, semantic kick context, readable states and mobile fit', async ({ page }) => {
  await select(page)
  await expect(page.getByTestId('coin')).toBeVisible()
  const choices = page.getByTestId('penalty-choices')
  await expect(choices.locator('button').first()).toBeFocused()
  await page.keyboard.press('Enter')
  await page.getByTestId('special-play-kickoff').click()
  await expect(page.getByTestId('result-description')).toContainText('40 yards')
  await expect(page.getByTestId('result-description')).toContainText('returns 10 yards')
  await page.getByTestId('offense-play-1').click()
  await expect(page.getByTestId('offense-play-1')).toHaveAttribute('aria-pressed', 'true')
  const ratios = await page.locator('.board-panel, .play-button').evaluateAll((elements) => {
    const rgb = (value) => value.match(/[\d.]+/g).slice(0, 3).map(Number)
    const luminance = (channels) => channels.map((c) => {
      c /= 255
      return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
    }).reduce((sum, c, i) => sum + c * [0.2126, 0.7152, 0.0722][i], 0)
    return elements.filter((el) => el.getBoundingClientRect().height).map((el) => {
      const style = getComputedStyle(el)
      const foreground = luminance(rgb(style.color))
      const backgrounds = style.backgroundImage.match(/rgb\([^)]+\)/g) || [style.backgroundColor]
      return backgrounds.map((color) => {
        const background = luminance(rgb(color))
        return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
      })
    }).flat()
  })
  expect(ratios.length).toBeGreaterThan(5)
  expect(Math.min(...ratios)).toBeGreaterThanOrEqual(4.5)
  await page.getByTestId('special-play-punt').click()
  await expect(page.getByTestId('offense-play-1')).toBeDisabled()
  await expect(page.getByTestId('penalty-choice-kick:fair_catch')).toBeFocused()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('snap')).toHaveCount(0)
  await expect(page.getByTestId('offense-play-1')).toHaveAttribute('aria-pressed', 'false')
})

test('hurry mode remains selected across repeated eligible snaps and can be turned off', async ({ page }) => {
  await select(page)
  await page.getByTestId('penalty-choice-toss:kick').click()
  await page.getByTestId('special-play-kickoff').click()
  await page.getByRole('checkbox', { name: 'Hurry-up mode' }).check()
  await page.getByTestId('offense-play-1').click()
  await page.getByTestId('defense-play-a').click()
  await expect(page.getByTestId('game-clock')).toHaveText('14:50')
  await page.getByTestId('offense-play-1').click()
  await page.getByTestId('defense-play-a').click()
  await expect(page.getByTestId('game-clock')).toHaveText('14:30')
  await expect(page.getByRole('checkbox', { name: 'Hurry-up mode' })).toBeChecked()
  await page.getByTestId('offense-play-1').click()
  await page.getByTestId('defense-play-a').click()
  // The hurried snap itself has a 20-second duration; no second reduction is offered.
  await expect(page.getByTestId('game-clock')).toHaveText('14:10')
  await page.getByRole('checkbox', { name: 'Hurry-up mode' }).uncheck()
  await page.getByTestId('offense-play-1').click()
  await page.getByTestId('defense-play-a').click()
  await expect(page.getByTestId('game-clock')).toHaveText('13:40')
})
