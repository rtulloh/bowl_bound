import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import DiceRoll from '../components/DiceRoll'
import * as api from '../api'
import { view, report } from './fixtures'

vi.mock('../api', () => ({ listTeams: vi.fn(), newGame: vi.fn(), snap: vi.fn(), decide: vi.fn(), kick: vi.fn(), gameAction: vi.fn(), coachStep: vi.fn(), getGame: vi.fn(), loadGame: vi.fn(), saveGame: vi.fn() }))
const turn = (role, overrides = {}) => ({
  human_side: 'home', human_role: role, automatic: role === 'computer', status: 'Your private controls',
  actions: { offense: role === 'offense' ? view().actions.offense : [], defense: role === 'defense' ? view().actions.defense : [], special: [] },
  game_actions: [], pending: null, ...overrides,
})
beforeEach(() => {
  vi.resetAllMocks()
  api.listTeams.mockResolvedValue({ teams: [{ id: 'a', name: 'Alpha', season: 2007 }, { id: 'b', name: 'Beta', season: 2007 }] })
})
async function start(role, mode = 'home') {
  api.newGame.mockResolvedValue({ game_id: 'cpu', seed: 7, view: view(), turn: turn(role) })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: mode } })
  fireEvent.click(screen.getByTestId('start-game'))
}
it.each(['offense', 'defense'])('shows only the human %s and sends only that call', async (role) => {
  api.coachStep.mockResolvedValue({ report: report(), view: view(), turn: turn(role) })
  await start(role, role === 'offense' ? 'home' : 'away')
  fireEvent.click(await screen.findByTestId(role === 'offense' ? 'offense-play-1' : 'defense-play-a'))
  expect(screen.queryByTestId(role === 'offense' ? 'defense-plays' : 'offense-plays')).toBeNull()
  expect(screen.queryByRole('button', { name: /Pause computer|Resume computer|Retry computer/ })).toBeNull()
  expect(screen.queryByLabelText('Control mode')).toBeNull()
  expect(screen.queryByTestId('snap')).toBeNull()
  await waitFor(() => expect(api.coachStep).toHaveBeenCalledWith('cpu', role === 'offense' ? 'home' : 'away', role === 'offense' ? '1' : 'A'))
  expect(api.snap).not.toHaveBeenCalled()
})
it('automatically advances serialized computer actions and stops for the human decision', async () => {
  let finish
  api.coachStep.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
  await start('computer')
  await waitFor(() => expect(api.coachStep).toHaveBeenCalledTimes(1))
  fireEvent.click(screen.getByText('Game', { selector: 'summary' }))
  expect(screen.getByRole('button', { name: 'Save game' })).toBeDisabled()
  expect(screen.queryByRole('button', { name: /Pause computer|Resume computer|Retry computer/ })).toBeNull()
  await new Promise((resolve) => setTimeout(resolve, 350))
  expect(api.coachStep).toHaveBeenCalledTimes(1)
  finish({ view: view(), turn: turn('decision', { pending: { chooser: 'Alpha Tech', choices: [{ id: 'conversion:kick', label: 'Kick PAT', enabled: true }] } }) })
  expect(await screen.findByRole('button', { name: 'Kick PAT' })).toBeEnabled()
  await new Promise((resolve) => setTimeout(resolve, 350))
  expect(api.coachStep).toHaveBeenCalledTimes(1)
})
it('stops automatic requests on error and offers retry only while an error is shown', async () => {
  api.coachStep.mockRejectedValueOnce(new Error('Computer request failed'))
    .mockResolvedValueOnce({ view: view(), turn: turn('offense') })
  await start('computer')
  expect(await screen.findByRole('alert')).toHaveTextContent('Computer request failed')
  await new Promise((resolve) => setTimeout(resolve, 350))
  expect(api.coachStep).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('button', { name: /Pause computer|Resume computer/ })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Retry computer' }))
  await screen.findByTestId('offense-play-1')
  expect(api.coachStep).toHaveBeenCalledTimes(2)
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Retry computer' })).toBeNull()
})
it('does not auto-play a final game', async () => {
  api.newGame.mockResolvedValue({ game_id: 'cpu', view: view({ finished: true }), turn: turn('computer') })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'home' } })
  fireEvent.click(screen.getByTestId('start-game'))
  await screen.findByTestId('session-status')
  await new Promise((resolve) => setTimeout(resolve, 350))
  expect(api.coachStep).not.toHaveBeenCalled()
})
it('renders engine-supplied die labels, colors, faces and authoritative totals without inferring dice', () => {
  const { rerender } = render(<DiceRoll roll={{ faces: [0, 4], total: 99, dice_label: 'Recorded dice', dice: [
    { role: 'white_one', label: 'White 1', color: 'white', face: 0 },
    { role: 'white_two', label: 'White 2', color: 'white', face: 4 },
  ] }} />)
  expect(screen.getByLabelText('White 1: 0')).toHaveAttribute('data-die-color', 'white')
  expect(screen.getByLabelText('White 2: 4')).toBeInTheDocument()
  expect(screen.getByText('Total 99')).toBeInTheDocument()
  rerender(<DiceRoll roll={{ faces: [1, 2], total: 3 }} />)
  expect(screen.queryByLabelText('Red: 1')).toBeNull()
  expect(screen.getByText('1 + 2 = 3')).toBeInTheDocument()
})

