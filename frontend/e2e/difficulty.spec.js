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
      await route.continue({ postData: JSON.stringify({ ...body, seed: 7, mode: 'scrimmage', start_yards_to_goal: 31 }) })
    })
    await page.goto('/')
    await page.getByLabel('Control mode').selectOption('home')
    await page.getByLabel('Difficulty').selectOption(difficulty)
    await page.getByTestId('home-select').selectOption('2002/guidance-home')
    await page.getByTestId('away-select').selectOption('2002/guidance-away')
    const created = page.waitForResponse((response) => response.url().includes('/api/games?') && response.request().method() === 'POST')
    await page.getByTestId('start-game').click()
    const gameId = (await (await created).json()).game_id
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
