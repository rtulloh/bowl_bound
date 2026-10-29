import { expect, test } from '@playwright/test'

async function expectReadable(locator) {
  const contrast = await locator.evaluate((element) => {
    const luminance = (color) => {
      const channels = color.match(/[\d.]+/g).slice(0, 3).map((value) => {
        const channel = Number(value) / 255
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
      })
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722
    }
    let background = element
    while (getComputedStyle(background).backgroundColor === 'rgba(0, 0, 0, 0)') {
      background = background.parentElement
    }
    const foreground = luminance(getComputedStyle(element).color)
    const behind = luminance(getComputedStyle(background).backgroundColor)
    return (Math.max(foreground, behind) + 0.05) / (Math.min(foreground, behind) + 0.05)
  })
  expect(contrast).toBeGreaterThanOrEqual(4.5)
}

async function start(page) {
  // Fix only the request seed, never a response or engine result.
  await page.route('**/api/games', async (route) => {
    const body = route.request().postDataJSON()
    await route.continue({ postData: JSON.stringify({ ...body, seed: 7 }) })
  })
  await page.goto('/')
  await page.getByLabel('Control mode').selectOption('manual')
  await page.getByTestId('home-select').selectOption('2002/alpha-tech')
  await page.getByTestId('away-select').selectOption('2002/beta-state')
  await page.getByTestId('start-game').click()
  await expect(page.getByTestId('opening-screen')).toBeVisible()
  await expect(page.getByTestId('scoreboard')).toHaveCount(0)
  // Seed 7: Away wins the real toss and elects to kick.
  await page.getByTestId('penalty-choice-toss:kick').click()
  await expect(page.getByTestId('quarter')).toHaveText('Q1')
  await expect(page.getByTestId('game-clock')).toHaveText('15:00')
  await page.getByTestId('special-play-kickoff').click()
  await expect(page.getByTestId('possession')).toHaveText('Alpha Tech')
  await expect(page.getByTestId('spot')).toHaveText('own 35')
  await expect(page.getByTestId('game-clock')).toHaveText('14:50')
}

async function snapPlay(page, offense = '1', defense = 'a') {
  await page.getByTestId('offense-play-' + offense).click()
  const response = page.waitForResponse((r) => r.url().endsWith('/snap') && r.request().method() === 'POST')
  await page.getByTestId('defense-play-' + defense).click()
  await response
}

async function continueClock(page, choice = 'clock:runoff') {
  if (choice === 'clock:runoff') {
    // Explicit compatibility decisions are exercised elsewhere; ordinary UI play needs no click.
    await expect(page.getByRole('radio', { name: 'None', exact: true })).toBeChecked()
  } else {
    await page.locator(`input[type="radio"][value="${choice}"]`).click()
  }
}

test('ordinary next snaps need no clock confirmation and timeout does not persist', async ({ page }) => {
  await start(page)
  await expect(page.getByTestId('snap')).toHaveCount(0)
  await snapPlay(page)
  await expect(page.getByTestId('result-description')).toContainText('gain of 6 yards')
  await expect(page.getByTestId('situation')).toHaveText('2nd and 4')
  await expect(page.getByTestId('spot')).toHaveText('own 41')
  await expect(page.getByTestId('trace').locator('li')).toHaveCount(2)
  await expect(page.getByTestId('log-entry')).toHaveCount(2)
  const logged = page.getByTestId('log-entry').last()
  await expect(logged.locator('div').first()).toContainText('Line Plunge vs A Standard')
  await expect(logged.locator('div').first()).not.toContainText('Formation')
  await expect(logged.getByLabel('Recorded dice')).toBeVisible()
  await expect(logged.getByLabel('Recorded dice')).toContainText('offense: [')
  await expect(logged.getByLabel('Recorded dice')).toContainText('defense: [')
  await expectReadable(logged.getByLabel('Recorded dice'))
  await expect(logged).toContainText('Before: Alpha Tech — 1st and 10 at own 35')
  await expect(logged).toContainText('After: Alpha Tech — 2nd and 4 at own 41')
  await expect(logged).toContainText('Recorded yardage: 6')
  await logged.locator('summary').click()
  await expect(logged.locator('details')).toHaveAttribute('open', '')
  await expect(logged.locator('details li')).toHaveCount(2)
  await expect(logged.locator('details')).toContainText('cell')
  await expect(page.getByTestId('offense-play-1')).toBeEnabled()
  await expect(page.getByTestId('offense-play-1')).toHaveAttribute('aria-pressed', 'false')
  await expect(page.getByTestId('defense-play-a')).toHaveAttribute('aria-pressed', 'false')
  await expect(page.getByTestId('clock-continue')).toHaveCount(0)
  await continueClock(page, 'clock:timeout:away')
  await expect(page.getByTestId('game-clock')).toHaveText('14:40')
  await expect(page.getByTestId('away-timeouts')).toContainText('2')
  await snapPlay(page)
  await expect(page.getByRole('radio', { name: 'None', exact: true })).toBeChecked()
  await snapPlay(page)
  await expect(page.getByTestId('game-clock')).toHaveText('14:20')
  await expect(page.getByTestId('away-timeouts')).toContainText('2')
})

