import { useMemo, useState } from 'react'
import TeamPicker from './TeamPicker'

const SAMPLE_HOME = '2007/cedar-valley'
const SAMPLE_AWAY = '2007/harbor-tech'

function teamsInSeason(teams, season) {
  return teams.filter((team) => String(team.season) === String(season))
}

function slugOf(teamId) {
  return teamId ? teamId.split('/')[1] : ''
}

function initialSides(teams) {
  if (!teams.length) {
    return { home: { season: '', teamId: '' }, away: { season: '', teamId: '' } }
  }
  const sampleHome = teams.find((team) => team.id === SAMPLE_HOME)
  const seasons = teams.map((team) => String(team.season)).sort().reverse()
  const season = sampleHome ? String(sampleHome.season) : seasons[0]
  const inSeason = teamsInSeason(teams, season)
  const home = sampleHome || inSeason[0]
  const away = teams.find((team) => team.id === SAMPLE_AWAY) || inSeason.find((team) => team.id !== home.id)
  return {
    home: { season, teamId: home.id },
    away: away ? { season: String(away.season), teamId: away.id } : { season, teamId: '' },
  }
}

function SeasonSelect({ testId, teams, value, onChange, disabled }) {
  const seasons = useMemo(
    () => [...new Set(teams.map((team) => String(team.season)))].sort().reverse(),
    [teams],
  )
  return (
    <label className="block">
      Season
      <select
        className="block w-full text-black p-1"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        data-testid={testId}
      >
        {seasons.map((season) => (
          <option key={season} value={season}>
            {season} ({teamsInSeason(teams, season).length} teams)
          </option>
        ))}
      </select>
    </label>
  )
}

export default function MatchupBuilder({
  teams,
  home,
  away,
  onHomeChange,
  onAwayChange,
  onSwap,
  onUseSameSeason,
  disabled,
  rules,
  children,
}) {
  const [notice, setNotice] = useState({ home: '', away: '' })
  const byId = useMemo(() => new Map(teams.map((team) => [team.id, team])), [teams])
  const sameSeason = Boolean(home.season && away.season && home.season === away.season)
  const raise = (side, message) => setNotice((current) => ({ ...current, [side]: message }))

  const changeSeason = (side, season) => {
    const current = side === 'home' ? home : away
    const slug = slugOf(current.teamId)
    const carried = teamsInSeason(teams, season).find((team) => slugOf(team.id) === slug)
    const change = side === 'home' ? onHomeChange : onAwayChange
    change({ season, teamId: carried ? carried.id : '' })
    raise(side, carried || !current.teamId ? '' : `Choose a ${season} team for this side.`)
  }

  const changeTeam = (side, teamId) => {
    const current = side === 'home' ? home : away
    const team = byId.get(teamId)
    const change = side === 'home' ? onHomeChange : onAwayChange
    // Clearing a team keeps the side's season so its list stays usable.
    change({ season: team ? String(team.season) : current.season, teamId })
    raise(side, '')
  }

  const side = (name) => {
    const value = name === 'home' ? home : away
    return (
      <fieldset className="space-y-3" data-testid={`${name}-card`}>
        <legend className="font-bold uppercase">{name === 'home' ? 'Home' : 'Away'}</legend>
        <SeasonSelect
          testId={`${name}-season`}
          teams={teams}
          value={value.season}
          onChange={(season) => changeSeason(name, season)}
          disabled={disabled}
        />
        <TeamPicker
          testId={`${name}-select`}
          label={name === 'home' ? 'Home team' : 'Away team'}
          teams={teams}
          season={value.season}
          value={value.teamId}
          onSelect={(team) => changeTeam(name, team ? team.id : '')}
          disabled={disabled}
        />
        {notice?.[name] && (
          <p className="text-sm text-yellow-200" role="status">
            {notice[name]}
          </p>
        )}
      </fieldset>
    )
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-start">
        {side('home')}
        <button
          type="button"
          className="play-button text-black self-center"
          onClick={() => { onSwap(); setNotice({ home: '', away: '' }) }}
          disabled={disabled}
          data-testid="swap-sides"
          aria-label="Swap home and away"
        >
          ⇄
        </button>
        {side('away')}
      </div>
      {!sameSeason && home.season && (
        <button type="button" className="text-sm underline" onClick={() => { onUseSameSeason(); raise('away', '') }} data-testid="same-season">
          Use {home.season} for both teams
        </button>
      )}
      {rules && (
        <section
          className={`rounded border p-3 text-sm ${rules.supported ? 'border-green-700 bg-green-950/40' : 'border-red-700 bg-red-950/40'}`}
          aria-live="polite"
          data-testid="rules-banner"
        >
          <p className="font-bold">{rules.summary}</p>
          <p className="mt-1">Kickoff placement, touchbacks, timing and overtime follow the home season. Both teams keep their own charts and rosters.</p>
          {rules.details?.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-2">
              {rules.details.map((detail) => (
                <li key={detail} className="rounded bg-green-900/60 px-2 py-1 text-xs">{detail}</li>
              ))}
            </ul>
          )}
        </section>
      )}
      {children}
    </div>
  )
}

export { initialSides }
