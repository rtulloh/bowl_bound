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
