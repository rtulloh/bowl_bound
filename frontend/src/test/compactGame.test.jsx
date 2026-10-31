import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import * as api from '../api'
import { view, report } from './fixtures'

vi.mock('../api', () => ({ listTeams: vi.fn(), newGame: vi.fn(), snap: vi.fn(), decide: vi.fn(), kick: vi.fn(), gameAction: vi.fn(), coachStep: vi.fn(), getGame: vi.fn(), loadGame: vi.fn(), saveGame: vi.fn() }))
beforeEach(() => {
  vi.resetAllMocks()
  api.listTeams.mockResolvedValue({ teams: [{ id: 'a', name: 'Alpha', season: 2007 }, { id: 'b', name: 'Beta', season: 2007 }] })
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 7, view: view() })
  api.snap.mockResolvedValue({ view: view(), report: report() })
})
async function start() {
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  fireEvent.click(screen.getByTestId('start-game'))
  await screen.findByTestId('offense-play-1')
}
it.each(['offense', 'defense'])('submits when the second manual call is selected, %s first, and requires fresh calls', async (first) => {
  await start()
  const offense = screen.getByTestId('offense-play-1')
  const defense = screen.getByTestId('defense-play-a')
  fireEvent.click(first === 'offense' ? offense : defense)
  expect(api.snap).not.toHaveBeenCalled()
  fireEvent.click(first === 'offense' ? defense : offense)
  await waitFor(() => expect(api.snap).toHaveBeenCalledWith('game', '1', 'A'))
  await waitFor(() => expect(offense).toBeEnabled())
  expect(offense).toHaveAttribute('aria-pressed', 'false')
  expect(defense).toHaveAttribute('aria-pressed', 'false')
  expect(screen.queryByTestId('snap')).toBeNull()
  fireEvent.click(offense)
  expect(api.snap).toHaveBeenCalledTimes(1)
  fireEvent.click(defense)
  await waitFor(() => expect(api.snap).toHaveBeenCalledTimes(2))
})
it('serializes selection-triggered requests and blocks repeated input while resolving', async () => {
  let finish
  api.snap.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
  await start()
  fireEvent.click(screen.getByTestId('offense-play-1'))
  fireEvent.click(screen.getByTestId('defense-play-a'))
  expect(screen.getByTestId('offense-play-1')).toBeDisabled()
  fireEvent.click(screen.getByTestId('defense-play-a'))
  expect(api.snap).toHaveBeenCalledTimes(1)
  finish({ view: view(), report: report() })
  await waitFor(() => expect(screen.getByTestId('offense-play-1')).toBeEnabled())
})
it('allows a failed snap to be retried by choosing fresh calls without reusing a stale opponent', async () => {
  api.snap.mockRejectedValueOnce(new Error('Request failed'))
  await start()
  fireEvent.click(screen.getByTestId('offense-play-1'))
  fireEvent.click(screen.getByTestId('defense-play-a'))
  expect(await screen.findByRole('alert')).toHaveTextContent('Request failed')
  fireEvent.click(screen.getByTestId('defense-play-b'))
  expect(api.snap).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByTestId('offense-play-2'))
  await waitFor(() => expect(api.snap).toHaveBeenLastCalledWith('game', '2', 'B'))
})
it('keeps game management in a collapsed header menu, supports keyboard dismissal and new-game setup', async () => {
  await start()
  const menu = screen.getByText('Game', { selector: 'summary' })
  expect(menu.closest('header')).not.toBeNull()
  expect(screen.getByTestId('new-drive')).not.toBeVisible()
  expect(screen.getByText('Save game')).not.toBeVisible()
  expect(screen.getByLabelText('Load saved game')).not.toBeVisible()
  expect(screen.queryByLabelText('Control mode')).toBeNull()
  fireEvent.click(menu)
  expect(screen.getByRole('button', { name: 'Save game' })).toBeVisible()
  expect(screen.getByLabelText('Load saved game')).toBeVisible()
  fireEvent.keyDown(menu, { key: 'Escape' })
  expect(menu.parentElement).not.toHaveAttribute('open')
  expect(menu).toHaveFocus()
  fireEvent.click(menu)
  fireEvent.click(screen.getByTestId('new-drive'))
  expect(await screen.findByTestId('start-game')).toBeInTheDocument()
  expect(screen.getByLabelText('Control mode')).toBeInTheDocument()
})

