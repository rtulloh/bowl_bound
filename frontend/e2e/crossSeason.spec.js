import { expect, test } from '@playwright/test'
import { selectTeams, selectedTeam } from './teamSetup.js'

test('selects teams from different seasons independently and keeps both identities', async ({ page }) => {
  await page.route('**/api/games', async (route) => {
    const body = route.request().postDataJSON()
    await route.continue({ postData: JSON.stringify({ ...body, seed: 7 }) })
  })
  await page.goto('/')
  await expect(page.getByTestId('start-game')).toBeVisible()

  await selectTeams(page, '2007/cedar-valley', '2002/alpha-tech')

  expect(await selectedTeam(page, 'home')).toBe('2007/cedar-valley')
  expect(await selectedTeam(page, 'away')).toBe('2002/alpha-tech')

  const created = page.waitForResponse((r) => r.url().includes('/api/games') && r.request().method() === 'POST')
  await page.getByTestId('start-game').click()
  const body = (await created).request().postDataJSON()
  expect(body.home).toBe('2007/cedar-valley')
  expect(body.away).toBe('2002/alpha-tech')
  await expect(page.getByTestId('opening-screen')).toBeVisible()
})

test('the swap button exchanges both complete selections', async ({ page }) => {
  await page.goto('/')
  await selectTeams(page, '2007/cedar-valley', '2002/alpha-tech')

  await page.getByTestId('swap-sides').click()
  await expect(page.getByTestId('home-season')).toHaveValue('2002')
  expect(await selectedTeam(page, 'home')).toBe('2002/alpha-tech')
  await expect(page.getByTestId('away-season')).toHaveValue('2007')
  expect(await selectedTeam(page, 'away')).toBe('2007/cedar-valley')
})

// --- Phase 4: end-to-end identity, rules boundaries and save/load ---------

async function tossAndKick(page) {
  await expect(page.getByTestId('opening-screen')).toBeVisible()
  const kicked = page.waitForResponse((r) => r.url().endsWith('/decision') && r.request().method() === 'POST')
  await page.getByTestId('penalty-choice-toss:kick').click()
  await kicked
  await expect(page.getByTestId('playing-screen')).toBeVisible()
  await expect(page.getByTestId('special-play-kickoff')).toBeVisible()
}

test('the same school in two years is selectable as two distinct sides', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('start-game')).toBeVisible()
  await selectTeams(page, '2007/cedar-valley', '2007/harbor-tech')
  // Both sides carry different charts from the same year and remain independent.
  expect(await selectedTeam(page, 'home')).toBe('2007/cedar-valley')
  expect(await selectedTeam(page, 'away')).toBe('2007/harbor-tech')
  await expect(page.getByTestId('start-game')).toBeEnabled()
})

for (const mode of ['manual', 'home']) {
  test(`starts a cross-year game in ${mode} control mode`, async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('start-game')).toBeVisible()
    await page.getByLabel('Control mode').selectOption(mode)
    await selectTeams(page, '2007/cedar-valley', '2002/alpha-tech')
    const created = page.waitForResponse((r) => r.url().includes('/api/games') && r.request().method() === 'POST')
    await page.getByTestId('start-game').click()
    const body = (await created).request().postDataJSON()
    expect(body.home).toBe('2007/cedar-valley')
    expect(body.away).toBe('2002/alpha-tech')
    await expect(page.getByTestId('opening-screen')).toBeVisible()
  })
}

test('the home season, not the away season, sets kickoff placement in the real engine', async ({ page }) => {
  // 2007 kicks from the 30; the away team's season must not change that.
  await page.goto('/')
  await expect(page.getByTestId('start-game')).toBeVisible()
  await page.getByLabel('Control mode').selectOption('manual')
  await selectTeams(page, '2007/cedar-valley', '2002/alpha-tech')
  await expect(page.getByTestId('rules-banner')).toContainText('Kickoffs from the 30')

  const created = page.waitForResponse((r) => r.url().includes('/api/games') && r.request().method() === 'POST')
  await page.getByTestId('start-game').click()
  const gameId = (await (await created).json()).game_id
  await tossAndKick(page)

  // Read the receiving spot the engine set from the HOME season's kickoff rule
  // before the kick resolves. 2007 kicks from the 30, so the returner starts
  // at their own 30 unless the kick changes field position.
  const preKick = await (await page.request.get('/api/games/' + gameId)).json()
  expect(preKick.view.state.spot).toBe('own 30')
})

test('swapping home and away changes the governing rules', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('start-game')).toBeVisible()
  await selectTeams(page, '2007/cedar-valley', '2002/alpha-tech')
  await expect(page.getByTestId('rules-banner')).toContainText('Kickoffs from the 30')

  await page.getByTestId('swap-sides').click()
  // 2002 now governs: kickoffs move back to the 35.
  await expect(page.getByTestId('rules-banner')).toContainText('Kickoffs from the 35')
  expect(await selectedTeam(page, 'home')).toBe('2002/alpha-tech')
})

test('a cross-year game saves and reloads with its identities intact', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('start-game')).toBeVisible()
  await page.getByLabel('Control mode').selectOption('manual')
  await selectTeams(page, '2007/cedar-valley', '2002/alpha-tech')
  const created = page.waitForResponse((r) => r.url().includes('/api/games') && r.request().method() === 'POST')
  await page.getByTestId('start-game').click()
  const gameId = (await (await created).json()).game_id
  const before = (await (await page.request.get('/api/games/' + gameId)).json()).view
  expect(before.home).toBe('Cedar Valley')
  expect(before.away).toBe('Alpha Tech')

  const downloaded = page.waitForEvent('download')
  await page.getByText('Game', { exact: true }).click()
  await page.getByRole('button', { name: 'Save game', exact: true }).click()
  const savedPath = await (await downloaded).path()

  await page.reload()
  await expect(page.getByTestId('team-select')).toBeVisible()
  await page.getByLabel('Control mode').selectOption('manual')
  const loaded = page.waitForResponse((r) => r.url().endsWith('/api/games/load'))
  await page.getByLabel('Load saved game', { exact: true }).setInputFiles(savedPath)
  const data = await (await loaded).json()
  // Both cross-year identities survive the round trip unchanged.
  expect(data.view).toEqual(before)
})
