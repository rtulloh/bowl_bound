import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'

const seasons = process.env.BB_E2E_SEASONS || '/tmp/bowl-bound-e2e-seasons'
const other = (side) => side === 'home' ? 'away' : 'home'
const withoutTimingLabels = (entries) => entries.map(({ timing_label, ...report }) => report)

async function loadPeriodEnd(page, control, quarter, openingChoice) {
  // Keep Python's integer seeds and complete replay journal intact in the upload.
  const save = execFileSync('.venv/bin/python', [
    '-m', 'tests.period_fixtures', seasons, String(quarter), openingChoice,
  ], { cwd: '..', env: { ...process.env, PYTHONPATH: '.' } })
  await page.goto('/')
  await page.getByLabel('Control mode').selectOption(control)
  const response = page.waitForResponse((r) => r.url().includes('/api/games/load'))
  await page.getByLabel('Load saved game', { exact: true }).setInputFiles({
    name: 'synthetic-period-end.json', mimeType: 'application/json', buffer: save,
  })
  const loaded = await response
  expect(loaded.ok()).toBeTruthy()
  const body = await loaded.json()
  expect(body.view.clock.quarter).toBe(quarter)
  expect(body.view.clock.remaining).toBe(10)
  await expect(page.getByTestId('quarter')).toHaveText('Q' + quarter)
  await expect(page.getByTestId('game-clock')).toHaveText('0:10')
  return body
}

async function expirePeriod(page, body, control) {
  const completed = page.waitForResponse((r) =>
    r.url().includes('/api/games/' + body.game_id + '/') &&
    r.request().method() === 'POST')
  if (control === 'manual') {
    await page.getByTestId('offense-play-1').click()
    await page.getByTestId('defense-play-a').click()
  } else {
    await page.getByTestId(body.turn.human_role === 'offense'
      ? 'offense-play-1' : 'defense-play-a').click()
  }
  const response = await completed
  expect(response.ok()).toBeTruthy()
  return response.json()
}

for (const openingChoice of ['toss:receive', 'toss:kick']) {
  for (const control of ['manual', 'home', 'away']) {
    test(`halftime schedules and records one reciprocal kickoff: ${control}, ${openingChoice}`, async ({ page, request }) => {
      const initial = await loadPeriodEnd(page, control, 2, openingChoice)
      const kicker = other(initial.view.opening_kicker)
      const receiver = initial.view.opening_kicker
      const boundary = await expirePeriod(page, initial, control)
      expect(boundary.view.phase).toBe('kickoff')
      expect(boundary.view.clock).toMatchObject({ quarter: 3, remaining: 900, timeouts: [3, 3] })
      expect(boundary.view.state.possession).toBe(kicker)
      // The attempted next scrimmage call must not become a second-half snap.
      expect(withoutTimingLabels(boundary.view.log)).toEqual(withoutTimingLabels(initial.view.log))
      expect(initial.view.log.at(-1).timing_label).toBeTruthy()
      expect(boundary.view.log.at(-1).timing_label).toBeNull()

      if (control === 'manual' || control === kicker) {
        await expect(page.getByTestId('quarter')).toHaveText('Q3')
        await expect(page.getByTestId('special-play-kickoff')).toBeEnabled()
        await expect(page.getByTestId('offense-play-1')).toHaveCount(0)
        const kicked = page.waitForResponse((r) => r.url().includes('/kick'))
        await page.getByTestId('special-play-kickoff').click()
        expect((await kicked).ok()).toBeTruthy()
      } else {
        expect(boundary.turn.automatic).toBe(true)
      }

      const suffix = control === 'manual' ? '' : '?human_side=' + control
      let after
      await expect.poll(async () => {
        after = await (await request.get('/api/games/' + initial.game_id + suffix)).json()
        return [after.view.phase, after.view.log.length]
      }).toEqual(['scrimmage', initial.view.log.length + 1])
      expect(after.view.state.possession).toBe(receiver)
      expect(after.view.clock).toMatchObject({ quarter: 3, remaining: 890, timeouts: [3, 3] })
      const kickoff = after.view.log.at(-1)
      expect(kickoff.outcome).toBe('kickoff_return')
      expect(kickoff.state_before.possession).toBe(kicker)
      expect(kickoff.state_after.possession).toBe(receiver)
      expect(kickoff.trace.map((step) => step.section)).toEqual(['kickoff', 'kickoff_return'])
      expect(kickoff.trace.map((step) => step.cell)).toEqual(['40', '10'])
      await expect(page.getByTestId('quarter')).toHaveText('Q3')
      await expect(page.getByTestId('game-clock')).toHaveText('14:50')
      await expect(page.getByTestId('log-entry')).toHaveCount(initial.view.log.length + 1)
      const recorded = page.getByTestId('log-entry').last()
      await expect(recorded).toContainText(kickoff.commentary)
      await expect(recorded.getByLabel('Recorded dice')).toContainText('kickoff_return')
      await expect(page.getByRole('alert')).toHaveCount(0)

      // Reloading after the kickoff must preserve, rather than replay, the kick.
      const saved = await request.get('/api/games/' + initial.game_id + '/save')
      await page.reload()
      await page.getByLabel('Control mode').selectOption(control)
      const resumed = page.waitForResponse((r) => r.url().includes('/api/games/load'))
      await page.getByLabel('Load saved game', { exact: true }).setInputFiles({
        name: 'synthetic-second-half.json', mimeType: 'application/json', buffer: Buffer.from(await saved.text()),
      })
      const resumedResponse = await resumed
      expect(resumedResponse.ok()).toBeTruthy()
      expect((await resumedResponse.json()).view.log).toEqual(after.view.log)
      await expect(page.getByTestId('log-entry')).toHaveCount(after.view.log.length)
      await expect(page.getByTestId('special-play-kickoff')).toHaveCount(0)
    })
  }

  test(`Q1 expiry preserves possession without a kickoff: ${openingChoice}`, async ({ page }) => {
    const initial = await loadPeriodEnd(page, 'manual', 1, openingChoice)
    const boundary = await expirePeriod(page, initial, 'manual')
    expect(boundary.view.clock).toMatchObject({ quarter: 2, remaining: 900, timeouts: [1, 2] })
    expect(boundary.view.state.possession).toBe(initial.view.state.possession)
    expect(boundary.view.state.yards_to_goal).toBe(initial.view.state.yards_to_goal)
    expect(boundary.view.state.down).toBe(initial.view.state.down + 1)
    expect(boundary.view.phase).toBe('clock_choice')
    // Unlike halftime, a quarter break permits the selected next scrimmage play.
    expect(boundary.view.log).toHaveLength(initial.view.log.length + 1)
    expect(boundary.view.log.at(-1).called_play).toBe('Line Plunge')
    expect(boundary.view.log.at(-1).trace.map((step) => step.section)).not.toContain('kickoff')
    await expect(page.getByTestId('quarter')).toHaveText('Q2')
    await expect(page.getByTestId('special-play-kickoff')).toHaveCount(0)
    await expect(page.getByTestId('offense-play-1')).toBeEnabled()
  })
}
