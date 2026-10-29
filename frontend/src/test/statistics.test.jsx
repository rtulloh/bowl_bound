import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import TeamStatistics from '../components/TeamStatistics'

it('displays engine statistics labels and values without recomputing them', () => {
  render(<TeamStatistics home="Home" away="Away" statistics={{ rows: [
    { label: 'Engine offense total', home: '-17', away: '42' },
    { label: 'Engine sacks', home: '3', away: '0' },
  ] }} />)
  expect(screen.getByTestId('team-statistics')).toHaveTextContent('Engine offense total')
  expect(screen.getByTestId('team-statistics')).toHaveTextContent('-17')
  expect(screen.getByTestId('team-statistics')).toHaveTextContent('42')
  expect(screen.getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['Statistic', 'Home', 'Away'])
})

it('handles older views without statistics', () => {
  const { container } = render(<TeamStatistics home="Home" away="Away" />)
  expect(container).toBeEmptyDOMElement()
})
