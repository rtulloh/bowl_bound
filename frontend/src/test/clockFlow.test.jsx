import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import * as api from '../api'
import { report, view } from './fixtures'

vi.mock('../api', () => ({
  listTeams: vi.fn(), newGame: vi.fn(), decide: vi.fn(), snap: vi.fn(), kick: vi.fn(), gameAction: vi.fn(), coachStep: vi.fn(),
}))

beforeEach(() => {
  vi.resetAllMocks()
  api.listTeams.mockResolvedValue({ teams: [{ id: 'a', name: 'Alpha', season: 2002 }, { id: 'b', name: 'Beta', season: 2002 }] })
})

it('keeps timeout selection serialized with defense and displays prior and selected-play timing from the engine', async () => {
  const priorTiming = 'Previous play timing is pending: normal timing is 30 seconds. Clock options adjust that play; selecting a play applies its normal timing first.'
  const choices = [{ id: 'clock:timeout:away', label: 'Away timeout (3)', enabled: true }]
  const human = { human_side: 'away', human_role: 'defense', automatic: false, status: 'Choose defense',
    actions: { offense: [], defense: view().actions.defense, special: [] },
    game_actions: [{ key: 'timeout:away', label: 'Legacy reservation (3)' }, { key: 'timeout_after:away', label: 'Use Away timeout on next play (3)' }],
    pending: { choices },
  }
  const before = view({ phase: 'clock_choice', clock_optional: true, clock_modifiers: choices,
    clock_timing_label: priorTiming, log: [report()] })
  api.newGame.mockResolvedValue({ game_id: 'timeout-game', revision: 4, view: before, turn: human })
  let selectTimeout
  api.gameAction.mockImplementation(() => new Promise((resolve) => { selectTimeout = resolve }))
  const timing = 'Away timeout used; this play took 10 seconds.'
  api.coachStep.mockResolvedValue({ revision: 6, report: report({ number: 2, timing_label: timing }),
    view: view({ log: [report(), report({ number: 2, timing_label: timing })] }),
    turn: { ...human, pending: null },
  })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'away' } })
  fireEvent.click(screen.getByTestId('start-game'))
  expect(await screen.findByText(priorTiming)).toBeVisible()
  expect(screen.queryByText('Choose one action for the next play.')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Legacy reservation (3)' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Use Away timeout on next play (3)' }))
  fireEvent.click(screen.getByTestId('defense-play-a'))
  expect(api.coachStep).not.toHaveBeenCalled()
  expect(api.gameAction).toHaveBeenCalledWith('timeout-game', 'timeout_after:away', 'away')
  const selected = 'Away timeout requested for the next play if eligible.'
  selectTimeout({ revision: 5, report: null, view: { ...before, armed_timeout: 'away', conditional_timeout: true, armed_timeout_label: selected },
    turn: { ...human, game_actions: [{ key: 'timeout_after:away', label: 'Cancel Away timeout (3)' }] },
  })
  expect(await screen.findByText(selected)).toBeVisible()
  fireEvent.click(screen.getByTestId('defense-play-a'))
  await waitFor(() => expect(api.coachStep).toHaveBeenCalledWith('timeout-game', 'away', 5, 'A'))
  expect(await screen.findAllByText(timing)).toHaveLength(2)
  expect(screen.queryByText(selected)).toBeNull()
  expect(api.decide).not.toHaveBeenCalled()
})

it('allows the next snap without a separate clock request', async () => {
  api.newGame.mockResolvedValue({ game_id: 'synthetic', seed: 1, view: view({
    phase: 'clock_choice', clock_optional: true, log: [report()],
    pending: { choices: [{ id: 'clock:timeout:home', label: 'Home timeout', enabled: true }] },
    clock_modifiers: [{ id: 'clock:timeout:home', label: 'Home timeout', enabled: true }],
  }) })
  api.snap.mockResolvedValue({ report: report(), view: view({ pending: null }) })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  expect(await screen.findByTestId('clock-controls')).toBeInTheDocument()
  expect(screen.getByRole('radio', { name: 'Home timeout' })).not.toBeChecked()
  expect(screen.queryByRole('radio', { name: /runoff|none/i })).toBeNull()
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


it('shows engine-offered next-play timeout actions beside existing post-play choices', async () => {
  const before = view({ phase: 'clock_choice', clock_optional: true,
    pending: { choices: [{ id: 'clock:timeout:home', label: 'Prior play timeout', enabled: true }] },
    clock_modifiers: [{ id: 'clock:timeout:home', label: 'Prior play timeout', enabled: true }],
    game_actions: [{ key: 'timeout:home', label: 'Use Home timeout on next play (3)' }],
  })
  api.newGame.mockResolvedValue({ game_id: 'synthetic', seed: 1, view: before })
  api.gameAction.mockResolvedValue({ report: null, view: { ...before, armed_timeout: 'home', armed_timeout_label: 'Home timeout selected for the next play; that play takes 10 seconds.', game_actions: [{ key: 'timeout:home', label: 'Cancel Home timeout (3)' }] } })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  expect(await screen.findByRole('radio', { name: 'Prior play timeout' })).not.toBeChecked()
  fireEvent.click(screen.getByRole('button', { name: 'Use Home timeout on next play (3)' }))
  await waitFor(() => expect(api.gameAction).toHaveBeenCalledWith('synthetic', 'timeout:home'))
  expect(await screen.findByText('Home timeout selected for the next play; that play takes 10 seconds.')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Cancel Home timeout (3)' })).toBeEnabled()
  expect(api.snap).not.toHaveBeenCalled()
  expect(api.decide).not.toHaveBeenCalled()
})
