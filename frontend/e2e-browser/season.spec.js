import { expect, test } from '@playwright/test'

const cedar = 'Cedar Valley (2007)'
const harbor = 'Harbor Tech (2007)'

async function openSeasons(page) {
  await page.getByRole('button', { name: 'Seasons', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Seasons' })).toBeVisible()
}

async function createSeason(page) {
  await page.getByLabel('Season name').fill('Saturday doubleheader')
  for (const team of [cedar, harbor]) {
    await page.getByLabel(team, { exact: true }).check()
    await page.getByLabel(team + ' conference', { exact: true }).fill('Synthetic Conference')
  }
  await page.getByLabel('Game 1 away team').selectOption('2007/harbor-tech')
  await page.getByLabel('Game 1 home team').selectOption('2007/cedar-valley')
  await page.getByLabel('Conference game').check()
  await page.getByRole('button', { name: 'Add fixture' }).click()
  await page.getByLabel('Game 2 week').fill('2')
  await page.getByLabel('Game 2 away team').selectOption('2007/cedar-valley')
  await page.getByLabel('Game 2 home team').selectOption('2007/harbor-tech')
  await page.getByLabel('Conference game').last().check()
  await page.getByRole('button', { name: 'Create season' }).click()
  await expect(page.getByLabel('Saved season').locator('option:checked')).toHaveText('Saturday doubleheader')
}

async function finishFixture(page) {
  // Drive only actions offered by the real worker. Use native browser clicks to
  // advance each play without waiting for animation/stability on every snap.
  await page.waitForFunction(() => {
    const game = document.querySelector('[data-testid="playing-screen"], [data-testid="opening-screen"]')
    if (!game) return false
    const error = game.querySelector('[role="alert"]')
    if (error) throw new Error(error.textContent)
    if (game.querySelector('#final-heading')) return true
    const pending = game.querySelector('[data-testid="penalty-choices"] button:enabled')
    const review = game.querySelector('[role="region"] > button.play-button:enabled')
    const offense = game.querySelector('button[data-testid^="offense-play-"]:enabled')
    const defense = game.querySelector('button[data-testid^="defense-play-"]:enabled')
    const normalCall = offense && defense && (
      offense.getAttribute('aria-pressed') === 'true' ? defense : offense
    )
    const special = game.querySelector(
      'button[data-testid="special-play-kickoff"]:enabled, button[data-testid^="special-play-"]:enabled',
    )
    const clock = game.querySelector('[data-testid="clock-controls"] input:enabled:not(:checked)')
    const action = pending || review || normalCall || special || clock
    action?.click()
    return false
  }, undefined, { timeout: 30_000 })
  await expect(page.getByText('Final result recorded.')).toBeVisible()
  const stats = page.getByTestId('team-statistics').getByRole('row', { name: /Total offense yards/ }).getByRole('cell')
  const homeYards = Number(await stats.nth(0).textContent())
  const awayYards = Number(await stats.nth(1).textContent())
  const homeScore = Number(await page.getByTestId('home-score').textContent())
  const awayScore = Number(await page.getByTestId('away-score').textContent())
  await page.getByRole('button', { name: 'Return to seasons' }).click()
  return { homeYards, awayYards, homeScore, awayScore }
}

test('a browser season resumes after reload and reconciles two conference finals to season totals', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/dist-browser/')
  await openSeasons(page)
  await createSeason(page)

  await page.getByLabel('Control team for new games').selectOption('manual')
  await page.getByRole('button', { name: 'Play game', exact: true }).first().click()
  await page.getByTestId('penalty-choice-toss:kick').click()
  await page.getByTestId('special-play-kickoff').click()
  await expect(page.getByTestId('log-entry').first()).toBeVisible()
  await page.getByText('Game', { selector: 'summary', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Return to seasons' })).toBeEnabled()

  const clock = await page.getByTestId('game-clock').textContent()
  const kickoff = await page.getByTestId('log-entry').first().textContent()
  await page.getByRole('button', { name: 'Return to seasons' }).click()
  await expect(page.getByRole('button', { name: 'Resume game', exact: true })).toBeVisible()
  await page.reload()
  await openSeasons(page)

  await expect(page.getByText('Conference game', { exact: false })).toHaveCount(2)
  await expect(page.getByRole('button', { name: 'Play game', exact: true })).toHaveCount(1)
  await page.getByRole('button', { name: 'Resume game', exact: true }).click()
  await expect(page.getByTestId('game-clock')).toHaveText(clock)
  await expect(page.getByTestId('log-entry').first()).toHaveText(kickoff)

  const first = await finishFixture(page)
  await page.getByLabel('Control team for new games').selectOption('manual')
  await page.getByRole('button', { name: 'Play game', exact: true }).click()
  const second = await finishFixture(page)
  await page.reload()
  await openSeasons(page)
  const schedule = page.getByRole('region', { name: 'Season schedule' })
  await expect(schedule.getByText('Final', { exact: false })).toHaveCount(2)
  const [gameOne, gameTwo] = await schedule.getByRole('listitem').all()
  await expect(gameOne).toContainText(`${first.awayScore}–${first.homeScore}`)
  await expect(gameTwo).toContainText(`${second.awayScore}–${second.homeScore}`)

  await page.getByRole('button', { name: 'Team statistics', exact: true }).click()
  const teamRows = page.getByRole('table', { name: 'Season team statistics' })
  for (const [name, yards] of [[cedar, first.homeYards + second.awayYards], [harbor, first.awayYards + second.homeYards]]) {
    const cells = teamRows.getByRole('row').filter({ has: page.getByRole('rowheader', { name, exact: true }) }).getByRole('cell')
    await expect(cells.nth(0)).toHaveText('2')
    await expect(cells.nth(1)).toHaveText(String(yards))
  }

  await page.getByRole('button', { name: 'Standings', exact: true }).click()
  await page.getByLabel('Conference', { exact: true }).selectOption('Synthetic Conference')
  const standings = page.getByRole('table', { name: 'Synthetic Conference' })
  const cedarRecord = standings.getByRole('row').filter({ has: page.getByRole('rowheader', { name: cedar, exact: true }) }).getByRole('cell')
  await expect(cedarRecord.nth(2)).toHaveText(String(first.homeScore + second.awayScore))
  await expect(cedarRecord.nth(3)).toHaveText(String(first.awayScore + second.homeScore))

  await page.getByRole('button', { name: 'Rankings', exact: true }).click()
  const ranks = page.getByRole('table', { name: 'Season rankings' }).locator('tbody tr')
  await expect(ranks).toHaveCount(2)
  for (const rank of await ranks.all()) {
    await expect(rank.getByRole('cell').nth(2)).toHaveText('50.0%')
  }
})
