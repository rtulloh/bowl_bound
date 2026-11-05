import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import ChartViewer, { DetachedCharts } from '../components/ChartViewer'
import * as api from '../api'

vi.mock('../api', () => ({ getCharts: vi.fn() }))
const table = (key) => ({ key, title: key === 'offense' ? 'Offense' : 'Defense', roll_label: 'Roll', columns: [{ key: '1', label: '1 · Line Plunge' }], rows: [{ label: '10', description: 'Offensive total 10', cells: [{ label: '0', color: 'white', description: 'No change' }] }, { label: '11', description: 'Offensive total 11', cells: [{ label: 'INT 20', color: 'red', description: 'Interception 20 yards downfield' }] }] })
const priority = { note: 'Read the offensive row against the defensive column.', table: { ...table('priority'), title: 'Priority chart', rows: [{ label: '# / B', description: 'Ordinary gain or Breakaway', cells: [{ label: 'ADD', color: 'green', description: 'Add signed yardage' }] }] }, legend: [{ label: 'ADD', description: 'Add signed yardage.' }], notes: ['The approved (B) extension is shown.'] }
const book = { priority, team: 'Alpha Tech', season: 2026, note: 'Chart reference.', offense: table('offense'), defense: table('defense'), legend: [{ color: 'red', label: 'Red', description: 'Losses and special results; read the cell.' }], symbols: [{ label: 'INT', description: 'Interception at the printed distance.' }] }

beforeEach(() => {
  vi.restoreAllMocks()
  vi.resetAllMocks()
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }
  api.getCharts.mockImplementation(async (_game, side) => ({ ...book, team: side === 'home' ? 'Alpha Tech' : 'Beta State' }))
})

it('opens the controlled team chart, renders supplied labels and restores focus without a play', async () => {
  render(<ChartViewer gameId="game" initialSide="away" initialChart="defense" />)
  const trigger = screen.getByRole('button', { name: 'Charts' })
  expect(api.getCharts).not.toHaveBeenCalled()
  fireEvent.click(trigger)
  expect(await screen.findByRole('table', { name: /Defense/ })).toBeVisible()
  expect(api.getCharts).toHaveBeenCalledTimes(2)
  expect(api.getCharts).toHaveBeenCalledWith('game', 'home')
  expect(api.getCharts).toHaveBeenCalledWith('game', 'away')
  expect(screen.getByRole('cell', { name: /^0 —/ })).toHaveTextContent('0')
  expect(screen.getByRole('cell', { name: /INT 20/ })).toHaveClass('chart-cell-red')
  const help = screen.getByText('How to read the charts').closest('details')
  expect(help.open).toBe(false)
  fireEvent.click(screen.getByText('How to read the charts'))
  expect(help.open).toBe(true)
  expect(screen.getByText('Interception at the printed distance.')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Offense', exact: true }))
  expect(screen.getByRole('table', { name: /Offense/ })).toBeVisible()
  expect(api.getCharts).toHaveBeenCalledTimes(2)
  fireEvent.click(screen.getByRole('button', { name: 'Close charts' }))
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(trigger).toHaveFocus()
})

it('changes teams, handles failures and retries without rendering a stale chart', async () => {
  api.getCharts.mockRejectedValueOnce(new Error('Server unavailable'))
  render(<ChartViewer gameId="game" initialSide="home" />)
  fireEvent.click(screen.getByRole('button', { name: 'Charts' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Charts could not be loaded')
  fireEvent.click(screen.getByRole('button', { name: 'Retry charts' }))
  await screen.findByRole('table')
  expect(api.getCharts).toHaveBeenCalledTimes(4)
  fireEvent.change(screen.getByLabelText('Chart team'), { target: { value: 'away' } })
  expect(api.getCharts).toHaveBeenCalledTimes(4)
  expect(await screen.findByRole('heading', { name: '2026 Beta State' })).toBeVisible()
  fireEvent(screen.getByRole('dialog'), new Event('cancel', { bubbles: true, cancelable: true }))
  expect(screen.queryByRole('dialog')).toBeNull()
})

it('shows the shared Priority reference and preserves the team without gameplay requests', async () => {
  render(<ChartViewer gameId="game" initialSide="away" />)
  fireEvent.click(screen.getByRole('button', { name: 'Charts' }))
  await screen.findByRole('table')
  fireEvent.click(screen.getByRole('button', { name: 'Priority', exact: true }))
  expect(screen.getByRole('table', { name: 'Priority chart' })).toBeVisible()
  expect(screen.getByRole('cell', { name: /ADD/ })).toHaveClass('chart-cell-green')
  expect(screen.queryByLabelText('Chart team')).toBeNull()
  const help = screen.getByText('How to read Priority').closest('details')
  expect(help.open).toBe(false)
  fireEvent.click(screen.getByText('How to read Priority'))
  expect(help.open).toBe(true)
  expect(screen.getByText('The approved (B) extension is shown.')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Defense', exact: true }))
  expect(screen.getByLabelText('Chart team')).toHaveValue('away')
  expect(screen.getByText('How to read the charts').closest('details').open).toBe(false)
  expect(api.getCharts).toHaveBeenCalledTimes(2)
  expect(api.getCharts).toHaveBeenCalledWith('game', 'home')
  expect(api.getCharts).toHaveBeenCalledWith('game', 'away')
})

it('offers a safe new-tab link and keeps a usable fallback when a popup is blocked', async () => {
  vi.spyOn(window, 'open').mockReturnValueOnce(null)
  render(<ChartViewer gameId="game" initialSide="away" initialChart="defense" />)
  fireEvent.click(screen.getByRole('button', { name: 'Charts' }))
  await screen.findByRole('table')
  const link = screen.getByRole('link', { name: 'Open in new tab' })
  expect(link).toHaveAttribute('target', '_blank')
  expect(link.getAttribute('rel')).toContain('noopener')
  expect(link.href).toContain('charts=game&side=away&view=defense')
  fireEvent.click(screen.getByRole('button', { name: 'Open in separate window' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Use Open in new tab')
  expect(screen.getByRole('dialog')).toBeVisible()
  expect(link).toBeVisible()
})

it('isolates a popup opener before navigation and returns the parent to play', async () => {
  const replace = vi.fn()
  const child = { opener: window, location: { replace }, close: vi.fn() }
  vi.spyOn(window, 'open').mockReturnValueOnce(child)
  render(<ChartViewer gameId="game" />)
  fireEvent.click(screen.getByRole('button', { name: 'Charts' }))
  await screen.findByRole('table')
  fireEvent.click(screen.getByRole('button', { name: 'Open in separate window' }))
  expect(child.opener).toBeNull()
  expect(replace).toHaveBeenCalledWith(expect.stringContaining('?charts=game'))
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(screen.getByRole('button', { name: 'Charts' })).toHaveFocus()
})

it('shows an accessible expired-game error in the detached shell without game controls', async () => {
  api.getCharts.mockRejectedValue(new Error('no such game'))
  render(<DetachedCharts gameId="missing-game" initialSide="home" initialChart="priority" />)
  expect(await screen.findByRole('alert')).toHaveTextContent('game is no longer available')
  expect(screen.queryByRole('button', { name: 'Charts' })).toBeNull()
  expect(screen.getByRole('button', { name: 'Retry charts' })).toBeVisible()
})
