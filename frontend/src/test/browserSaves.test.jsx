import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import * as api from '../api'
import * as library from '../runtime/gameLibrary'
import { view } from './fixtures'
import { waitForStartReady } from './startGame'

vi.mock('../api', () => ({
  listTeams: vi.fn(), getRules: vi.fn(), newGame: vi.fn(), decide: vi.fn(), coachStep: vi.fn(),
  kick: vi.fn(), snap: vi.fn(), gameAction: vi.fn(), getCharts: vi.fn(), saveGame: vi.fn(), loadGame: vi.fn(),
}))
vi.mock('../runtime/gameLibrary', () => ({
  listSavedGames: vi.fn(), writeSavedGame: vi.fn(), deleteSavedGame: vi.fn(),
}))

const checkpoint = '{"rng":900719925474099313}'
const game = { game_id: 'live', seed: 42, revision: 1, view: view({ phase: 'opening_choice' }) }
const saved = { id: 'snapshot', name: 'Friday game', humanSide: 'away', checkpoint, version: 'old' }

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubEnv('MODE', 'browser')
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })))
  api.listTeams.mockResolvedValue({ teams: [{ id: 'a', name: 'Alpha', season: 2007 }, { id: 'b', name: 'Beta', season: 2007 }] })
  api.getRules.mockResolvedValue({ season: 2007, game_type: 'regular', supported: true, details: [] })
  api.newGame.mockResolvedValue(game)
  api.saveGame.mockResolvedValue(checkpoint)
  library.listSavedGames.mockResolvedValue([])
  library.writeSavedGame.mockImplementation(async (record) => ({ ...record, version: 'written' }))
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

it('writes the exact engine checkpoint and acknowledges the durable browser save', async () => {
  render(<App />)
  await waitForStartReady()
  fireEvent.click(screen.getByTestId('start-game'))
  await waitFor(() => expect(library.writeSavedGame).toHaveBeenCalledWith(expect.objectContaining({ checkpoint, humanSide: 'home' }), undefined))
  expect(await screen.findByText('Game saved locally.')).toBeInTheDocument()
})

it('resumes a named game using its recorded control mode and leaves its checkpoint untouched', async () => {
  library.listSavedGames.mockResolvedValue([saved])
  api.loadGame.mockResolvedValue(game)
  render(<App />)
  fireEvent.click(screen.getByText('Saved games', { selector: 'summary' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Resume Friday game' }))
  await screen.findByTestId('opening-screen')
  expect(api.loadGame).toHaveBeenCalledWith(checkpoint, 'away')
  expect(library.writeSavedGame).not.toHaveBeenCalled()
  expect(api.decide).not.toHaveBeenCalled()
})

it('keeps the live game available for export when browser storage fails', async () => {
  library.writeSavedGame.mockRejectedValue(new Error('Storage quota exceeded'))
  render(<App />)
  await waitForStartReady()
  fireEvent.click(screen.getByTestId('start-game'))
  await screen.findByTestId('opening-screen')
  expect(await screen.findByRole('alert')).toHaveTextContent('Storage quota exceeded')
  fireEvent.click(screen.getByText('Game', { selector: 'summary' }))
  expect(screen.getByRole('button', { name: 'Export game' })).toBeEnabled()
})
