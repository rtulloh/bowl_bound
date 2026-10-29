import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import Scoreboard from '../components/Scoreboard'
import { view } from './fixtures'

it('shows engine-provided quarter, clock and timeout labels without running a local clock', () => {
  render(<Scoreboard view={view({ clock: { quarter: 4, remaining: 65, quarter_label: 'Q4', label: '1:05', timeouts: [2, 1] } })} />)
  expect(screen.getByTestId('quarter')).toHaveTextContent('Q4')
  expect(screen.getByTestId('game-clock')).toHaveTextContent('1:05')
  expect(screen.getByTestId('home-timeouts')).toHaveTextContent('2')
  expect(screen.getByTestId('away-timeouts')).toHaveTextContent('1')
})
