import { useState } from 'react'

const inputClass = 'block w-full text-black p-1'
const fixtureDraft = (key, week = 1) => ({ key, week, away: '', home: '', conference_game: false })
const edition = (team) => `${team.name} (${team.year ?? team.season})`
const fixtureDate = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' })

function FixtureTeam({ label, value, teams, onChange }) {
  return (
    <label>{label}
      <select className={inputClass} required value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Choose team</option>
        {teams.map((team) => <option key={team.id} value={team.id}>{edition(team)}</option>)}
      </select>
    </label>
  )
}

function CreateSeason({ teams, templates, busy, onCreate }) {
  const [name, setName] = useState('')
  const [type, setType] = useState('custom')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState({})
  const [fixtures, setFixtures] = useState([fixtureDraft(0)])
  const [nextKey, setNextKey] = useState(1)
  const [validation, setValidation] = useState('')
  const participants = teams.filter((team) => Object.hasOwn(selected, team.id))
  const visibleTeams = teams.filter((team) =>
    Object.hasOwn(selected, team.id) || edition(team).toLowerCase().includes(query.trim().toLowerCase()),
  )
  const template = templates.find((item) => item.id === type)
  const setParticipant = (team, checked) => {
    const updated = { ...selected }
    if (checked) {
      updated[team.id] = team.conference ?? ''
    } else {
      delete updated[team.id]
      setFixtures(fixtures.map((game) => ({
        ...game,
        away: game.away === team.id ? '' : game.away,
        home: game.home === team.id ? '' : game.home,
      })))
    }
    setSelected(updated)
  }
  const changeFixture = (key, patch) => setFixtures(fixtures.map((game) => (
    game.key === key ? { ...game, ...patch } : game
  )))
  const addFixture = () => {
    setFixtures([...fixtures, fixtureDraft(nextKey, fixtures.at(-1)?.week ?? 1)])
    setNextKey(nextKey + 1)
  }
  const submit = (event) => {
    event.preventDefault()
    setValidation('')
    if (!name.trim()) return setValidation('Enter a season name.')
    if (template) return onCreate({ name: name.trim(), template_id: template.id })
    if (participants.length < 2) return setValidation('Choose at least two teams.')
    if (!fixtures.length) return setValidation('Add at least one fixture.')
    const busyTeamsByWeek = new Map()
    for (const { week, away, home, conference_game } of fixtures) {
      if (!away || !home || away === home) return setValidation('Choose two different teams for each fixture.')
      const busyTeams = busyTeamsByWeek.get(week) ?? new Set()
      if (busyTeams.has(away) || busyTeams.has(home)) {
        return setValidation(`A team appears more than once in Week ${week}.`)
      }
      busyTeams.add(away).add(home)
      busyTeamsByWeek.set(week, busyTeams)
      if (conference_game && (!selected[away].trim() || selected[away].trim() !== selected[home].trim())) {
        return setValidation('A conference game requires both teams to share a conference.')
      }
    }
    return onCreate({
      name: name.trim(),
      teams: participants.map(({ id }) => ({ id, conference: selected[id].trim() })),
      fixtures: fixtures.map(({ week, away, home, conference_game }) => ({ week, away, home, conference_game })),
    })
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      <fieldset disabled={busy} className="space-y-3">
        <legend className="font-bold">New season</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          <label>Season name
            <input className={inputClass} required maxLength={160} value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>Schedule type
            <select className={inputClass} value={type} onChange={(event) => setType(event.target.value)}>
              <option value="custom">Custom schedule</option>
              {templates.map(({ id, name }) => <option key={id} value={id}>{name}</option>)}
            </select>
          </label>
        </div>
        {template ? <p>{template.coverage}</p> : <>
          <fieldset className="space-y-2">
            <legend className="font-bold">League teams</legend>
            <label>Find teams
              <input className={inputClass} type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
            <ul className="max-h-64 overflow-y-auto space-y-1">
              {visibleTeams.map((team) => (
                <li key={team.id} className="flex flex-wrap items-center gap-2">
                  <label>
                    <input className="mr-2" type="checkbox" checked={Object.hasOwn(selected, team.id)}
                      onChange={(event) => setParticipant(team, event.target.checked)} />
                    {edition(team)}
                  </label>
                  {Object.hasOwn(selected, team.id) && (
                    <input className="text-black p-1" aria-label={`${edition(team)} conference`}
                      placeholder="Conference (optional)" maxLength={100} value={selected[team.id]}
                      onChange={(event) => setSelected({ ...selected, [team.id]: event.target.value })} />
                  )}
                </li>
              ))}
            </ul>
          </fieldset>
          <fieldset className="space-y-2">
            <legend className="font-bold">Schedule</legend>
            {fixtures.map((game, index) => (
              <fieldset key={game.key} className="grid gap-2 rounded border border-gray-500 p-2 sm:grid-cols-3">
                <legend>Game {index + 1}</legend>
                <label>Game {index + 1} week
                  <input className={inputClass} type="number" required min="1" max="1000" value={game.week}
                    onChange={(event) => changeFixture(game.key, { week: event.target.value === '' ? '' : Number(event.target.value) })} />
                </label>
                <FixtureTeam label={`Game ${index + 1} away team`} value={game.away} teams={participants}
                  onChange={(away) => changeFixture(game.key, { away })} />
                <FixtureTeam label={`Game ${index + 1} home team`} value={game.home} teams={participants}
                  onChange={(home) => changeFixture(game.key, { home })} />
                <label>
                  <input className="mr-2" type="checkbox" checked={game.conference_game}
                    onChange={(event) => changeFixture(game.key, { conference_game: event.target.checked })} />
                  Conference game
                </label>
                <button type="button" className="play-button"
                  onClick={() => setFixtures(fixtures.filter(({ key }) => key !== game.key))}>Remove game {index + 1}</button>
              </fieldset>
            ))}
            <button type="button" className="play-button" onClick={addFixture}>Add fixture</button>
          </fieldset>
        </>}
        {validation && <p role="alert">{validation}</p>}
        <button type="submit" className="play-button">Create season</button>
      </fieldset>
    </form>
  )
}

