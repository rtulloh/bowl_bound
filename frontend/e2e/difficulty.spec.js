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
    expect(body.coach_policy).toBe(difficulty + '-v1')
    expect(body.turn).not.toHaveProperty('computer_choice')
    expect(body).not.toHaveProperty('estimates')
    const saved = await request.get('/api/games/' + body.game_id + '/save')
    expect(saved.ok()).toBeTruthy()
    const text = await saved.text()
    expect(JSON.parse(text).config.coach_policy).toBe(difficulty + '-v1')
    // Preserve private 63-bit coaching seeds; do not round-trip saves through JS Numbers.
    const loaded = await request.post('/api/games/load', { data: text, headers: { 'Content-Type': 'application/json' } })
    expect(loaded.ok()).toBeTruthy()
    expect((await loaded.json()).coach_policy).toBe(difficulty + '-v1')
    await expect(page.getByText('Easy helper', { exact: false })).toHaveCount(0)
  })
}
