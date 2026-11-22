import { readFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'
import { selectTeams } from '../e2e/teamSetup.js'

test('a static worker game resumes after reload and imports its export in a fresh context', async ({ browser, page }, testInfo) => {
  const apiRequests = []
  const errors = []
  const observe = (tab) => {
    tab.on('request', request => {
      if (new URL(request.url()).pathname.startsWith('/api/')) apiRequests.push(request.url())
    })
    tab.on('pageerror', error => errors.push(error.message))
  }
  observe(page)
  await page.goto('/dist-browser/')
  await page.getByLabel('Control mode').selectOption('manual')
  await selectTeams(page, '2007/cedar-valley', '2007/harbor-tech')
  await page.getByTestId('start-game').click()
  await page.getByTestId('penalty-choice-toss:kick').click()
  await page.getByTestId('special-play-kickoff').click()
  await expect(page.getByTestId('log-entry').first()).toBeVisible()
  await expect(page.getByText('Game saved locally.', { exact: true })).toBeVisible()

  const clock = await page.getByTestId('game-clock').textContent()
  const summary = await page.getByTestId('log-entry').first().textContent()
  const expectCheckpoint = async (tab) => {
    await expect(tab.getByTestId('game-clock')).toHaveText(clock)
    await expect(tab.getByTestId('log-entry').first()).toHaveText(summary)
  }

  await page.reload()
  await page.getByText('Saved games', { selector: 'summary' }).click()
  await page.getByRole('button', { name: /^Resume / }).click()
  await expectCheckpoint(page)

  await page.getByText('Game', { selector: 'summary', exact: true }).click()
  const [download] = await Promise.all([
    page.waitForEvent('download'), page.getByRole('button', { name: 'Export game', exact: true }).click(),
  ])
  const bytes = await readFile(await download.path())
  const exported = JSON.parse(bytes)
  expect(exported).toMatchObject({ format: 'bowl-bound-browser-game', version: 1, humanSide: 'manual' })
  expect(typeof exported.checkpoint).toBe('string')

  const fresh = await browser.browserType().launch({
    channel: testInfo.project.use.channel,
    ...testInfo.project.use.launchOptions,
  })
  try {
    const restored = await fresh.newPage()
    observe(restored)
    await restored.goto(new URL('/dist-browser/', page.url()).href)
    await restored.getByLabel('Import saved game').setInputFiles({
      name: 'bowl-bound-save.json', mimeType: 'application/json', buffer: bytes,
    })
    await expectCheckpoint(restored)
    await expect(restored.getByText('Game saved locally.', { exact: true })).toBeVisible()
  } finally {
    await fresh.close()
  }
  expect(apiRequests).toEqual([])
  expect(errors).toEqual([])
})
