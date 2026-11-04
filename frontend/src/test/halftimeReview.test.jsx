import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import HalftimeReview from '../components/HalftimeReview'

const review = {
  title: 'HALFTIME',
  lines: ['Legacy prose is deliberately unrelated to the structured recap.'],
  action: { key: 'review:continue', label: 'START 2ND HALF' },
  halftime: {
    home: { name: 'Cedar Valley', first: 2, second: 9, total: 11 },
    away: { name: 'Harbor Tech', first: 0, second: 7, total: 7 },
    summary: 'Cedar Valley leads',
    scoring: ['Play 22: Cedar Valley safety +2.', 'Play 56: Harbor Tech touchdown +6.'],
    statistics: [{ label: 'Total offense yards', home: '127', away: '48' }],
    kickoff: 'Cedar Valley kicks to Harbor Tech to start the second half.',
  },
}

describe('Paydirt-style halftime recap', () => {
  it('renders prominent scores, separate tables and scoring from engine facts', () => {
    render(<HalftimeReview review={review} onContinue={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'HALFTIME' })).toBeVisible()
    expect(screen.getByTestId('halftime-home-score')).toHaveTextContent('11')
    expect(screen.getByTestId('halftime-away-score')).toHaveTextContent('7')
    expect(screen.getByText('Cedar Valley leads')).toBeVisible()
    fireEvent.click(screen.getByText('First-half details'))
    expect(screen.getByRole('table', { name: 'First-half score' })).toBeVisible()
    const rows = within(screen.getByRole('table', { name: 'First-half score' })).getAllByRole('row')
    expect(within(rows[1]).getByRole('rowheader')).toHaveTextContent('Harbor Tech')
    expect(within(rows[1]).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['0', '7', '7'])
    expect(within(rows[2]).getByRole('rowheader')).toHaveTextContent('Cedar Valley')
    expect(within(rows[2]).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['2', '9', '11'])
    const statistics = screen.getByRole('table', { name: 'First-half team statistics' })
    expect(within(statistics).getByRole('rowheader')).toHaveTextContent('Total offense yards')
    expect(within(statistics).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['48', '127'])
    expect(screen.getByRole('heading', { name: 'SCORING SUMMARY' })).toBeVisible()
    expect(screen.getByText(review.halftime.scoring[0])).toBeVisible()
    expect(screen.getByText(review.halftime.kickoff)).toBeVisible()
    expect(screen.queryByText(review.lines[0])).toBeNull()
  })

  it('displays the engine summary verbatim and leaves football decisions to the backend', () => {
    render(<HalftimeReview review={{ ...review, halftime: { ...review.halftime, summary: 'Engine supplied summary' } }} onContinue={vi.fn()} />)
    expect(screen.getByText('Engine supplied summary')).toBeVisible()
    expect(screen.queryByText('Cedar Valley leads')).toBeNull()
  })

  it('continues only when requested and respects a pending request', () => {
    const onContinue = vi.fn()
    const { rerender } = render(<HalftimeReview review={review} onContinue={onContinue} />)
    expect(onContinue).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'START 2ND HALF' }))
    expect(onContinue).toHaveBeenCalledOnce()
    rerender(<HalftimeReview review={review} busy onContinue={onContinue} />)
    expect(screen.getByRole('button', { name: 'START 2ND HALF' })).toBeDisabled()
  })

  it('retains a final conversion result when it shares the halftime review', () => {
    render(<HalftimeReview review={{ ...review, halftime: { ...review.halftime, result: 'Harbor Tech two-point conversion no good.' } }} onContinue={vi.fn()} />)
    expect(screen.getByText('Harbor Tech two-point conversion no good.')).toBeVisible()
  })

  it('keeps the primary view as simple as the owner screenshot', () => {
    render(<HalftimeReview review={review} onContinue={vi.fn()} />)
    expect(screen.getByText('End of 2nd Quarter')).toBeVisible()
    expect(screen.getAllByTestId('halftime-team-badge').map((badge) => badge.textContent)).toEqual(['HM', 'AW'])
    expect(screen.getByText('First-half details').closest('details')).not.toHaveAttribute('open')
    expect(screen.getByRole('table', { name: 'First-half score', hidden: true })).not.toBeVisible()
    expect(screen.getByRole('table', { name: 'First-half team statistics', hidden: true })).not.toBeVisible()
    expect(screen.getAllByRole('button')).toHaveLength(1)
  })
})
