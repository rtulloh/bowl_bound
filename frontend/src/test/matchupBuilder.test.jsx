import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
  // Echo the requested season so any selected home year yields supported rules.
  api.getRules.mockImplementation((season, gameType) => Promise.resolve({
    season: Number(season),
    game_type: gameType,
    supported: true,
    summary: `${season} home-season rules govern this game.`,
    details: ['Kickoffs from the 30'],
  }))
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 7, view: view() })
})

async function setup({ waitForStart = true } = {}) {
  render(<App />)
  if (waitForStart) {
    await screen.findByTestId('start-game')
    // Start stays disabled until the matching rules summary arrives.
    await waitFor(() => expect(screen.getByTestId('start-game')).toBeEnabled())
  } else {
    await screen.findByTestId('team-select')
  }
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
  await waitFor(() => expect(screen.getByTestId('start-game')).toBeEnabled())
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
  await waitFor(() => expect(screen.getByTestId('start-game')).toBeEnabled())
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
  await setup({ waitForStart: false })
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

// --- Phase 2: searchable picker integration ---------------------------------

const largeCatalog = [
  ...catalog,
  ...Array.from({ length: 20 }, (_, index) => ({
    id: `2007/filler-${index}`,
    name: `Filler ${String(index).padStart(2, '0')}`,
    season: 2007,
  })),
]

it('searches within the selected year and picks from the combobox', async () => {
  api.listTeams.mockResolvedValue({ teams: largeCatalog, problems: [] })
  await setup()
  fireEvent.click(screen.getByRole('combobox', { name: 'Home team' }))
  fireEvent.change(screen.getByRole('combobox', { name: 'Home team' }), { target: { value: 'harbor' } })
  fireEvent.click(screen.getByRole('option', { name: 'Harbor Tech 2007' }))
  expect(screen.getByTestId('home-select')).toHaveValue('2007 Harbor Tech')
  expect(screen.getByTestId('home-season')).toHaveValue('2007')
})

it('choosing an all-seasons result updates that card year and team together', async () => {
  api.listTeams.mockResolvedValue({ teams: largeCatalog, problems: [] })
  await setup()
  fireEvent.click(screen.getByRole('combobox', { name: 'Home team' }))
  fireEvent.click(screen.getByRole('button', { name: /search all seasons/i }))
  fireEvent.change(screen.getByRole('combobox', { name: 'Home team' }), { target: { value: 'lakeside' } })
  fireEvent.click(screen.getByRole('option', { name: 'Lakeside 2012' }))
  expect(screen.getByTestId('home-season')).toHaveValue('2012')
  expect(screen.getByTestId('home-select')).toHaveValue('2012 Lakeside')
  // The away side keeps its own year and team.
  expect(screen.getByTestId('away-season')).toHaveValue('2007')
  expect(screen.getByTestId('away-select')).toHaveValue('2007 Harbor Tech')
})

// --- Phase 3: unsupported rules and catalog problems ------------------------

it('disables start and explains an unsupported home season', async () => {
  api.getRules.mockResolvedValue({
    season: 2007,
    game_type: 'regular',
    supported: false,
    summary: '2007 home-season rules are not supported; choose a season between 1940 and 2023.',
    details: [],
  })
  await setup({ waitForStart: false })
  const banner = await screen.findByTestId('rules-banner')
  expect(banner).toHaveAttribute('role', 'alert')
  expect(banner).toHaveTextContent('choose a season between 1940 and 2023')
  expect(screen.getByTestId('start-game')).toBeDisabled()
})

it('surfaces unavailable teams grouped by season instead of dropping them', async () => {
  api.listTeams.mockResolvedValue({
    teams: catalog,
    problems: [
      { id: '2012/broken-state', reason: 'could not be read' },
      { id: '2007/bad-tech', reason: 'could not be read' },
    ],
  })
  await setup()
  const note = screen.getByTestId('catalog-problems')
  expect(note).toHaveTextContent('Unavailable teams')
  expect(note).toHaveTextContent('2007')
  expect(note).toHaveTextContent('bad-tech')
  expect(note).toHaveTextContent('2012')
  expect(note).toHaveTextContent('broken-state')
  expect(note).toHaveTextContent('could not be read')
})

it('keeps the matchup populated and shows the backend message when creation fails', async () => {
  api.newGame.mockRejectedValue(new Error('home season 2007 is not supported'))
  await setup()
  fireEvent.click(screen.getByTestId('start-game'))
  expect(await screen.findByRole('alert')).toHaveTextContent('home season 2007 is not supported')
  expect(screen.getByTestId('home-select')).toHaveValue('2007/cedar-valley')
  expect(screen.getByTestId('away-select')).toHaveValue('2007/harbor-tech')
  await waitFor(() => expect(screen.getByTestId('start-game')).toBeEnabled())
})

it('keeps start disabled until a matching rules response arrives', async () => {
  let resolveRules
  api.getRules.mockImplementationOnce(() => new Promise((resolve) => { resolveRules = resolve }))
  await setup({ waitForStart: false })
  // Teams are selected, but rules are still pending: Start must stay disabled.
  expect(screen.getByTestId('start-game')).toBeDisabled()
  resolveRules({ season: 2007, game_type: 'regular', supported: true, summary: '2007 home-season rules govern this game.', details: [] })
  await screen.findByTestId('rules-banner')
  expect(screen.getByTestId('start-game')).toBeEnabled()
})

it('keeps start disabled when the rules request fails', async () => {
  api.getRules.mockRejectedValue(new Error('rules unavailable'))
  await setup({ waitForStart: false })
  expect(await screen.findByTestId('rules-error')).toHaveTextContent('rules unavailable')
  expect(screen.getByTestId('start-game')).toBeDisabled()
})

it('shows catalog problems even when no teams are readable', async () => {
  api.listTeams.mockResolvedValue({
    teams: [],
    problems: [{ id: '2007/bad-tech', reason: 'could not be read' }],
  })
  await setup({ waitForStart: false })
  expect(screen.getByText(/No teams were found/)).toBeInTheDocument()
  const note = screen.getByTestId('catalog-problems')
  expect(note).toHaveTextContent('bad-tech')
  expect(note).toHaveTextContent('could not be read')
})

it('recovers from a transient rules failure via Retry without changing the matchup', async () => {
  api.getRules.mockRejectedValueOnce(new Error('rules unavailable'))
  await setup({ waitForStart: false })
  expect(await screen.findByTestId('rules-error')).toHaveTextContent('rules unavailable')
  expect(screen.getByTestId('start-game')).toBeDisabled()

  fireEvent.click(screen.getByTestId('retry-rules'))
  await waitFor(() => expect(screen.getByTestId('start-game')).toBeEnabled())
  expect(screen.queryByTestId('rules-error')).toBeNull()
  expect(screen.getByTestId('home-select')).toHaveValue('2007/cedar-valley')
  expect(screen.getByTestId('away-select')).toHaveValue('2007/harbor-tech')
})

it('ignores a stale rules success that resolves after a newer selection', async () => {
  let resolveOld
  api.getRules.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
  await setup({ waitForStart: false })
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })
  pickTeam('home-select', '2012/harbor-tech')
  await waitFor(() => expect(screen.getByTestId('start-game')).toBeEnabled())
  // The superseded 2007 response must not overwrite the 2012 summary.
  resolveOld({ season: 2007, game_type: 'regular', supported: true, summary: '2007 home-season rules govern this game.', details: [] })
  await waitFor(() => expect(screen.getByTestId('rules-banner')).toHaveTextContent('2012 home-season rules govern this game.'))
})

it('ignores a stale rules failure that rejects after a newer selection', async () => {
  let rejectOld
  api.getRules.mockImplementationOnce(() => new Promise((_, reject) => { rejectOld = reject }))
  await setup({ waitForStart: false })
  fireEvent.change(screen.getByTestId('home-season'), { target: { value: '2012' } })
  pickTeam('home-select', '2012/harbor-tech')
  await waitFor(() => expect(screen.getByTestId('start-game')).toBeEnabled())
  rejectOld(new Error('stale failure'))
  await waitFor(() => expect(screen.queryByTestId('rules-error')).toBeNull())
  expect(screen.getByTestId('start-game')).toBeEnabled()
})