test('an interception waits for an engine-owned choice and charges ten seconds once', async ({ page }) => {
  await start(page)
  await snapPlay(page, '9')
  await expect(page.getByTestId('penalty-choice-interception:decline')).toBeVisible()
  const event = page.getByTestId('result-panel').getByText('Interception decision', { exact: true })
  await expect(event).toBeVisible()
  await expectReadable(event)
  await expect(page.locator('[data-testid^=offense-play-]:enabled, [data-testid^=defense-play-]:enabled')).toHaveCount(0)
  await page.getByTestId('penalty-choice-interception:decline').click()
  await expect(page.getByTestId('situation')).toHaveText('2nd and 10')
  await expect(page.getByTestId('spot')).toHaveText('own 35')
  await expect(page.getByTestId('game-clock')).toHaveText('14:40')
  await expect(page.getByTestId('log-entry').last().getByLabel('Play highlights')).toHaveCount(0)
})

test('the page shows only engine wording', async ({ page }) => {
  await start(page)
  const body = await page.locator('body').innerText()
  for (const paydirtLabel of ['Ln-Plg', 'O-Tkl', 'Sneak']) expect(body).not.toContain(paydirtLabel)
  await expect(page.getByTestId('game-play-kneel')).toContainText('Kneel')
})

test('PI acceptance updates engine state and clock once', async ({ page }) => {
  await start(page)
  await snapPlay(page, '8')
  await expect(page.getByTestId('game-clock')).toHaveText('14:50')
  await expect(page.getByTestId('penalty-choice-decline')).toHaveText('Decline penalties: incomplete pass')
  await page.getByTestId('penalty-choice-accept:0:previous').click()
  await expect(page.getByTestId('spot')).toHaveText('own 43')
  await expect(page.getByTestId('game-clock')).toHaveText('14:40')
  await expect(page.getByTestId('log-entry')).toHaveCount(2)
})

test('a punt waits for reception and commits a fair catch through the real engine', async ({ page }) => {
  await start(page)
  await page.getByTestId('special-play-punt').click()
  await expect(page.getByTestId('spot')).toHaveText('own 35')
  await page.getByTestId('penalty-choice-kick:fair_catch').click()
  await expect(page.getByTestId('possession')).toHaveText('Beta State')
  await expect(page.getByTestId('situation')).toHaveText('1st and 10')
  await expect(page.getByTestId('game-clock')).toHaveText('14:40')
  await expect(page.getByTestId('trace').locator('li')).toHaveCount(1)
})

