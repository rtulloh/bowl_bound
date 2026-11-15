import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import * as api from '../api'
import { view } from './fixtures'

vi.mock('../api', () => ({ listTeams: vi.fn(), getRules: vi.fn(), newGame: vi.fn(), snap: vi.fn(), decide: vi.fn(), kick: vi.fn(), gameAction: vi.fn(), coachStep: vi.fn(), getGame: vi.fn(), loadGame: vi.fn(), saveGame: vi.fn() }))

const catalog = [
  { id: '2007/cedar-valley', name: 'Cedar Valley', season: 2007 },
  { id: '2007/harbor-tech', name: 'Harbor Tech', season: 2007 },
  { id: '2012/harbor-tech', name: 'Harbor Tech', season: 2012 },
  { id: '2012/lakeside', name: 'Lakeside', season: 2012 },
]

beforeEach(() => {
  vi.resetAllMocks()
  api.listTeams.mockResolvedValue({ teams: catalog, problems: [] })
  api.getRules.mockResolvedValue({ season: 2007, game_type: 'regular', supported: true, summary: '2007 home-season rules govern this game.', details: ['Kickoffs from the 30'] })
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 7, view: view() })
})

async function setup() {
  render(<App />)
  await screen.findByTestId('start-game')
}

function pickTeam(testId, value) {
  fireEvent.change(screen.getByTestId(testId), { target: { value } })
}

it('defaults to the public sample matchup when those teams exist', async () => {
  await setup()
  expect(screen.getByTestId('home-season')).toHaveValue('2007')
  expect(screen.getByTestId('away-season')).toHaveValue('2007')
  expect(screen.getByTestId('home-select')).toHaveValue('2007/cedar-valley')
  expect(screen.getByTestId('away-select')).toHaveValue('2007/harbor-tech')
})

it('defaults to the newest season when the samples are absent', async () => {
  api.listTeams.mockResolvedValue({
    teams: catalog.filter((t) => !t.id.startsWith('2007/')),
    problems: [],
  })
  await setup()
  expect(screen.getByTestId('home-season')).toHaveValue('2012')
  expect(screen.getByTestId('away-season')).toHaveValue('2012')
  expect(screen.getByTestId('home-select')).toHaveValue('2012/harbor-tech')
  expect(screen.getByTestId('away-select')).toHaveValue('2012/lakeside')
})

it('changing the home season does not clear or restrict the away selection', async () => {
  await setup()
  fireEvent.change(screen.getByTestId('away-season'), { target: { value: '2012' } })
  pickTeam('away-select', '2012/lakeside')
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })

  expect(screen.getByTestId('away-season')).toHaveValue('2012')
  expect(screen.getByTestId('away-select')).toHaveValue('2012/lakeside')
  const awayOptions = within(screen.getByTestId('away-select')).getAllByRole('option')
  expect(awayOptions.map((o) => o.value)).toEqual(['', '2012/harbor-tech', '2012/lakeside'])
})

it('carries a team across years when the school exists and clears it otherwise', async () => {
  await setup()
  // Harbor Tech exists in 2012, so moving to that year keeps the same school.
  pickTeam('home-select', '2007/harbor-tech')
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })
  expect(screen.getByTestId('home-select')).toHaveValue('2012/harbor-tech')

  // Cedar Valley does not exist in 2012, so the selection clears with a notice.
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2007' } })
  pickTeam('home-select', '2007/cedar-valley')
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })
  expect(screen.getByTestId('home-select')).toHaveValue('')
  expect(screen.getByTestId('home-card')).toHaveTextContent('Choose a 2012 team for this side.')
})

it('allows the same school from different seasons on opposite sides', async () => {
  await setup()
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })
  fireEvent.change(screen.getByTestId('away-season'), { target: { value: '2007' } })
  pickTeam('home-select', '2012/harbor-tech')
  pickTeam('away-select', '2007/harbor-tech')
  expect(screen.getByTestId('home-select')).toHaveValue('2012/harbor-tech')
  expect(screen.getByTestId('away-select')).toHaveValue('2007/harbor-tech')
  expect(screen.getByTestId('start-game')).toBeEnabled()
})