function Schedule({ season, busy, onPlay, onReset, onRemoveResult }) {
  const [side, setSide] = useState('home')
  const [week, setWeek] = useState('')
  const [confirm, setConfirm] = useState(null)
  const { snapshot, games } = season
  const teams = new Map(snapshot.teams.map((team) => [team.id, team]))
  const weeks = [...new Set(snapshot.fixtures.map((game) => game.week))].sort((a, b) => a - b)
  const fixtures = snapshot.fixtures.filter((game) => !week || String(game.week) === week)
  return (
    <section aria-label="Season schedule" className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-2">
        <label>Show week
          <select className={inputClass} value={week} onChange={(event) => setWeek(event.target.value)}>
            <option value="">All weeks</option>
            {weeks.map((item) => <option key={item} value={item}>Week {item}</option>)}
          </select>
        </label>
        <label>Control team for new games
          <select className={inputClass} value={side} onChange={(event) => setSide(event.target.value)}>
            <option value="home">Home</option>
            <option value="away">Away</option>
            <option value="manual">Both teams (manual)</option>
          </select>
        </label>
      </div>
      <ul className="divide-y divide-gray-500">
        {fixtures.map((fixture) => {
          const game = games?.[fixture.id]
          const result = snapshot.results[fixture.id]
          const inProgress = game?.status === 'in_progress'
          const remove = result ? onRemoveResult : onReset
          return (
            <li className="flex flex-wrap items-center justify-between gap-2 py-2" key={fixture.id}>
              <div>
                <p className="font-bold">{edition(teams.get(fixture.away))} at {edition(teams.get(fixture.home))}</p>
                <p>
                  Week {fixture.week}
                  {fixture.date && <> · <time dateTime={fixture.date}>{fixtureDate.format(new Date(fixture.date))}</time></>}
                  {fixture.conference_game && ' · Conference game'}
                </p>
                {result ? <p>Final <span>{result.away_score}–{result.home_score}</span></p>
                  : <p>{inProgress ? 'In progress' : 'Scheduled'}</p>}
              </div>
              <div className="flex flex-wrap gap-2">
                {!result && onPlay && (
                  <button type="button" className="play-button" disabled={busy}
                    onClick={() => onPlay(season, fixture, side)}>{inProgress ? 'Resume game' : 'Play game'}</button>
                )}
                {(result || inProgress) && remove && (
                  confirm === fixture.id ? <>
                    <button type="button" className="play-button" disabled={busy}
                      onClick={async () => {
                        await remove(season, fixture)
                        setConfirm(null)
                      }}>{result ? 'Confirm removal' : 'Confirm restart'}</button>
                    <button type="button" className="play-button" onClick={() => setConfirm(null)}>Cancel</button>
                  </> : <button type="button" className="play-button" disabled={busy}
                    onClick={() => setConfirm(fixture.id)}>{result ? 'Remove result' : 'Discard progress'}</button>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function SeasonTable({ name, columns, children }) {
  return (
    <div className="max-w-full overflow-x-auto">
      <table aria-label={name} className="w-full text-left whitespace-nowrap">
        <thead className="border-b border-gray-500">
          <tr>{columns.map((label) => <th key={label} className="p-2" scope="col">{label}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-gray-500">{children}</tbody>
      </table>
    </div>
  )
}

function Cells({ values }) {
  return values.map((value, index) => <td className="p-2" key={index}>{value}</td>)
}

function TeamCell({ team }) {
  return <th scope="row" className="p-2">{edition(team)}</th>
}

const record = (wins, losses, ties) => `${wins}–${losses}–${ties}`
const percentage = (number) => number == null ? '—' : `${(100 * number).toFixed(1)}%`

function Standings({ summary, teams }) {
  const [group, setGroup] = useState('')
  const conference = summary.conferences.find(({ name }) => name === group)
  const displayed = conference
    ? conference.team_ids.map((id) => teams.get(id))
    : [...summary.teams].sort((left, right) =>
      (right.win_percentage ?? -1) - (left.win_percentage ?? -1)
      || right.wins - left.wins
      || left.name.localeCompare(right.name),
    )
  return (
    <section aria-label="Standings" className="space-y-2">
      {summary.conferences.length > 0 && <label>Conference
        <select className={inputClass} value={group} onChange={(event) => setGroup(event.target.value)}>
          <option value="">All teams</option>
          {summary.conferences.map(({ name }) => <option key={name}>{name}</option>)}
        </select>
      </label>}
      <SeasonTable name={conference?.name ?? 'Overall standings'}
        columns={['Team', 'Overall W–L–T', 'Conference W–L–T', 'Points for', 'Points against']}>
        {displayed.map((team) => (
          <tr key={team.team_id}>
            <TeamCell team={team} />
            <Cells values={[
              record(team.wins, team.losses, team.ties),
              team.conference ? record(team.conference_wins, team.conference_losses, team.conference_ties) : '—',
              team.points_for,
              team.points_against,
            ]} />
          </tr>
        ))}
      </SeasonTable>
    </section>
  )
}

const totalsGroups = [
  ['Total', 'total_yards', 'Total yards'],
  ['Passing', 'passing_yards', 'Passing yards'],
  ['Rushing', 'rushing_yards', 'Rushing yards'],
  ['Points', 'points', 'Points'],
]
const rate = (key, label, unit = 'YDS/G') => [key + '_per_game', unit, label + ' per game']
const seasonStatCategories = {
  Offense: [['Total', 'Total yards'], ['Passing'], ['Rushing'], ['Receiving'], ['Downs']],
  Defense: [['Total', 'Yards allowed'], ['Points', 'Points allowed'], ['Turnovers'], ['Passing'], ['Rushing'], ['Receiving'], ['Downs']],
  'Special teams': [['Returning'], ['Kicking'], ['Punting']],
}
const unavailableCategory = {
  Downs: 'down and conversion statistics',
  Returning: 'return statistics',
  Kicking: 'kicking statistics',
  Punting: 'punting statistics',
}
const detailColumns = {
  Points: [['points', 'PTS', 'Points'], rate('points', 'Points', 'PTS/G')],
  Turnovers: [['interceptions', 'INT', 'Interceptions made']],
  Receiving: [
    ['completions', 'REC', 'Receptions'],
    ['passing_yards', 'YDS', 'Receiving yards'],
    rate('passing_yards', 'Receiving yards'),
    ['passing_touchdowns', 'TD', 'Receiving touchdowns'],
  ],
  Passing: [
    ['completions', 'CMP', 'Completions'],
    ['passing_attempts', 'ATT', 'Pass attempts'],
    ['passing_yards', 'YDS', 'Passing yards'],
    rate('passing_yards', 'Passing yards'),
    ['passing_touchdowns', 'TD', 'Passing touchdowns'],
    ['interceptions', 'INT', 'Interceptions'],
    ['sacks_taken', 'SACK', 'Sacks'],
    ['sack_yards_lost', 'SYL', 'Sack yards lost'],
  ],
  Rushing: [
    ['rushing_attempts', 'ATT', 'Rush attempts'],
    ['rushing_yards', 'YDS', 'Rush yards'],
    rate('rushing_yards', 'Rush yards'),
    ['rushing_touchdowns', 'TD', 'Rushing touchdowns'],
  ],
}
const overallColumns = totalsGroups.flatMap(([group, key, label]) => [
  [key, group === 'Points' ? 'PTS' : 'YDS', label],
  rate(key, label, group === 'Points' ? 'PTS/G' : 'YDS/G'),
])
const statNumber = new Intl.NumberFormat('en-US')
const statAverage = new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

const leaderCategories = [
  ['Total offense', 'YDS/G', (team) => team.per_game?.total_yards],
  ['Passing', 'YDS/G', (team) => team.per_game?.passing_yards],
  ['Rushing', 'YDS/G', (team) => team.per_game?.rushing_yards],
  ['Scoring', 'PTS/G', (team) => team.points_for / team.games_played],
  ['Total defense', 'YDS/G allowed', (team) => team.allowed_per_game?.total_yards, true],
]

function SeasonLeaders({ teams }) {
  return (
    <section aria-label="Season leaders at a glance" className="space-y-3">
      <h3 className="text-lg font-semibold">Season leaders at a glance</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {leaderCategories.map(([label, unit, measure, ascending]) => {
          const leaders = teams.filter((team) => team.games_played && Number.isFinite(measure(team)))
            .sort((left, right) => (ascending ? 1 : -1) * (measure(left) - measure(right))
              || left.name.localeCompare(right.name)).slice(0, 5)
          return (
            <section key={label} className="rounded-lg border border-slate-600 bg-slate-800 p-3">
              <h4 className="font-semibold text-amber-300">{label}</h4>
              <p className="text-xs text-slate-300">{unit}</p>
              {leaders.length ? <ol className="mt-2 divide-y divide-slate-600">
                {leaders.map((team, index) => (
                  <li className="flex items-baseline gap-2 py-2 text-sm" key={team.team_id}>
                    <span className="text-slate-300">{index + 1}</span>
                    <span className="flex-1">{edition(team)}</span>
                    <strong className="tabular-nums">{measure(team).toFixed(1)}</strong>
                  </li>
                ))}
              </ol> : <p className="mt-2 text-sm text-slate-300">No completed games</p>}
            </section>
          )
        })}
      </div>
    </section>
  )
}

function SeasonStatistics({ summary }) {
  const [side, setSide] = useState('Offense')
  const [group, setGroup] = useState('Total')
  const [conference, setConference] = useState('')
  const [sort, setSort] = useState({ key: 'total_yards_per_game', direction: 'descending' })
  const select = (nextSide, nextGroup) => {
    setSide(nextSide)
    setGroup(nextGroup)
    const key = {
      Total: 'total_yards_per_game',
      Passing: 'passing_yards_per_game',
      Rushing: 'rushing_yards_per_game',
      Receiving: 'passing_yards_per_game',
      Points: 'points_per_game',
      Turnovers: 'interceptions',
    }[nextGroup] ?? 'games_played'
    setSort({ key, direction: nextSide === 'Defense' && nextGroup !== 'Turnovers' ? 'ascending' : 'descending' })
  }
  const total = group === 'Total'
  const columns = total ? overallColumns : detailColumns[group]
  const defense = side === 'Defense'
  const value = (team, key) => {
    if (key === 'games_played') return team.games_played
    if (!team.games_played) return null
    const perGame = key.endsWith('_per_game')
    const stat = key.replace(/_per_game$/, '')
    if (stat === 'points') {
      const points = defense ? team.points_against : team.points_for
      return perGame ? points / team.games_played : points
    }
    const view = perGame ? 'per_game' : 'totals'
    return team[defense ? `allowed_${view}` : view]?.[stat]
  }
  const ordered = summary.teams.filter((team) => !conference || team.conference === conference).sort((left, right) => {
    const a = value(left, sort.key)
    const b = value(right, sort.key)
    if (a == null || b == null) return Number(a == null) - Number(b == null) || left.name.localeCompare(right.name)
    return (sort.direction === 'ascending' ? a - b : b - a) || left.name.localeCompare(right.name)
  })
  const highlight = (key) => sort.key === key ? 'bg-sky-900/50' : ''
  const header = (key, short, label, rowSpan = 1) => {
    const description = defense ? label.replace(/^Points/, 'Points allowed') : label
    return (
      <th scope="col" rowSpan={rowSpan} className={`px-2 py-1.5 text-right ${highlight(key)}`}
        key={key} aria-sort={sort.key === key ? sort.direction : undefined}>
        <button type="button" aria-label={description} title={description} className="underline decoration-slate-500 underline-offset-2"
          onClick={() => setSort({
            key, direction: sort.key === key && sort.direction === 'descending' ? 'ascending' : 'descending',
          })}>{short}{sort.key === key && <span aria-hidden="true">{sort.direction === 'ascending' ? ' ↑' : ' ↓'}</span>}</button>
      </th>
    )
  }
  return (
    <section className="space-y-4 rounded-xl border border-slate-600 bg-slate-900 p-4" aria-label="Team statistics">
      <h3 className="text-xl font-bold">{side} statistics</h3>
      <nav aria-label="Team statistics categories" className="grid gap-4 sm:grid-cols-3">
        {Object.entries(seasonStatCategories).map(([label, categories]) => (
          <div key={label} className="border-t-2 border-slate-500">
            <h4 className="px-2 py-2 font-semibold">{label}</h4>
            {categories.map(([category, title = category]) => (
              <button key={category} type="button" aria-label={`${label}: ${title}`}
                aria-pressed={label === side && category === group}
                className="block w-full border-t border-slate-700 px-2 py-2 text-left even:bg-slate-800 aria-pressed:text-amber-300"
                onClick={() => select(label, category)}>{title}</button>
            ))}
          </div>
        ))}
      </nav>
      <div className="grid grid-cols-3 border-b border-slate-600">
        {Object.keys(seasonStatCategories).map((label) => (
          <button key={label} type="button" aria-pressed={side === label}
            className={`border-b-2 py-2 font-semibold ${side === label ? 'border-amber-300 text-amber-300' : 'border-transparent text-slate-300'}`}
            onClick={() => select(label, seasonStatCategories[label][0][0])}>{label}</button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <select className="rounded-full border border-slate-500 bg-slate-800 px-3 py-2 text-sm" aria-label="Statistic category"
          value={group} onChange={(event) => select(side, event.target.value)}>
          {seasonStatCategories[side].map(([category, title = category]) => <option key={category} value={category}>{title}</option>)}
        </select>
        {summary.conferences.length > 0 && (
          <select className="rounded-full border border-slate-500 bg-slate-800 px-3 py-2 text-sm" aria-label="Statistics conference"
            value={conference} onChange={(event) => setConference(event.target.value)}>
            <option value="">All conferences</option>
            {summary.conferences.map(({ name }) => <option key={name}>{name}</option>)}
          </select>
        )}
      </div>
      {group === 'Turnovers' && <p className="text-sm text-slate-300">Season box scores include interceptions. Fumble recoveries are unavailable.</p>}
      {columns ? <div className="max-w-full overflow-x-auto">
        <table aria-label="Season team statistics" className="w-full whitespace-nowrap text-sm tabular-nums">
          <colgroup span="2" />
          {total && totalsGroups.map(([label]) => <colgroup key={label} span="2" className="border-l border-slate-700" />)}
          <thead className="border-y border-slate-600 text-xs uppercase tracking-wide text-slate-200">
            <tr>
              <th scope="col" rowSpan={total ? 2 : 1} className="px-2 py-1.5 text-left align-bottom">Team</th>
              {header('games_played', 'GP', 'Games played', total ? 2 : 1)}
              {total
                ? totalsGroups.map(([label]) => <th key={label} scope="colgroup" colSpan="2" className="border-b border-slate-700 px-2 py-1.5">{label}</th>)
                : columns.map(([key, short, label]) => header(key, short, label))}
            </tr>
            {total && <tr>{columns.map(([key, short, label]) => header(key, short, label))}</tr>}
          </thead>
          <tbody className="divide-y divide-slate-800">
            {ordered.map((team) => (
              <tr key={team.team_id} className="even:bg-slate-800/50">
                <th scope="row" className="px-2 py-1.5 text-left font-medium">{edition(team)}</th>
                <td className={`px-2 py-1.5 text-right ${highlight('games_played')}`}>{team.games_played}</td>
                {columns.map(([key]) => {
                  const number = value(team, key)
                  const format = key.endsWith('_per_game') ? statAverage : statNumber
                  return <td key={key} className={`px-2 py-1.5 text-right ${highlight(key)}`}>
                    {number == null ? '—' : format.format(number)}
                  </td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div> : <p className="text-sm text-slate-300">Season box scores do not include {unavailableCategory[group]}.</p>}
      {summary.teams.some((team) => team.games_played) && <SeasonLeaders teams={summary.teams} />}
    </section>
  )
}

function Rankings({ summary, teams }) {
  if (!summary.rankings.length) return <p>Rankings appear after the first completed game.</p>
  return (<section className="space-y-2">
    <h3 className="text-lg font-semibold">Top 25</h3>
    <p className="text-sm text-slate-300">Tiebreakers use offense yards, points scored, and yards allowed per game.</p>
    <SeasonTable name="Season rankings" columns={['Team', 'Rank', 'W–L–T', 'Schedule strength', 'Rating']}>
      {summary.rankings.map(({ team_id, rank, strength_of_schedule, rating }) => {
        const team = teams.get(team_id)
        return (
          <tr key={team_id}>
            <TeamCell team={team} />
            <Cells values={[rank, record(team.wins, team.losses, team.ties), percentage(strength_of_schedule), percentage(rating)]} />
          </tr>
        )
      })}
    </SeasonTable>
  </section>)
}

const views = ['Schedule', 'Standings', 'Team statistics', 'Rankings']

function SeasonDesk({ season, busy, onPlay, onReset, onRemoveResult }) {
  const [panel, setPanel] = useState(views[0])
  const { summary } = season
  const teams = new Map(summary.teams.map((team) => [team.team_id, team]))
  return (
    <>
      <nav aria-label="Season views" className="flex flex-wrap gap-2">
        {views.map((view) => (
          <button type="button" key={view} className="play-button" aria-pressed={panel === view}
            onClick={() => setPanel(view)}>{view}</button>
        ))}
      </nav>
      {panel === 'Schedule' && <Schedule season={season} busy={busy} onPlay={onPlay} onReset={onReset} onRemoveResult={onRemoveResult} />}
      {panel === 'Standings' && <Standings summary={summary} teams={teams} />}
      {panel === 'Team statistics' && <SeasonStatistics summary={summary} />}
      {panel === 'Rankings' && <Rankings summary={summary} teams={teams} />}
    </>
  )
}

export default function SeasonManager({ teams = [], templates = [], seasons = [], busy, onCreate, onPlay, onReset, onRemoveResult }) {
  const [seasonId, setSeasonId] = useState('')
  const [creating, setCreating] = useState(false)
  const season = seasons.find(({ snapshot }) => snapshot.id === seasonId) ?? seasons[0]
  const create = async (payload) => {
    const created = await onCreate(payload)
    if (created?.snapshot?.id) {
      setSeasonId(created.snapshot.id)
      setCreating(false)
    }
  }
  return (
    <section aria-label="Season manager" className="space-y-4">
      <h2 className="text-xl font-bold">Seasons</h2>
      {season && (
        <div className="flex items-end flex-wrap gap-2">
          <label>Saved season
            <select className={inputClass} value={season.snapshot.id} disabled={busy}
              onChange={(event) => {
                setSeasonId(event.target.value)
                setCreating(false)
              }}>
              {seasons.map(({ snapshot }) => <option key={snapshot.id} value={snapshot.id}>{snapshot.name}</option>)}
            </select>
          </label>
          {onCreate && <button type="button" className="play-button" disabled={busy}
            onClick={() => setCreating(!creating)}>{creating ? 'Cancel new season' : 'New season'}</button>}
        </div>
      )}
      {(!season || creating) && onCreate && <CreateSeason teams={teams} templates={templates} busy={busy} onCreate={create} />}
      {season && !creating && (
        <SeasonDesk key={season.snapshot.id} season={season} busy={busy} onPlay={onPlay} onReset={onReset}
          onRemoveResult={onRemoveResult} />
      )}
    </section>
  )
}
