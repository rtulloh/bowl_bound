import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import * as api from '../api'
import { report, view } from './fixtures'

vi.mock('../api', () => ({
  listTeams: vi.fn(), newGame: vi.fn(), decide: vi.fn(), snap: vi.fn(), kick: vi.fn(), gameAction: vi.fn(),
}))

beforeEach(() => {
  vi.resetAllMocks()
  api.listTeams.mockResolvedValue({ teams: [{ id: 'a', name: 'Alpha', season: 2002 }, { id: 'b', name: 'Beta', season: 2002 }] })
})

it('allows the next snap with None selected and no separate clock request', async () => {
  api.newGame.mockResolvedValue({ game_id: 'synthetic', seed: 1, view: view({
    phase: 'clock_choice', clock_optional: true, log: [report()],
    pending: { choices: [{ id: 'clock:runoff', label: 'Run 30 seconds', enabled: true }] },
    clock_modifiers: [{ id: 'clock:runoff', label: 'None', enabled: true }],
  }) })
  api.snap.mockResolvedValue({ report: report(), view: view({ pending: null }) })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  expect(await screen.findByTestId('clock-controls')).toBeInTheDocument()
  expect(screen.getByRole('radio', { name: 'None' })).toBeChecked()
  expect(screen.queryByTestId('clock-continue')).toBeNull()
  expect(screen.queryByTestId('penalty-choices')).toBeNull()
  fireEvent.click(screen.getByTestId('offense-play-1'))
  fireEvent.click(screen.getByTestId('defense-play-a'))
  expect(screen.queryByTestId('snap')).toBeNull()
  await waitFor(() => expect(api.snap).toHaveBeenCalledWith('synthetic', '1', 'A'))
  expect(api.decide).not.toHaveBeenCalled()
})

it('keeps genuine football decisions blocking', async () => {
  api.newGame.mockResolvedValue({ game_id: 'synthetic', seed: 1, view: view({
    phase: 'scrimmage', pending: { choices: [{ id: 'accept:0:previous', label: 'Accept foul', enabled: true }] },
  }) })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  expect(await screen.findByTestId('penalty-choices')).toBeInTheDocument()
  expect(screen.queryByTestId('clock-controls')).toBeNull()
  expect(screen.getByTestId('offense-play-1')).toBeDisabled()
})


it('sends the selected game type without choosing an overtime era in the UI', async () => {
  api.newGame.mockResolvedValue({ game_id: 'synthetic', seed: 1, view: view() })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.change(screen.getByLabelText('Game type'), { target: { value: 'postseason' } })
  fireEvent.click(screen.getByTestId('start-game'))
  await waitFor(() => expect(api.newGame).toHaveBeenCalledWith({ home: 'a', away: 'b', mode: 'regulation', game_type: 'postseason', difficulty: 'medium' }))
})