for (const conversion of ['kick', 'two']) {
  test('touchdown and CONVERSION conversion schedule the real post-score kickoff'.replace('CONVERSION', conversion), async ({ page }) => {
    await start(page)
    for (let number = 1; number <= 11; number++) {
      await snapPlay(page)
      await expect(page.getByTestId('log-entry')).toHaveCount(number + 1)
      if (number < 11) await continueClock(page)
    }
    await expect(page.getByTestId('home-score')).toHaveText('6')
    await expect(page.getByTestId('result-panel').getByText('Touchdown', { exact: true })).toBeVisible()
    const badge = page.getByTestId('log-entry').last().getByText('Touchdown', { exact: true })
    await expect(badge).toBeVisible()
    await expectReadable(badge)
    await expect(page.getByTestId('session-status')).toContainText('choose a one-point kick or two-point try')
    await page.getByTestId('penalty-choice-conversion:' + conversion).click()
    if (conversion === 'two') {
      await expect(page.getByTestId('spot')).toHaveText('opponent 2')
      await expect(page.getByTestId('special-play-punt')).toHaveCount(0)
      await snapPlay(page)
      await expect(page.getByTestId('home-score')).toHaveText('8')
    } else {
      await expect(page.getByTestId('home-score')).toHaveText('7')
    }
    await expect(page.getByTestId('scoring-event')).toHaveCount(2)
    await expect(page.getByTestId('session-status')).toContainText('Kickoff required')
    await expect(page.getByTestId('special-play-kickoff')).toBeEnabled()
    await expect(page.getByTestId('snap')).toHaveCount(0)
    await expect(page.getByTestId('log-entry')).toHaveCount(13)
  })
}

test('hurry and spike are exclusive engine choices, with automatic kneel available', async ({ page }) => {
  await start(page)
  await snapPlay(page)
  await continueClock(page, 'clock:hurry')
  await expect(page.getByTestId('game-clock')).toHaveText('14:30')
  await expect(page.getByTestId('clock-controls')).toHaveCount(0)
  await snapPlay(page)
  await continueClock(page, 'clock:spike')
  await expect(page.getByTestId('game-clock')).toHaveText('14:20')
  await expect(page.getByTestId('situation')).toHaveText('2nd and 10')
  await page.getByTestId('game-play-kneel').click()
  await expect(page.getByTestId('result-description')).toContainText('Kneel; -2 yards')
  await snapPlay(page)
  await expect(page.getByTestId('game-clock')).toHaveText('13:50')
})


test('a complete regulation game shows quarter and half transitions and cannot reopen', async ({ page }) => {
  test.setTimeout(120_000)
  const created = page.waitForResponse((r) => r.url().endsWith('/api/games') && r.request().method() === 'POST')
  await start(page)
  const gameId = (await (await created).json()).game_id
  const path = '/api/games/' + gameId
  const quarters = new Set()
  let halfSeen = false
  for (let step = 0; step < 600; step++) {
    const view = (await (await page.request.get(path)).json()).view
    quarters.add(view.clock.quarter)
    await expect(page.getByTestId('quarter')).toHaveText(view.clock.quarter_label)
    await expect(page.getByTestId('game-clock')).toHaveText(view.clock.label)
    if (view.finished) {
      expect([...quarters]).toEqual([1, 2, 3, 4])
      expect(halfSeen).toBe(true)
      expect(view.clock.remaining).toBe(0)
      expect(view.score.home).toBe(view.scoring.filter((e) => e.team === view.home).reduce((n, e) => n + e.points, 0))
      expect(view.score.away).toBe(view.scoring.filter((e) => e.team === view.away).reduce((n, e) => n + e.points, 0))
      await expect(page.getByTestId('snap')).toHaveCount(0)
      await expect(page.locator('[data-testid^=offense-play-]:enabled, [data-testid^=defense-play-]:enabled')).toHaveCount(0)
      const refused = await page.request.post(path + '/decision', { data: { choice: 'clock:timeout:home' } })
      expect(refused.status()).toBe(409)
      expect((await (await page.request.get(path)).json()).view).toEqual(view)
      return
    }
    let button
    if (view.pending && !view.clock_optional) {
      if (view.phase === 'halftime_choice') {
        halfSeen = true
        expect(view.pending.chooser).toBe('Alpha Tech')
        expect(view.clock.remaining).toBe(0)
      }
      const choice = view.pending.choices.find((c) => c.id === 'clock:runoff') || view.pending.choices.find((c) => c.enabled)
      button = view.phase === 'clock_choice'
        ? page.getByTestId('clock-continue')
        : page.getByTestId('penalty-choice-' + choice.id)
    } else if (view.phase === 'kickoff') {
      button = page.getByTestId('special-play-kickoff')
    } else if (view.overtime?.series_number === 2 && view.phase === 'scrimmage') {
      button = page.getByTestId('game-play-kneel')
    } else {
      await page.getByTestId('offense-play-1').click()
      button = page.getByTestId('defense-play-a')
    }
    await Promise.all([
      page.waitForResponse((r) => r.url().includes(path + '/') && r.request().method() === 'POST'),
      button.click(),
    ])
  }
  throw new Error('Synthetic regulation did not terminate')
})


