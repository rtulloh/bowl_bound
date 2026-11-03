import { test, expect } from '@playwright/test'

for (const difficulty of ['easy', 'medium', 'hard']) {
  test('difficulty ' + difficulty + ' reaches the real engine and survives save/load', async ({ page, request }) => {
    await page.goto('/')
    await expect(page.getByLabel('Difficulty')).toHaveValue('medium')
    await page.getByLabel('Difficulty').selectOption(difficulty)
    await page.getByTestId('home-select').selectOption('2002/alpha-tech')
    await page.getByTestId('away-select').selectOption('2002/beta-state')
    const created = page.waitForResponse((response) => response.url().includes('/api/games?') && response.request().method() === 'POST')
    await page.getByTestId('start-game').click()
    const response = await created
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    expect(body.difficulty).toBe(difficulty)
    expect(body.turn).not.toHaveProperty('computer_choice')
    expect(body).not.toHaveProperty('estimates')
    const saved = await request.get('/api/games/' + body.game_id + '/save')
    expect(saved.ok()).toBeTruthy()
    const text = await saved.text()
    expect(JSON.parse(text).config.difficulty).toBe(difficulty)
    // Preserve private 63-bit coaching seeds; do not round-trip saves through JS Numbers.
    const loaded = await request.post('/api/games/load', { data: text, headers: { 'Content-Type': 'application/json' } })
    expect(loaded.ok()).toBeTruthy()
    expect((await loaded.json()).difficulty).toBe(difficulty)
    await expect(page.getByText('Easy helper', { exact: false })).toHaveCount(0)
  })
}


for (const difficulty of ['easy', 'medium', 'hard']) {
  test('fourth-down public guidance ' + difficulty + ' comes from the real engine', async ({ page, request }) => {
    await page.route('**/api/games?*', async (route) => {
      const body = route.request().postDataJSON()
      await route.continue({ postData: JSON.stringify({ ...body, seed: 7, mode: 'drive', start_yards_to_goal: 31 }) })
    })
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption('home')
    await page.getByLabel('Difficulty').selectOption(difficulty)
    await page.getByTestId('home-select').selectOption('2002/guidance-home')
    await page.getByTestId('away-select').selectOption('2002/guidance-away')
    const created = page.waitForResponse((response) => response.url().includes('/api/games?') && response.request().method() === 'POST')
    await page.getByTestId('start-game').click()
    const createdResponse = await created
    expect(createdResponse.ok()).toBeTruthy()
    const initial = await createdResponse.json()
    expect(initial.view.phase).toBe('scrimmage')
    const gameId = initial.game_id
    await expect(page.getByTestId('offense-play-1')).toBeVisible()
    await expect(page.getByRole('region', { name: 'Fourth-down guidance' })).toHaveCount(0)
    let body
    for (let index = 0; index < 3; index += 1) {
      const completed = page.waitForResponse((response) => response.url().endsWith('/coach'))
      await page.getByTestId('offense-play-1').click()
      const response = await completed
      expect(response.ok()).toBeTruthy()
      body = await response.json()
    }
    const guidance = body.view.fourth_down_guidance
    expect(guidance.action).toBe('field_goal')
    expect(guidance.attempt_distance).toBe(48)
    await expect(page.getByText(guidance.label, { exact: true })).toBeVisible()
    await expect(page.getByText(guidance.summary, { exact: true })).toBeVisible()
    const saved = await request.get('/api/games/' + gameId + '/save')
    const loaded = await request.post('/api/games/load?human_side=home', { data: await saved.text(), headers: { 'Content-Type': 'application/json' } })
    expect(loaded.ok()).toBeTruthy()
    expect((await loaded.json()).view.fourth_down_guidance).toEqual(guidance)
    const kicked = page.waitForResponse((response) => response.url().includes('/kick?'))
    await page.getByTestId('special-play-field_goal').click()
    expect((await kicked).ok()).toBeTruthy()
    await expect(page.getByRole('region', { name: 'Fourth-down guidance' })).toHaveCount(0)
  })
}


