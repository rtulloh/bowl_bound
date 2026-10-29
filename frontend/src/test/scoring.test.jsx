import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import ScoringLedger from '../components/ScoringLedger'

it('renders engine-provided scoring events without calculating scores', () => {
  render(<ScoringLedger events={[{ number: 1, play_number: 3, team: 'Beta State', kind: 'touchdown', points: 6 }, { number: 2, play_number: 4, team: 'Beta State', kind: 'pat', points: 1 }]} />)
  expect(screen.getAllByTestId('scoring-event')).toHaveLength(2)
  expect(screen.getByTestId('scoring-ledger')).toHaveTextContent('Beta State')
  expect(screen.getByTestId('scoring-ledger')).toHaveTextContent('touchdown')
  expect(screen.getAllByTestId('scoring-event')[1]).toHaveTextContent('pat')
})

it('renders no ledger before any scoring events', () => {
  const { container } = render(<ScoringLedger events={[]} />)
  expect(container).toBeEmptyDOMElement()
})