test('optional modifiers fit desktop/mobile without a routine Continue step', async ({ page }) => {
  await start(page)
  await snapPlay(page)
  const controls = page.getByRole('region', { name: 'Play modifiers' })
  await expect(page.getByTestId('clock-controls')).toBeVisible()
  await expect(controls).toBeVisible()
  await expect(page.getByRole('radio', { name: 'None', exact: true })).toBeChecked()
  await expect(page.getByTestId('offense-play-1')).toBeEnabled()
  await expect(page.getByTestId('defense-play-a')).toBeEnabled()
  await expect(page.getByTestId('clock-continue')).toHaveCount(0)
  expect((await controls.boundingBox()).height).toBeLessThan(85)
  await page.setViewportSize({ width: 390, height: 844 })
  const mobile = await controls.boundingBox()
  expect(mobile.height).toBeLessThan(130)
  expect(mobile.x + mobile.width).toBeLessThanOrEqual(390)
  await snapPlay(page)
  await expect(page.getByTestId('offense-play-1')).toBeVisible()
  await expect(page.getByTestId('game-clock')).toHaveText('14:20')
})


test('tied regulation continues into untimed overtime and finishes without a kickoff', async ({ page }) => {
  test.setTimeout(120_000)
  const created = page.waitForResponse((r) => r.url().endsWith('/api/games') && r.request().method() === 'POST')
  await start(page)
  const path = '/api/games/' + (await (await created).json()).game_id
  let overtimeSeen = false
  for (let step = 0; step < 600; step++) {
    const view = (await (await page.request.get(path)).json()).view
    if (view.finished) {
      expect(overtimeSeen).toBe(true)
      expect(view.score.home === view.score.away).toBe(false)
      await expect(page.getByTestId('session-status')).toContainText('Final: overtime')
      await expect(page.getByTestId('special-play-kickoff')).toHaveCount(0)
      await expect(page.getByTestId('snap')).toHaveCount(0)
      return
    }
    let button
    if (view.phase === 'overtime_choice') {
      expect(view.score.home).toBe(0)
      expect(view.score.away).toBe(0)
      button = page.getByTestId('penalty-choice-ot:offense')
    } else if (view.overtime && !overtimeSeen) {
      overtimeSeen = true
      await expect(page.getByTestId('quarter')).toHaveText('OT1')
      await expect(page.getByTestId('game-clock')).toHaveText('Untimed')
      await expect(page.getByTestId('spot')).toHaveText('opponent 25')
      await expect(page.getByTestId('clock-controls')).toHaveCount(0)
      button = page.getByTestId('game-play-timeout:home')
    } else if (view.pending && !view.clock_optional) {
      const choice = view.pending.choices.find((c) => c.id === 'clock:runoff') || view.pending.choices.find((c) => c.enabled)
      button = view.phase === 'clock_choice' ? page.getByTestId('clock-continue') : page.getByTestId('penalty-choice-' + choice.id)
    } else if (view.phase === 'kickoff') {
      button = page.getByTestId('special-play-kickoff')
    } else {
      if (view.overtime?.series_number === 1) {
        await page.getByTestId('offense-play-1').click()
        button = page.getByTestId('defense-play-a')
      } else {
        button = page.getByTestId('game-play-kneel')
      }
    }
    await Promise.all([
      page.waitForResponse((r) => r.url().includes(path + '/') && r.request().method() === 'POST'),
      button.click(),
    ])
  }
  throw new Error('Synthetic overtime game did not terminate')
})


