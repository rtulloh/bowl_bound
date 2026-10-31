import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import PenaltyChoices from '../components/PenaltyChoices'
import PlaySelector from '../components/PlaySelector'
import { report, stateView, view } from './fixtures'
import * as api from '../api'

vi.mock('../api', () => ({ listTeams: vi.fn(), newGame: vi.fn(), snap: vi.fn(), decide: vi.fn(), kick: vi.fn(), gameAction: vi.fn() }))
beforeEach(() => {
  vi.resetAllMocks()
  api.listTeams.mockResolvedValue({ teams: [{ id: 'a', name: 'Alpha', season: 2007 }, { id: 'b', name: 'Beta', season: 2007 }] })
})

it('names the chooser and focuses the first enabled decision, not a disabled choice', () => {
  render(<PenaltyChoices pending={{ chooser: 'Beta State', choices: [
    { id: 'no', label: 'Unavailable', enabled: false }, { id: 'yes', label: 'Return', enabled: true },
  ] }} onChoose={() => {}} />)
  expect(screen.getByTestId('penalty-choices')).toHaveTextContent('Beta State')
  expect(screen.getByRole('button', { name: 'Return' })).toHaveFocus()
})

it('exposes selected play state to assistive technology', () => {
  render(<PlaySelector title="OFFENSE" prefix="offense" actions={view().actions.offense} selected="1" onSelect={() => {}} />)
  expect(screen.getByTestId('offense-play-1')).toHaveAttribute('aria-pressed', 'true')
})

it('clears both selections after possession changes and names the selecting teams', async () => {
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 1, view: view() })
  api.snap.mockResolvedValue({ report: report(), view: view({
    state: stateView({ possession: 'away', possession_name: 'Beta State' }),
  }) })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  fireEvent.click(await screen.findByTestId('offense-play-1'))
  fireEvent.click(screen.getByTestId('defense-play-a'))
  await waitFor(() => expect(screen.getByTestId('offense-plays')).toHaveTextContent('Beta State'))
  expect(screen.queryByTestId('snap')).toBeNull()
  expect(api.snap).toHaveBeenCalledTimes(1)
  expect(screen.getByTestId('offense-play-1')).toHaveAttribute('aria-pressed', 'false')
  expect(screen.getByTestId('defense-play-a')).toHaveAttribute('aria-pressed', 'false')
})

it('keeps hurry mode enabled, using only offered legal hurry choices', async () => {
  const clock = view({ phase: 'clock_choice', clock_optional: true, pending: { choices: [
    { id: 'clock:hurry', label: 'Hurry', enabled: true },
  ] }, clock_modifiers: [{ id: 'clock:hurry', label: 'Hurry-up', enabled: true }] })
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 1, view: clock })
  api.decide.mockResolvedValue({ report: null, view: view() })
  api.snap.mockResolvedValue({ report: report(), view: view() })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  fireEvent.click(await screen.findByRole('checkbox', { name: 'Hurry-up mode' }))
  fireEvent.click(screen.getByTestId('offense-play-1'))
  fireEvent.click(screen.getByTestId('defense-play-a'))
  await waitFor(() => expect(api.snap).toHaveBeenCalledTimes(1))
  expect(api.decide).toHaveBeenCalledWith('game', 'clock:hurry')
  expect(screen.getByRole('checkbox', { name: 'Hurry-up mode' })).toBeChecked()
  fireEvent.click(screen.getByTestId('offense-play-1'))
  fireEvent.click(screen.getByTestId('defense-play-a'))
  await waitFor(() => expect(api.snap).toHaveBeenCalledTimes(2))
  expect(api.decide).toHaveBeenCalledTimes(1)
})

it('uses the engine toss winner in the coin presentation without generating a winner', async () => {
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 1, view: view({ phase: 'opening_choice',
    pending: { chooser: 'Beta State', choices: [{ id: 'toss:receive', label: 'Receive', enabled: true }] } }) })
  api.decide.mockResolvedValue({ report: null, view: view() })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  const receive = await screen.findByRole('button', { name: 'Receive' }, { timeout: 2000 })
  expect(screen.getByTestId('coin-toss')).toHaveTextContent('Beta State')
  fireEvent.click(receive)
  await waitFor(() => expect(api.decide).toHaveBeenCalledWith('game', 'toss:receive'))
})


it('retains hurry mode through pending decisions and possession changes, but starts a new game clean', async () => {
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 1, view: view() })
  api.snap.mockResolvedValue({ report: report({ pending: true }), view: view({ pending: {
    chooser: 'Beta State', choices: [{ id: 'interception:return', label: 'Return', enabled: true }],
  } }) })
  api.decide.mockResolvedValue({ report: report(), view: view({ state: stateView({ possession: 'away', possession_name: 'Beta State' }) }) })
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  fireEvent.click(await screen.findByRole('checkbox', { name: 'Hurry-up mode' }))
  fireEvent.click(screen.getByTestId('offense-play-1'))
  fireEvent.click(screen.getByTestId('defense-play-a'))
  const choice = await screen.findByRole('button', { name: 'Return' })
  expect(screen.getByRole('checkbox', { name: 'Hurry-up mode' })).toBeChecked()
  expect(api.decide).not.toHaveBeenCalled()
  fireEvent.click(choice)
  await waitFor(() => expect(screen.getByTestId('offense-plays')).toHaveTextContent('Beta State'))
  expect(screen.getByRole('checkbox', { name: 'Hurry-up mode' })).toBeChecked()
  fireEvent.click(screen.getByText('Game', { selector: 'summary' }))
  fireEvent.click(screen.getByTestId('new-drive'))
  fireEvent.click(await screen.findByTestId('start-game'))
  expect(await screen.findByRole('checkbox', { name: 'Hurry-up mode' })).not.toBeChecked()
  expect(screen.queryByTestId('snap')).toBeNull()
  expect(screen.getByTestId('offense-play-1')).toHaveAttribute('aria-pressed', 'false')
  expect(screen.getByTestId('defense-play-a')).toHaveAttribute('aria-pressed', 'false')
  expect(screen.queryByTestId('result-description')).toBeNull()
})


it('defaults to public fictional teams when they share a catalog with historical teams', async () => {
  api.listTeams.mockResolvedValue({ teams: [
    { id: '2002/private-a', name: 'Local historical A', season: 2002 },
    { id: '2002/private-b', name: 'Local historical B', season: 2002 },
    { id: '2007/cedar-valley', name: 'Cedar Valley', season: 2007 },
    { id: '2007/harbor-tech', name: 'Harbor Tech', season: 2007 },
  ] })
  render(<App />)
  await screen.findByTestId('start-game')
  expect(screen.getByTestId('home-select')).toHaveValue('2007/cedar-valley')
  expect(screen.getByTestId('away-select')).toHaveValue('2007/harbor-tech')
})
