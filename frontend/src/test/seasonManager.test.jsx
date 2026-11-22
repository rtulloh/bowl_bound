import { fireEvent, render, screen, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import SeasonManager from '../components/SeasonManager'

const teams = [
  { id: '2007/cedar', name: 'Cedar Valley', season: 2007 },
  { id: '2007/harbor', name: 'Harbor Tech', season: 2007 },
]

it('lets players choose a historical schedule or enter their own fixture and conferences', () => {
  const onCreate = vi.fn()
  render(<SeasonManager teams={teams} templates={[{ id: 'ncaa-2007', name: '2007 NCAA' }]} seasons={[]} onCreate={onCreate} />)
  fireEvent.change(screen.getByLabelText('Season name'), { target: { value: 'My replay' } })
  fireEvent.change(screen.getByLabelText('Schedule type'), { target: { value: 'ncaa-2007' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create season' }))
  expect(onCreate).toHaveBeenCalledWith({ name: 'My replay', template_id: 'ncaa-2007' })

  fireEvent.change(screen.getByLabelText('Schedule type'), { target: { value: 'custom' } })
  fireEvent.change(screen.getByLabelText('Season name'), { target: { value: 'Saturday league' } })
  fireEvent.click(screen.getByLabelText('Cedar Valley (2007)'))
  fireEvent.click(screen.getByLabelText('Harbor Tech (2007)'))
  fireEvent.change(screen.getByLabelText('Cedar Valley (2007) conference'), { target: { value: 'Big Eight' } })
  fireEvent.change(screen.getByLabelText('Harbor Tech (2007) conference'), { target: { value: 'SEC' } })
  fireEvent.change(screen.getByLabelText('Game 1 away team'), { target: { value: '2007/cedar' } })
  fireEvent.change(screen.getByLabelText('Game 1 home team'), { target: { value: '2007/harbor' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create season' }))
  expect(onCreate).toHaveBeenLastCalledWith({
    name: 'Saturday league',
    teams: [
      { id: '2007/cedar', conference: 'Big Eight' },
      { id: '2007/harbor', conference: 'SEC' },
    ],
    fixtures: [{ week: 1, away: '2007/cedar', home: '2007/harbor', conference_game: false }],
  })
})

const [away, home] = teams.map((team) => team.id)
const completed = { id: 'g1', week: 1, away, home, conference_game: true, date: '2007-09-01' }
const unfinished = { id: 'g2', week: 2, away: home, home: away, conference_game: true }
const season = {
  snapshot: {
    id: 'a',
    name: 'Saturday league',
    fixtures: [completed, unfinished],
    results: { g1: { away_score: 10, home_score: 14 } },
    teams: teams.map((team) => ({ ...team, year: team.season, conference: 'Big Eight' })),
  },
  games: { g2: { status: 'in_progress' } },
  summary: {
    teams: [
      { team_id: away, name: 'Cedar Valley', year: 2007, games_played: 1, wins: 0, losses: 1, ties: 0, conference_wins: 0, conference_losses: 1, conference_ties: 0, points_for: 10, points_against: 14, totals: { total_yards: 212 }, per_game: { total_yards: 212 } },
      { team_id: home, name: 'Harbor Tech', year: 2007, games_played: 1, wins: 1, losses: 0, ties: 0, conference_wins: 1, conference_losses: 0, conference_ties: 0, points_for: 14, points_against: 10, totals: { total_yards: 231 }, per_game: { total_yards: 231 } },
    ],
    conferences: [{ name: 'Big Eight', team_ids: [home, away] }],
    rankings: [{ team_id: home, rank: 1, strength_of_schedule: 0.5, rating: 0.8 }],
  },
}

it('resumes a scheduled game and displays backend standings, totals and rankings', () => {
  const onPlay = vi.fn()
  render(<SeasonManager seasons={[season]} onPlay={onPlay} />)
  expect(screen.getByText('10–14')).toBeInTheDocument()
  expect(screen.getByText('Sep 1, 2007')).toHaveAttribute('datetime', '2007-09-01')
  fireEvent.click(screen.getByRole('button', { name: 'Resume game' }))
  expect(onPlay).toHaveBeenCalledWith(season, unfinished, 'home')

  fireEvent.click(screen.getByRole('button', { name: 'Standings' }))
  fireEvent.change(screen.getByLabelText('Conference'), { target: { value: 'Big Eight' } })
  expect(screen.getByRole('table', { name: 'Big Eight' })).toHaveTextContent('Harbor Tech (2007)')
  fireEvent.click(screen.getByRole('button', { name: 'Team statistics' }))
  expect(screen.getByRole('table', { name: 'Season team statistics' })).toHaveTextContent('231')
  expect(screen.getByRole('region', { name: 'Season leaders at a glance' })).toBeVisible()
  const totals = screen.getByRole('table', { name: 'Season team statistics' })
  expect(within(totals).getByRole('columnheader', { name: 'Passing', exact: true })).toHaveAttribute('colspan', '2')
  expect(within(totals).getByRole('button', { name: 'Total yards per game' })).toHaveTextContent('YDS/G')
  fireEvent.change(screen.getByLabelText('Statistic category'), { target: { value: 'Passing' } })
  expect(screen.queryByRole('columnheader', { name: 'Rush yards' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Defense', exact: true }))
  expect(screen.getByRole('button', { name: 'Defense', exact: true })).toHaveAttribute('aria-pressed', 'true')
  fireEvent.click(screen.getByRole('button', { name: 'Rankings' }))
  expect(screen.getByRole('table', { name: 'Season rankings' })).toHaveTextContent('50.0%')
})

it('requires explicit confirmation to remove a completed result', () => {
  const onRemoveResult = vi.fn()
  render(<SeasonManager seasons={[season]} onRemoveResult={onRemoveResult} />)
  fireEvent.click(screen.getByRole('button', { name: 'Remove result' }))
  expect(onRemoveResult).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Confirm removal' }))
  expect(onRemoveResult).toHaveBeenCalledWith(season, completed)
})

it('shows overall records for custom leagues without conferences', () => {
  render(<SeasonManager seasons={[{ ...season, summary: { ...season.summary, conferences: [] } }]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Standings' }))
  expect(screen.getByRole('table', { name: 'Overall standings' })).toHaveTextContent('Harbor Tech (2007)')
  expect(screen.getByRole('table', { name: 'Overall standings' })).toHaveTextContent('1–0–0')
})
