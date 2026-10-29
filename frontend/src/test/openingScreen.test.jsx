import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import * as api from '../api'
import { view } from './fixtures'

vi.mock('../api', () => ({ listTeams: vi.fn(), newGame: vi.fn(), snap: vi.fn(), decide: vi.fn(), kick: vi.fn(), gameAction: vi.fn(), coachStep: vi.fn(), getGame: vi.fn(), loadGame: vi.fn(), saveGame: vi.fn() }))
const pending = { chooser: 'Alpha Tech', choices: [
  { id: 'toss:kick', label: 'Kick', enabled: true },
  { id: 'toss:receive', label: 'Receive', enabled: true },
] }
const opening = () => view({ phase: 'opening_choice', pending, status: 'Alpha Tech won the opening toss; choose kick or receive.' })
const kickoff = () => view({ phase: 'kickoff', pending: null, actions: { offense: [], defense: [], special: [{ key: 'kickoff', label: 'Kickoff' }] } })
const turn = (role, extra = {}) => ({ human_side: 'home', human_role: role, automatic: role === 'computer', status: 'Engine turn status', actions: { offense: [], defense: [], special: [] }, game_actions: [], pending: role === 'decision' ? pending : null, ...extra })
beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })))
  api.listTeams.mockResolvedValue({ teams: [{ id: 'a', name: 'Alpha', season: 2007 }, { id: 'b', name: 'Beta', season: 2007 }] })
})
afterEach(() => vi.unstubAllGlobals())
async function start(mode = 'home', role = 'decision') {
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 7, view: opening(), turn: turn(role) })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: mode } })
  fireEvent.click(screen.getByTestId('start-game'))
  await screen.findByTestId('opening-screen')
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    await waitFor(() => expect(screen.queryByTestId('toss-flipping')).toBeNull(), { timeout: 300 })
  }
}
function expectOnlyOpening() {
  expect(screen.getByTestId('opening-screen')).toBeInTheDocument()
  expect(screen.queryByTestId('playing-screen')).toBeNull()
  expect(screen.queryByTestId('quarter')).toBeNull()
  expect(screen.queryByTestId('result-empty')).toBeNull()
  expect(screen.queryByTestId('team-statistics')).toBeNull()
  expect(screen.queryByRole('region', { name: 'Play modifiers' })).toBeNull()
}
it.each(['manual', 'home'])('shows a separate toss screen then enters kickoff after the engine decision, mode=%s', async (mode) => {
  api.decide.mockResolvedValue({ view: kickoff(), turn: turn('offense', { actions: kickoff().actions }) })
  await start(mode)
  expectOnlyOpening()
  const kick = screen.getByRole('button', { name: 'Kick', exact: true })
  expect(kick).toHaveFocus()
  expect(screen.getByRole('button', { name: 'Receive', exact: true })).toBeVisible()
  fireEvent.click(kick)
  await screen.findByTestId('playing-screen')
  expect(api.decide).toHaveBeenCalledWith(...(mode === 'manual' ? ['game', 'toss:kick'] : ['game', 'toss:kick', 'home']))
  expect(screen.queryByTestId('coin-toss')).toBeNull()
  const kickoffButton = screen.getByTestId('special-play-kickoff')
  expect(kickoffButton).toBeVisible()
  expect(kickoffButton.compareDocumentPosition(screen.getByTestId('football-field')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})
it('keeps a failed toss decision on its screen with retry and game management available', async () => {
  api.decide.mockRejectedValue(new Error('Decision failed'))
  await start()
  fireEvent.click(screen.getByRole('button', { name: 'Receive', exact: true }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Decision failed')
  expectOnlyOpening()
  expect(screen.getByRole('button', { name: 'Receive', exact: true })).toBeEnabled()
  fireEvent.click(screen.getByText('Game', { selector: 'summary' }))
  expect(screen.getByRole('button', { name: 'Save game' })).toBeEnabled()
  fireEvent.click(screen.getByTestId('new-drive'))
  await screen.findByTestId('start-game')
})
it('advances a computer-owned toss without exposing its decision controls', async () => {
  let finish
  api.coachStep.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
  await start('home', 'computer')
  expectOnlyOpening()
  expect(screen.queryByRole('button', { name: 'Kick', exact: true })).toBeNull()
  expect(screen.queryByRole('button', { name: 'Receive', exact: true })).toBeNull()
  await waitFor(() => expect(api.coachStep).toHaveBeenCalledWith('game', 'home'))
  await act(async () => { finish({ view: kickoff(), turn: turn('offense', { actions: kickoff().actions }) }) })
  await screen.findByTestId('playing-screen')
  expect(screen.getByTestId('special-play-kickoff')).toBeVisible()
  expect(api.decide).not.toHaveBeenCalled()
})
it('loads an unresolved opening toss back into the separate screen without deciding it', async () => {
  api.loadGame.mockResolvedValue({ game_id: 'loaded', seed: 7, view: opening() })
  api.getGame.mockResolvedValue({ game_id: 'loaded', seed: 7, view: opening(), turn: turn('decision') })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Load saved game'), { target: { files: [{ size: 20, text: async () => '{opaque}' }] } })
  await screen.findByTestId('opening-screen')
  expectOnlyOpening()
  expect(await screen.findByRole('button', { name: 'Receive', exact: true }, { timeout: 300 })).toBeEnabled()
  expect(api.decide).not.toHaveBeenCalled()
  expect(api.coachStep).not.toHaveBeenCalled()
})

it.each(['decision', 'computer'])('animates before revealing the recorded toss without another roll, role=%s', async (role) => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false })))
  api.coachStep.mockResolvedValue({ view: kickoff(), turn: turn('offense', { actions: kickoff().actions }) })
  await start('home', role)
  expect(screen.getByTestId('coin')).toHaveClass('toss-coin')
  expect(screen.getByTestId('coin')).toHaveTextContent('?')
  expect(screen.getByTestId('toss-flipping')).toHaveTextContent('Flipping coin')
  expect(screen.queryByRole('button', { name: 'Kick', exact: true })).toBeNull()
  expect(screen.queryByText('Alpha Tech won the engine toss.')).toBeNull()
  await act(async () => { await new Promise((resolve) => setTimeout(resolve, 250)) })
  expect(api.coachStep).not.toHaveBeenCalled()
  if (role === 'decision') {
    await screen.findByRole('button', { name: 'Kick', exact: true }, { timeout: 2000 })
    expect(screen.getByTestId('coin')).not.toHaveClass('toss-coin')
    expect(screen.getByText('Alpha Tech won the engine toss.')).toBeVisible()
    expect(screen.queryByTestId('toss-flipping')).toBeNull()
    expect(api.coachStep).not.toHaveBeenCalled()
  } else {
    await screen.findByTestId('playing-screen', {}, { timeout: 2000 })
    expect(api.coachStep).toHaveBeenCalledTimes(1)
  }
  expect(api.newGame).toHaveBeenCalledTimes(1)
  expect(api.decide).not.toHaveBeenCalled()
  expect(api.snap).not.toHaveBeenCalled()
})