for (const side of ['home', 'away']) {
  test('next-play timeout is side-owned after kickoff for human ' + side, async ({ page, request }) => {
    const created = await request.post('/api/games', { data: { home: '2002/guidance-home', away: '2002/guidance-away', mode: 'regulation', seed: 7, difficulty: 'medium' } })
    expect(created.ok()).toBeTruthy()
    const gameId = (await created.json()).game_id
    expect((await request.post('/api/games/' + gameId + '/decision', { data: { choice: 'toss:kick' } })).ok()).toBeTruthy()
    const kicked = await request.post('/api/games/' + gameId + '/kick', { data: { action: 'kickoff' } })
    expect(kicked.ok()).toBeTruthy()
    const before = (await kicked.json()).view
    const initial = await request.get('/api/games/' + gameId + '/save')
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption(side)
    const loadedResponse = page.waitForResponse((response) => response.url().includes('/api/games/load?'))
    await page.getByLabel('Load saved game', { exact: true }).setInputFiles({ name: 'synthetic.json', mimeType: 'application/json', buffer: Buffer.from(await initial.text()) })
    const loaded = await (await loadedResponse).json()
    const other = side === 'home' ? 'away' : 'home'
    await expect(page.getByTestId('game-play-timeout_after:' + other)).toHaveCount(0)
    const actionResponse = page.waitForResponse((response) => response.url().includes('/action?'))
    await page.getByTestId('game-play-timeout_after:' + side).click()
    const armed = await (await actionResponse).json()
    expect(armed.report).toBeNull()
    expect(armed.view.clock).toEqual(before.clock)
    expect(armed.view.armed_timeout).toBe(side)
    expect(armed.view.conditional_timeout).toBe(true)
    await expect(page.getByText(armed.view.armed_timeout_label, { exact: true })).toBeVisible()
    const text = await (await request.get('/api/games/' + loaded.game_id + '/save')).text()
    await page.reload()
    await page.getByLabel('Control mode').selectOption(side)
    const resumedResponse = page.waitForResponse((response) => response.url().includes('/api/games/load?'))
    await page.getByLabel('Load saved game', { exact: true }).setInputFiles({ name: 'armed.json', mimeType: 'application/json', buffer: Buffer.from(text) })
    const resumed = await (await resumedResponse).json()
    expect(resumed.view.armed_timeout).toBe(side)
    await expect(page.getByText(armed.view.armed_timeout_label, { exact: true })).toBeVisible()
    const calledResponse = page.waitForResponse((response) => response.url().endsWith('/coach'))
    await page.getByTestId(side === 'home' ? 'offense-play-1' : 'defense-play-a').click()
    expect((await calledResponse).ok()).toBeTruthy()
    // A concealed CPU RZDZ call may require the human's result choice. Finish
    // actual engine continuations while proving the intent stays on this play.
    for (let step = 0; step < 4; step += 1) {
      let current
      await expect.poll(async () => {
        current = await (await request.get('/api/games/' + resumed.game_id + '?human_side=' + side)).json()
        return current.turn.automatic
      }).toBe(false)
      if (current.view.armed_timeout === null) break
      expect(current.view.conditional_timeout).toBe(true)
      expect(current.view.clock).toEqual(before.clock)
      expect(current.view.timing_log).toEqual(before.timing_log)
      expect(current.turn.human_role).toBe('decision')
      const choice = current.turn.pending.choices.find((entry) => entry.enabled)
      expect(choice).toBeTruthy()
      const decisionResponse = page.waitForResponse((response) => response.url().includes('/decision?'))
      await page.getByTestId('penalty-choice-' + choice.id).click()
      expect((await decisionResponse).ok()).toBeTruthy()
    }
    await expect(page.getByText(armed.view.armed_timeout_label, { exact: true })).toHaveCount(0)
    const after = await (await request.get('/api/games/' + resumed.game_id + '?human_side=' + side)).json()
    expect(after.view.armed_timeout).toBeNull()
    expect(after.view.conditional_timeout).toBe(false)
    await expect(page.getByTestId('play-log')).toContainText(after.view.log.at(-1).timing_label)
    expect(after.view.clock.remaining).toBe(before.clock.remaining - 10)
    expect(after.view.clock.timeouts).toEqual(side === 'home' ? [2, 3] : [3, 2])
    expect(after.view.timing_log.at(-1).method).toBe('timeout:' + side)
  })
}

for (const choice of ['interception:return', 'interception:decline']) {
  test('conditional timeout follows the CPU pass through ' + choice + ' without spending on natural timing', async ({ page, request }) => {
    const created = await request.post('/api/games', { data: {
      home: '2002/timeout-home', away: '2002/guidance-away', mode: 'regulation', seed: 7, coach_policy: 'baseline-v2',
    } })
    expect(created.ok()).toBeTruthy()
    const path = '/api/games/' + (await created.json()).game_id
    expect((await request.post(path + '/decision', { data: { choice: 'toss:kick' } })).ok()).toBeTruthy()
    const kicked = await request.post(path + '/kick', { data: { action: 'kickoff' } })
    expect(kicked.ok()).toBeTruthy()
    const before = (await kicked.json()).view
    const saved = await request.get(path + '/save')
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption('away')
    const loadedResponse = page.waitForResponse((response) => response.url().includes('/api/games/load?'))
    await page.getByLabel('Load saved game', { exact: true }).setInputFiles({ name: 'synthetic.json', mimeType: 'application/json', buffer: Buffer.from(await saved.text()) })
    await loadedResponse
    const selectedResponse = page.waitForResponse((response) => response.url().includes('/action?'))
    await page.getByTestId('game-play-timeout_after:away').click()
    const selected = await (await selectedResponse).json()
    expect(selected.view.clock).toEqual(before.clock)
    const playedResponse = page.waitForResponse((response) => response.url().endsWith('/coach'))
    await page.getByTestId('defense-play-a').click()
    const pending = await (await playedResponse).json()
    expect(pending.report.pending).toBe(true)
    expect(pending.turn.human_role).toBe('decision')
    expect(pending.view.conditional_timeout).toBe(true)
    expect(pending.report.timing_label).toBeNull()
    expect(pending.view.armed_timeout_label).not.toContain('armed')
    await expect(page.getByText(pending.view.armed_timeout_label, { exact: true })).toBeVisible()
    const finalResponse = page.waitForResponse((response) => response.url().includes('/decision?'))
    await page.getByTestId('penalty-choice-' + choice).click()
    const final = await (await finalResponse).json()
    expect(final.report.pending).toBe(false)
    expect(final.view.conditional_timeout).toBe(false)
    expect(final.view.armed_timeout).toBeNull()
    expect(final.view.clock.timeouts).toEqual([3, 3])
    expect(final.view.clock.remaining).toBe(before.clock.remaining - 10)
    expect(final.view.timing_log.at(-1).play_number).toBe(final.report.number)
    expect(final.view.timing_log.at(-1).method).toBe('standard')
    await expect(page.getByText(pending.view.armed_timeout_label, { exact: true })).toHaveCount(0)
  })
}
