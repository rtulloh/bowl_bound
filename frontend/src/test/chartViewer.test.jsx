import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import ChartViewer from '../components/ChartViewer'
import * as api from '../api'

vi.mock('../api', () => ({ getCharts: vi.fn() }))
const table = (key) => ({ key, title: key === 'offense' ? 'Offense' : 'Defense', roll_label: 'Roll', columns: [{ key: '1', label: '1 · Line Plunge' }], rows: [{ label: '10', description: 'Offensive total 10', cells: [{ label: '0', color: 'white', description: 'No change' }] }, { label: '11', description: 'Offensive total 11', cells: [{ label: 'INT 20', color: 'red', description: 'Interception 20 yards downfield' }] }] })
const book = { team: 'Alpha Tech', season: 2026, note: 'Chart reference.', offense: table('offense'), defense: table('defense'), legend: [{ color: 'red', label: 'Red', description: 'Losses and special results; read the cell.' }], symbols: [{ label: 'INT', description: 'Interception at the printed distance.' }] }

beforeEach(() => {
  vi.resetAllMocks()
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }
  api.getCharts.mockResolvedValue(book)
})

it('opens the controlled team chart, renders supplied labels and restores focus without a play', async () => {
  render(<ChartViewer gameId="game" home="Alpha Tech" away="Beta State" initialSide="away" initialChart="defense" />)
  const trigger = screen.getByRole('button', { name: 'Charts' })
  expect(api.getCharts).not.toHaveBeenCalled()
  fireEvent.click(trigger)
  expect(await screen.findByRole('table', { name: /Defense/ })).toBeVisible()
  expect(api.getCharts).toHaveBeenCalledExactlyOnceWith('game', 'away')
  expect(screen.getByRole('cell', { name: /^0 —/ })).toHaveTextContent('0')
  expect(screen.getByRole('cell', { name: /INT 20/ })).toHaveClass('chart-cell-red')
  expect(screen.getByText('Interception at the printed distance.')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Offense', exact: true }))
  expect(screen.getByRole('table', { name: /Offense/ })).toBeVisible()
  expect(api.getCharts).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Close charts' }))
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(trigger).toHaveFocus()
})

it('changes teams, handles failures and retries without rendering a stale chart', async () => {
  api.getCharts.mockRejectedValueOnce(new Error('Server unavailable')).mockResolvedValue(book)
  render(<ChartViewer gameId="game" home="Alpha Tech" away="Beta State" initialSide="home" />)
  fireEvent.click(screen.getByRole('button', { name: 'Charts' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Server unavailable')
  fireEvent.click(screen.getByRole('button', { name: 'Retry charts' }))
  await screen.findByRole('table')
  api.getCharts.mockResolvedValue({ ...book, team: 'Beta State' })
  fireEvent.change(screen.getByLabelText('Chart team'), { target: { value: 'away' } })
  await waitFor(() => expect(api.getCharts).toHaveBeenLastCalledWith('game', 'away'))
  expect(await screen.findByRole('heading', { name: '2026 Beta State' })).toBeVisible()
  fireEvent(screen.getByRole('dialog'), new Event('cancel', { bubbles: true, cancelable: true }))
  expect(screen.queryByRole('dialog')).toBeNull()
})