it('places offered punt, field-goal and kneel controls in the offensive play panel without adding Sneak', async () => {
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 7, view: view({
    actions: { ...view().actions, special: [{ key: 'punt', label: 'Punt' }, { key: 'field_goal', label: 'Field goal' }] },
    game_actions: [{ key: 'kneel', label: 'Kneel' }],
  }) })
  api.kick.mockResolvedValue({ view: view(), report: report() })
  await start()
  const offense = screen.getByTestId('offense-plays')
  expect(offense).toContainElement(screen.getByTestId('special-play-punt'))
  expect(offense).toContainElement(screen.getByTestId('special-play-field_goal'))
  expect(offense).toContainElement(screen.getByTestId('game-play-kneel'))
  expect(screen.getByTestId('special-play-punt')).toHaveTextContent('PPunt')
  expect(screen.getByTestId('special-play-field_goal')).toHaveTextContent('FFG')
  expect(screen.getByTestId('special-play-field_goal')).toHaveAccessibleName('F: Field goal')
  expect(screen.getByTestId('special-play-field_goal')).toHaveAttribute('title', 'Field goal')
  expect(screen.getByTestId('game-play-kneel')).toHaveTextContent('KKneel')
  expect(screen.queryByTestId('special-plays')).toBeNull()
  expect(screen.queryByTestId('game-plays')).toBeNull()
  expect(screen.queryByRole('button', { name: /Sneak/ })).toBeNull()
  fireEvent.click(screen.getByTestId('special-play-punt'))
  await waitFor(() => expect(api.kick).toHaveBeenCalledWith('game', 'punt'))
  expect(api.snap).not.toHaveBeenCalled()
})

it('executes the offered kneel directly from the play panel, without another selection', async () => {
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 7, view: view({ game_actions: [{ key: 'kneel', label: 'Kneel' }] }) })
  api.gameAction.mockResolvedValue({ view: view(), report: report() })
  await start()
  fireEvent.click(screen.getByTestId('game-play-kneel'))
  await waitFor(() => expect(api.gameAction).toHaveBeenCalledWith('game', 'kneel'))
  expect(api.snap).not.toHaveBeenCalled()
})

it('defaults to human home/computer away while keeping two-sided manual play last', async () => {
  render(<App />)
  await screen.findByTestId('start-game')
  const modes = screen.getByLabelText('Control mode')
  expect(Array.from(modes.options, (option) => option.value)).toEqual(['home', 'away', 'manual'])
  expect(modes).toHaveValue('home')
})

it('keeps hurry-up, timeouts, spike and unavailable OOB together in the visible modifier row', async () => {
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 7, view: view({ phase: 'clock_choice', clock_optional: true,
    pending: { choices: [
      { id: 'clock:timeout:home', label: 'Home timeout', enabled: true },
      { id: 'clock:spike', label: 'Spike', enabled: true },
    ] },
    clock_modifiers: [
      { id: 'clock:timeout:home', label: 'Home timeout', enabled: true },
      { id: 'clock:spike', label: 'Spike', enabled: true },
    ],
  }) })
  api.decide.mockResolvedValue({ view: view() })
  await start()
  const row = screen.getByRole('region', { name: 'Play modifiers' })
  expect(row).toContainElement(screen.getByRole('checkbox', { name: 'Hurry-up mode' }))
  expect(row).toContainElement(screen.getByRole('radio', { name: 'Home timeout' }))
  expect(row).toContainElement(screen.getByRole('radio', { name: 'Spike' }))
  expect(row).toContainElement(screen.getByRole('button', { name: 'OOB' }))
  expect(screen.getByRole('button', { name: 'OOB' })).toBeDisabled()
  fireEvent.click(screen.getByRole('radio', { name: 'Home timeout' }))
  await waitFor(() => expect(api.decide).toHaveBeenCalledWith('game', 'clock:timeout:home'))
  expect(screen.getByRole('button', { name: 'Timeout' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Spike' })).toBeDisabled()
})

it('shows unavailable Timeout, Spike and OOB beside Hurry-up instead of hiding them', async () => {
  await start()
  const row = screen.getByRole('region', { name: 'Play modifiers' })
  for (const name of ['Timeout', 'Spike', 'OOB', 'IB']) {
    const button = screen.getByRole('button', { name, exact: true })
    expect(row).toContainElement(button)
    expect(button).toBeDisabled()
    fireEvent.click(button)
  }
  expect(api.decide).not.toHaveBeenCalled()
  expect(api.gameAction).not.toHaveBeenCalled()
})

it('keeps engine-offered between-play timeouts in the same modifier row, not in play panels', async () => {
  api.newGame.mockResolvedValue({ game_id: 'game', seed: 7, view: view({
    game_actions: [{ key: 'timeout:home', label: 'Alpha timeout (3)' }],
  }) })
  api.gameAction.mockResolvedValue({ view: view() })
  await start()
  const timeout = screen.getByTestId('game-play-timeout:home')
  expect(screen.getByRole('region', { name: 'Play modifiers' })).toContainElement(timeout)
  expect(screen.getByTestId('offense-plays')).not.toContainElement(timeout)
  expect(screen.queryByRole('button', { name: 'Timeout', exact: true })).toBeNull()
  fireEvent.click(timeout)
  await waitFor(() => expect(api.gameAction).toHaveBeenCalledWith('game', 'timeout:home'))
  expect(screen.getByRole('button', { name: 'Timeout', exact: true })).toBeDisabled()
})