it('never shows the opposing timeout control in optional clock modifiers', async () => {
  const own = [
    { id: 'clock:runoff', label: 'None', enabled: true },
    { id: 'clock:timeout:home', label: 'Home timeout', enabled: true },
  ]
  api.newGame.mockResolvedValue({ game_id: 'cpu', seed: 7,
    view: view({ phase: 'clock_choice', clock_optional: true, clock_modifiers: [...own, { id: 'clock:timeout:away', label: 'Away timeout', enabled: true }] }),
    turn: turn('offense', { pending: { chooser: 'Alpha Tech', choices: own } }),
  })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'home' } })
  fireEvent.click(screen.getByTestId('start-game'))
  expect(await screen.findByRole('radio', { name: 'Home timeout' })).toBeInTheDocument()
  expect(screen.queryByRole('radio', { name: 'Away timeout' })).toBeNull()
})
it('uses the explicitly selected coach mode on load without an in-game mode selector', async () => {
  await start('offense')
  await screen.findByTestId('offense-play-1')
  api.loadGame.mockResolvedValue({ game_id: 'loaded', seed: 7, view: view() })
  api.getGame.mockResolvedValue({ game_id: 'loaded', seed: 7, view: view(), turn: turn('defense') })
  fireEvent.click(screen.getByText('Game', { selector: 'summary' }))
  fireEvent.change(screen.getByLabelText('Load saved game'), { target: { files: [{ size: 20, text: async () => '{opaque}' }] } })
  await screen.findByTestId('defense-play-a')
  expect(api.getGame).toHaveBeenCalledWith('loaded', 'home')
  expect(screen.queryByLabelText('Control mode')).toBeNull()
  expect(screen.queryByTestId('offense-plays')).toBeNull()
  expect(api.coachStep).not.toHaveBeenCalled()
})

it('loads in manual mode when explicitly selected at setup', async () => {
  api.loadGame.mockResolvedValue({ game_id: 'loaded', seed: 7, view: view() })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.change(screen.getByLabelText('Load saved game'), { target: { files: [{ size: 20, text: async () => '{opaque}' }] } })
  await screen.findByTestId('defense-play-a')
  expect(screen.getByTestId('offense-play-1')).toBeInTheDocument()
  expect(screen.queryByLabelText('Control mode')).toBeNull()
  expect(api.getGame).not.toHaveBeenCalled()
  expect(api.coachStep).not.toHaveBeenCalled()
})

it('keeps the current game intact if preparing the loaded computer controls fails', async () => {
  await start('offense')
  await screen.findByTestId('offense-play-1')
  api.loadGame.mockResolvedValue({ game_id: 'loaded', seed: 7, view: view() })
  api.getGame.mockRejectedValue(new Error('Could not prepare computer controls'))
  fireEvent.click(screen.getByText('Game', { selector: 'summary' }))
  fireEvent.change(screen.getByLabelText('Load saved game'), { target: { files: [{ size: 20, text: async () => '{opaque}' }] } })
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not prepare computer controls')
  expect(screen.getByTestId('offense-play-1')).toBeInTheDocument()
  expect(screen.queryByTestId('defense-plays')).toBeNull()
  expect(api.coachStep).not.toHaveBeenCalled()
})

