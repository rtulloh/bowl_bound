import { expect, test } from '@playwright/test'

test('selects teams from different seasons independently and keeps both identities', async ({ page }) => {
  await page.route('**/api/games', async (route) => {
    const body = route.request().postDataJSON()
    await route.continue({ postData: JSON.stringify({ ...body, seed: 7 }) })
  })
  await page.goto('/')
  await expect(page.getByTestId('start-game')).toBeVisible()

  await page.getByTestId('home-season').selectOption('2007')
  await page.getByTestId('home-select').selectOption('2007/cedar-valley')
  await page.getByTestId('away-season').selectOption('2002')
  await page.getByTestId('away-select').selectOption('2002/alpha-tech')

  await expect(page.getByTestId('home-select')).toHaveValue('2007/cedar-valley')
  await expect(page.getByTestId('away-select')).toHaveValue('2002/alpha-tech')

  const created = page.waitForResponse((r) => r.url().includes('/api/games') && r.request().method() === 'POST')
  await page.getByTestId('start-game').click()
  const body = (await created).request().postDataJSON()
  expect(body.home).toBe('2007/cedar-valley')
  expect(body.away).toBe('2002/alpha-tech')
  await expect(page.getByTestId('opening-screen')).toBeVisible()
})

test('the swap button exchanges both complete selections', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('home-season').selectOption('2007')
  await page.getByTestId('home-select').selectOption('2007/cedar-valley')
  await page.getByTestId('away-season').selectOption('2002')
  await page.getByTestId('away-select').selectOption('2002/alpha-tech')

  await page.getByTestId('swap-sides').click()
  await expect(page.getByTestId('home-season')).toHaveValue('2002')
  await expect(page.getByTestId('home-select')).toHaveValue('2002/alpha-tech')
  await expect(page.getByTestId('away-season')).toHaveValue('2007')
  await expect(page.getByTestId('away-select')).toHaveValue('2007/cedar-valley')
})