it('swaps both complete selections without changing either identity', async () => {
  await setup()
  fireEvent.change(screen.getByTestId('away-season'), { target: { value: '2012' } })
  pickTeam('away-select', '2012/lakeside')
  fireEvent.click(screen.getByTestId('swap-sides'))
  expect(screen.getByTestId('home-season')).toHaveValue('2012')
  expect(screen.getByTestId('home-select')).toHaveValue('2012/lakeside')
  expect(screen.getByTestId('away-season')).toHaveValue('2007')
  expect(screen.getByTestId('away-select')).toHaveValue('2007/cedar-valley')
})

it('sends the unchanged setup payload with independent team IDs', async () => {
  await setup()
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })
  fireEvent.change(screen.getByTestId('away-season'), { target: { value: '2007' } })
  pickTeam('home-select', '2012/harbor-tech')
  pickTeam('away-select', '2007/cedar-valley')
  fireEvent.click(screen.getByTestId('start-game'))
  expect(api.newGame).toHaveBeenCalledWith(
    { home: '2012/harbor-tech', away: '2007/cedar-valley', mode: 'regulation', game_type: 'regular', difficulty: 'medium' },
    'home',
  )
})

it('keeps the selected season when its team is cleared, so it can be reselected', async () => {
  await setup()
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })
  pickTeam('home-select', '2012/lakeside')
  expect(screen.getByTestId('home-season')).toHaveValue('2012')

  pickTeam('home-select', '')
  expect(screen.getByTestId('home-season')).toHaveValue('2012')
  expect(screen.getByTestId('home-select')).toHaveValue('')
  expect(screen.getByTestId('start-game')).toBeDisabled()

  const options = within(screen.getByTestId('home-select')).getAllByRole('option').map((o) => o.value)
  expect(options).toEqual(['', '2012/harbor-tech', '2012/lakeside'])
  pickTeam('home-select', '2012/harbor-tech')
  expect(screen.getByTestId('home-select')).toHaveValue('2012/harbor-tech')
})

it('disables start until both sides have a team', async () => {
  await setup()
  pickTeam('home-select', '')
  expect(screen.getByTestId('start-game')).toBeDisabled()
})

it('offers a same-season shortcut only when the years differ', async () => {
  await setup()
  expect(screen.queryByTestId('same-season')).toBeNull()
  fireEvent.change(screen.getByTestId('away-season'), { target: { value: '2012' } })
  fireEvent.click(screen.getByTestId('same-season'))
  expect(screen.getByTestId('away-season')).toHaveValue('2007')
  expect(screen.queryByTestId('same-season')).toBeNull()
})

it('clears an opponent that does not exist in the home season instead of substituting one', async () => {
  await setup()
  fireEvent.change(screen.getByTestId('away-season'), { target: { value: '2012' } })
  pickTeam('away-select', '2012/lakeside')
  fireEvent.click(screen.getByTestId('same-season'))
  expect(screen.getByTestId('away-season')).toHaveValue('2007')
  expect(screen.getByTestId('away-select')).toHaveValue('')
  expect(screen.getByTestId('start-game')).toBeDisabled()
})

it('shows the backend rules summary for the home season', async () => {
  await setup()
  expect(await screen.findByTestId('rules-banner')).toHaveTextContent('2007 home-season rules govern this game.')
  expect(screen.getByTestId('rules-banner')).toHaveTextContent('Kickoffs from the 30')
})

it('does not show stale rules while a new home season is loading', async () => {
  let resolveRules
  api.getRules.mockImplementationOnce(() => Promise.resolve({ season: 2007, game_type: 'regular', supported: true, summary: '2007 home-season rules govern this game.', details: [] }))
  api.getRules.mockImplementationOnce(() => new Promise((resolve) => { resolveRules = resolve }))
  await setup()
  await screen.findByTestId('rules-banner')
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })
  expect(screen.queryByTestId('rules-banner')).toBeNull()
  resolveRules({ season: 2012, game_type: 'regular', supported: true, summary: '2012 home-season rules govern this game.', details: [] })
  expect(await screen.findByTestId('rules-banner')).toHaveTextContent('2012 home-season rules govern this game.')
})

it('labels teams with the season-qualified identity', async () => {
  await setup()
  const homeOption = within(screen.getByTestId('home-select')).getByRole('option', { name: '2007 Cedar Valley' })
  expect(homeOption).toHaveValue('2007/cedar-valley')
})
