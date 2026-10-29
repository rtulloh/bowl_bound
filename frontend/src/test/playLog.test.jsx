import { fireEvent, render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import PlayLog from '../components/PlayLog'
import { report, stateView } from './fixtures'

it('shows each play’s recorded line of scrimmage, situation and yardage with expandable actual dice', () => {
  render(<PlayLog entries={[report({
    number: 3, description: 'Alpha Tech: Option vs Formation D - safety for Beta State.',
    state_before: stateView({ spot: 'own 4', situation: '2nd and 8' }),
    state_after: null, yards: -6,
    trace: [{ section: 'defense', team: 'Beta State', play: 'Option', formation: 'Formation D',
      roll: { faces: [2, 1], total: 3 }, cell: '-6' }],
  })]} />)
  const entry = screen.getByTestId('log-entry')
  expect(within(entry).getByText('Before: Alpha Tech — 2nd and 8 at own 4')).toBeVisible()
  expect(within(entry).getByText('Recorded yardage: -6')).toBeVisible()
  const details = entry.querySelector('details')
  expect(details.open).toBe(false)
  fireEvent.click(within(entry).getByText('Dice and chart audit'))
  expect(details.open).toBe(true)
  expect(entry).toHaveTextContent('defense: Beta State Option / Formation D — dice 2+1 = 3, cell -6')
  expect(entry).not.toHaveTextContent('After:')
})

it('keeps before/after possession and positions verbatim, including zero yardage and no invented dice', () => {
  render(<PlayLog entries={[report({ yards: 0, trace: [],
    state_after: stateView({ possession_name: 'Beta State', situation: '1st and 10', spot: 'opponent 8' }),
  })]} />)
  expect(screen.getByText('Before: Alpha Tech — 1st and 10 at own 35')).toBeVisible()
  expect(screen.getByText('After: Beta State — 1st and 10 at opponent 8')).toBeVisible()
  expect(screen.getByText('Recorded yardage: 0')).toBeVisible()
  expect(screen.queryByText('Dice and chart audit')).toBeNull()
})


it('shows compact recorded dice without opening the audit or treating black faces as additions', () => {
  render(<PlayLog entries={[report()]} />)
  const dice = screen.getByLabelText('Recorded dice')
  expect(dice).toBeVisible()
  expect(dice).toHaveTextContent('offense: [1, 2, 3] → 15')
  expect(dice).toHaveTextContent('defense: [2, 1] → 3')
  expect(screen.getByTestId('log-entry').querySelector('details').open).toBe(false)
})

it('keeps supplemental and repeated rolls in recorded order', () => {
  const trace = [
    ...report().trace,
    { section: 'option', roll: { faces: [3, 4, 5], total: 39 }, cell: '8' },
    { section: 'option', roll: { faces: [1, 0, 0], total: 10 }, cell: '2' },
  ]
  render(<PlayLog entries={[report({ trace })]} />)
  const dice = screen.getByLabelText('Recorded dice')
  expect(dice.children).toHaveLength(4)
  expect(dice.children[2]).toHaveTextContent('option: [3, 4, 5] → 39')
  expect(dice.children[3]).toHaveTextContent('option: [1, 0, 0] → 10')
})

it('does not invent a compact dice line when no rolls were recorded', () => {
  render(<PlayLog entries={[report({ trace: [] })]} />)
  expect(screen.queryByLabelText('Recorded dice')).toBeNull()
})
