import { expect, test } from '@playwright/test'

for (const human of ['home', 'away']) {
  for (const reverse of [false, true]) {
    test(`baseline computer game reconciles: human=${human}, reversed=${reverse}`, async ({ page }) => {
      test.setTimeout(240_000)
      const ids = ['2007/cedar-valley', '2007/harbor-tech']
      if (reverse) ids.reverse()
      await page.route('**/api/games?human_side=*', async (route) => {
        await route.continue({ postData: JSON.stringify({ ...route.request().postDataJSON(), seed: 39 }) })
      })
      await page.goto('/')
      await page.getByTestId('home-select').selectOption(ids[0])
      await page.getByTestId('away-select').selectOption(ids[1])
      await expect(page.getByLabel('Control mode')).toHaveValue('home')
      if (human !== 'home') await page.getByLabel('Control mode').selectOption(human)
      const created = page.waitForResponse((r) => r.url().includes('/api/games?') && r.request().method() === 'POST')
      await page.getByTestId('start-game').click()
      const data = await (await created).json()
      const path = '/api/games/' + data.game_id
      const roles = new Set()
      const calls = new Set()
      const responseErrors = []
      const callsSent = []
      page.on('response', (response) => { if (response.url().includes(path) && response.status() >= 400) responseErrors.push(response.status()) })
      page.on('request', (request) => {
        if (request.url().endsWith(path + '/coach')) callsSent.push(request.postDataJSON())
      })
      for (let step = 0; step < 1400; step++) {
        const current = await (await page.request.get(path + '?human_side=' + human)).json()
        const { view, turn } = current
        expect(Object.keys(turn).sort()).toEqual(['actions', 'automatic', 'game_actions', 'human_role', 'human_side', 'pending', 'status'])
        expect(JSON.stringify(current)).not.toContain('computer_choice')
        expect(JSON.stringify(current)).not.toContain('coach_seed')
        roles.add(turn.human_role)
        if (view.finished) {
          await expect(page.getByTestId('snap')).toHaveCount(0)
          await expect(page.locator('[data-testid^=offense-play-]:enabled, [data-testid^=defense-play-]:enabled')).toHaveCount(0)
          expect(roles.has('offense')).toBe(true)
          expect(roles.has('defense')).toBe(true)
          expect(roles.has('computer')).toBe(true)
          expect(calls.size).toBeGreaterThanOrEqual(6)
          expect(responseErrors).toEqual([])
          expect(callsSent.length).toBeGreaterThan(50)
          for (const body of callsSent) expect(Object.keys(body).sort()).toEqual(['human_call', 'human_side'])
          for (const quarter of [1, 2, 3, 4]) expect(view.timing_log.filter((t) => t.quarter === quarter).reduce((sum, t) => sum + t.before - t.after, 0)).toBe(900)
          for (const side of ['home', 'away']) expect(view.score[side]).toBe(view.scoring.filter((e) => e.team === view[side]).reduce((sum, e) => sum + e.points, 0))
          await page.getByTestId('team-statistics').locator('summary').click()
          for (const row of view.statistics.rows) {
            const shown = page.getByTestId('team-statistics').getByRole('row').filter({ has: page.getByRole('rowheader', { name: row.label, exact: true }) })
            await expect(shown.getByRole('cell')).toHaveText([row.home, row.away])
          }
          return
        }
        if (turn.automatic) {
          await expect.poll(async () => (await (await page.request.get(path + '?human_side=' + human)).json()).turn.automatic).toBe(false)
          continue
        }
        await expect(page.getByTestId('session-status')).toHaveText(turn.status)
        await expect(page.getByLabel('Control mode')).toHaveCount(0)
        await expect(page.getByRole('button', { name: /Pause computer|Resume computer/ })).toHaveCount(0)
        await expect(page.getByTestId('snap')).toHaveCount(0)
        await expect(page.getByRole('alert')).toHaveCount(0)
        let button
        if (turn.human_role === 'decision') {
          const enabled = turn.pending.choices.filter((c) => c.enabled)
          const choice = ['clock:runoff', 'toss:receive', 'half:receive', 'ot:offense', 'conversion:kick', 'kick:touchback'].map((id) => enabled.find((c) => c.id === id)).find(Boolean) || enabled[0]
          button = view.phase === 'clock_choice' ? page.getByTestId('clock-continue') : page.getByTestId('penalty-choice-' + choice.id)
        } else if (!turn.actions.offense.length && turn.human_role === 'offense') {
          button = page.getByTestId('special-play-' + turn.actions.special[0].key)
        } else {
          const offense = turn.human_role === 'offense'
          await expect(page.getByTestId(offense ? 'defense-plays' : 'offense-plays')).toHaveCount(0)
          const key = offense ? String(step % 9 + 1) : 'abcdef'[step % 6]
          button = page.getByTestId((offense ? 'offense-play-' : 'defense-play-') + key)
        }
        const response = page.waitForResponse((r) => r.url().includes(path + '/') && r.request().method() === 'POST')
        await button.click()
        const result = await (await response).json()
        expect(result.report?.supported ?? true).toBe(true)
        for (const entry of result.report?.trace || []) {
          expect(entry.roll.dice.map((die) => die.face)).toEqual(entry.roll.faces)
          expect(entry.roll.dice.map((die) => die.color)).toEqual(entry.roll.faces.length === 3 ? ['black', 'white', 'white'] : ['red', 'green'])
        }
        if (result.report && turn.human_role === 'defense') calls.add(result.report.called_play)
        if (result.report && turn.human_role === 'offense') calls.add(result.report.defense)
        if (result.report?.trace?.length && !result.turn.automatic) {
          const shown = page.getByLabel('Observed play dice')
          await expect(shown.getByRole('img').first()).toBeVisible()
        }
      }
      throw new Error('Computer game failed to finish')
    })
  }
}