test('team statistics show committed real-engine offense, excluding a pending interception', async ({ page }) => {
  const created = page.waitForResponse((r) => r.url().endsWith('/api/games') && r.request().method() === 'POST')
  await start(page)
  const path = '/api/games/' + (await (await created).json()).game_id
  const summary = page.getByTestId('team-statistics')
  await summary.locator('summary').click()
  await snapPlay(page)
  await snapPlay(page, '6')
  const before = (await (await page.request.get(path)).json()).view.statistics
  expect(before.home.rushing_attempts).toBe(1)
  expect(before.home.passing_attempts).toBe(1)
  expect(before.home.completions).toBe(1)
  expect(before.home.total_yards).toBe(12)
  expect(before.home.total_plays).toBe(2)
  for (const row of before.rows) {
    const displayed = summary.getByRole('row').filter({ has: page.getByRole('rowheader', { name: row.label, exact: true }) })
    await expect(displayed.getByRole('cell')).toHaveText([row.home, row.away])
  }
  await snapPlay(page, '9')
  expect((await (await page.request.get(path)).json()).view.statistics).toEqual(before)
  await page.getByTestId('penalty-choice-interception:decline').click()
  const after = (await (await page.request.get(path)).json()).view.statistics
  expect(after.home.passing_attempts).toBe(2)
  expect(after.home.completions).toBe(1)
  expect(after.home.total_plays).toBe(3)
  expect(after.home.total_yards).toBe(12)
  const plays = summary.getByRole('row').filter({ has: page.getByRole('rowheader', { name: 'Total offensive plays', exact: true }) })
  await expect(plays.getByRole('cell')).toHaveText(['3', '0'])
})


test('download and load resume a pending interception after a page refresh with identical future dice', async ({ page }) => {
  const created = page.waitForResponse((r) => r.url().endsWith('/api/games') && r.request().method() === 'POST')
  await start(page)
  const originalPath = '/api/games/' + (await (await created).json()).game_id
  await snapPlay(page, '9')
  const before = (await (await page.request.get(originalPath)).json()).view
  const downloaded = page.waitForEvent('download')
  await page.getByText('Game', { exact: true }).click()
  await page.getByRole('button', { name: 'Save game', exact: true }).click()
  const file = await downloaded
  expect(file.suggestedFilename()).toBe('bowl-bound-save.json')
  const savedPath = await file.path()
  await page.reload()
  await expect(page.getByTestId('team-select')).toBeVisible()
  await page.getByLabel('Control mode').selectOption('manual')
  const loaded = page.waitForResponse((r) => r.url().endsWith('/api/games/load'))
  await page.getByLabel('Load saved game', { exact: true }).setInputFiles(savedPath)
  const data = await (await loaded).json()
  const resumedPath = '/api/games/' + data.game_id
  expect(data.view).toEqual(before)
  await expect(page.getByTestId('penalty-choice-interception:return')).toBeVisible()
  await expect(page.locator('[data-testid^=offense-play-]:enabled, [data-testid^=defense-play-]:enabled')).toHaveCount(0)
  const original = await page.request.post(originalPath + '/decision', { data: { choice: 'interception:return' } })
  const continued = page.waitForResponse((r) => r.url().endsWith(resumedPath + '/decision'))
  await page.getByTestId('penalty-choice-interception:return').click()
  expect(await (await continued).json()).toEqual(await original.json())
  await expect(page.getByTestId('possession')).toHaveText('Beta State')
  await expect(page.getByTestId('game-clock')).toHaveText('14:40')
  await expect(page.getByTestId('offense-play-1')).toHaveAttribute('aria-pressed', 'false')
  await expect(page.getByTestId('defense-play-a')).toHaveAttribute('aria-pressed', 'false')
})

test('invalid save upload leaves the visible game and choices intact', async ({ page }) => {
  await start(page)
  await page.getByTestId('offense-play-1').click()
  await page.getByText('Game', { exact: true }).click()
  const loaded = page.waitForResponse((r) => r.url().endsWith('/api/games/load'))
  await page.getByLabel('Load saved game', { exact: true }).setInputFiles({
    name: 'invalid.json', mimeType: 'application/json', buffer: Buffer.from('{"private":"not a save"}'),
  })
  expect((await loaded).status()).toBe(422)
  await expect(page.getByRole('alert')).toContainText('Save is invalid')
  await expect(page.getByTestId('possession')).toHaveText('Alpha Tech')
  await expect(page.getByTestId('game-clock')).toHaveText('14:50')
  await expect(page.getByTestId('offense-play-1')).toHaveAttribute('aria-pressed', 'true')
  await page.keyboard.press('Escape')
  await page.getByTestId('defense-play-a').click()
  await expect(page.getByTestId('situation')).toHaveText('2nd and 4')
})