it('does not silently retry a failed computer turn when saving the stopped game', async () => {
  api.coachStep.mockRejectedValueOnce(new Error('Computer request failed'))
  api.saveGame.mockResolvedValue('{opaque}')
  vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:save'), revokeObjectURL: vi.fn() })
  const download = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  try {
    await start('computer')
    expect(await screen.findByRole('alert')).toHaveTextContent('Computer request failed')
    fireEvent.click(screen.getByText('Game', { selector: 'summary' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save game' }))
    await waitFor(() => expect(download).toHaveBeenCalledTimes(1))
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 350)) })
    expect(api.coachStep).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Retry computer' })).toBeInTheDocument()
  } finally {
    download.mockRestore()
    vi.unstubAllGlobals()
  }
})

it('starts human home/computer away without changing the default selection', async () => {
  api.newGame.mockResolvedValue({ game_id: 'cpu', seed: 7, view: view(), turn: turn('offense') })
  render(<App />)
  fireEvent.click(await screen.findByTestId('start-game'))
  await screen.findByTestId('offense-play-1')
  expect(api.newGame).toHaveBeenCalledWith({ home: 'a', away: 'b', mode: 'regulation', game_type: 'regular', difficulty: 'medium' }, 'home')
  expect(screen.queryByTestId('defense-plays')).toBeNull()
})

it('loads with human home controls by default without changing the selection', async () => {
  api.loadGame.mockResolvedValue({ game_id: 'loaded', seed: 7, view: view() })
  api.getGame.mockResolvedValue({ game_id: 'loaded', seed: 7, view: view(), turn: turn('defense') })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Load saved game'), { target: { files: [{ size: 20, text: async () => '{opaque}' }] } })
  await screen.findByTestId('defense-play-a')
  expect(api.getGame).toHaveBeenCalledWith('loaded', 'home')
  expect(screen.queryByTestId('offense-plays')).toBeNull()
  expect(api.coachStep).not.toHaveBeenCalled()
})

it.each([['scrimmage', 'offense'], ['scrimmage', 'defense'], ['clock_choice', 'offense']])('removes the routine scoreboard prompt from the visual layout, phase=%s role=%s', async (phase, role) => {
  api.newGame.mockResolvedValue({ game_id: 'cpu', seed: 7,
    view: view({ phase, clock_optional: phase === 'clock_choice' }), turn: turn(role),
  })
  render(<App />)
  fireEvent.click(await screen.findByTestId('start-game'))
  expect(await screen.findByTestId('session-status')).toHaveClass('sr-only')
  expect(screen.getByText('Choose your play to resolve it. Computer calls stay hidden until resolution.')).toBeVisible()
})

it.each([['kickoff', 'offense', false], ['conversion_choice', 'decision', false], ['final', 'offense', true]])('keeps contextual status messages visible, phase=%s', async (phase, role, finished) => {
  api.newGame.mockResolvedValue({ game_id: 'cpu', seed: 7,
    view: view({ phase, finished }), turn: turn(role, { status: 'Engine context' }),
  })
  render(<App />)
  fireEvent.click(await screen.findByTestId('start-game'))
  const status = await screen.findByTestId('session-status')
  expect(status).not.toHaveClass('sr-only')
  expect(status).toHaveTextContent('Engine context')
})

it.each(['easy', 'medium', 'hard'])('submits %s difficulty without adding a browser helper', async (difficulty) => {
  api.newGame.mockResolvedValue({ game_id: 'cpu', seed: 7, view: view(), turn: turn('offense') })
  render(<App />)
  await screen.findByTestId('start-game')
  const select = screen.getByLabelText('Difficulty')
  expect(select).toHaveValue('medium')
  expect(Array.from(select.options, (option) => option.textContent)).toEqual(['Easy (0.3)', 'Medium (0.5)', 'Hard (0.7)'])
  fireEvent.change(select, { target: { value: difficulty } })
  fireEvent.click(screen.getByTestId('start-game'))
  await waitFor(() => expect(api.newGame).toHaveBeenCalledWith(expect.objectContaining({ difficulty }), 'home'))
  expect(screen.queryByText(/Easy helper/)).toBeNull()
})
