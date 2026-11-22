import { useEffect, useRef, useState } from 'react'
import { coachStep, decide, gameAction, getRules, kick, listTeams, newGame, saveGame, snap } from './api'
import { createSeason, listSeasonTemplates, loadGame, recordSeasonResult, removeSeasonResult, summarizeSeason } from './api'
import SeasonManager from './components/SeasonManager'
import FootballField from './components/FootballField'
import { GamePlayLog } from './components/PlayLog'
import PlaySelector from './components/PlaySelector'
import Scoreboard from './components/Scoreboard'
import PenaltyChoices from './components/PenaltyChoices'
import ScoringLedger from './components/ScoringLedger'
import ClockChoices from './components/ClockChoices'
import TeamStatistics from './components/TeamStatistics'
import SaveControls from './components/SaveControls'
import BrowserSaves from './components/BrowserSaves'
import { listSavedSeasons, writeSavedGame, writeSavedSeason } from './runtime/gameLibrary'
import CoinToss from './components/CoinToss'
import DiceRoll from './components/DiceRoll'
import HalftimeReview from './components/HalftimeReview'
import ChartViewer from './components/ChartViewer'
import MatchupBuilder, { initialSides } from './components/MatchupBuilder'
import CatalogProblems from './components/CatalogProblems'

const gameName = (game) => game ? `${game.view.home} vs ${game.view.away}`.slice(0, 160) : ''

export default function App() {
  const browser = import.meta.env.MODE === 'browser'
  const [showSeasons, setShowSeasons] = useState(false)
  const [seasonRecords, setSeasonRecords] = useState([])
  const [seasonTemplates, setSeasonTemplates] = useState([])
  const [conferences, setConferences] = useState({})
  const linkedFixture = useRef(null)
  const [saveStatus, setSaveStatus] = useState(null)
  const savedGame = useRef(null)
  const saveIdentity = useRef(null)
  const [teams, setTeams] = useState(null)
  const [catalogProblems, setCatalogProblems] = useState([])
  const [home, setHome] = useState({ season: '', teamId: '' })
  const [away, setAway] = useState({ season: '', teamId: '' })

  const [gameType, setGameType] = useState('regular')
  const [rules, setRules] = useState(null)
  const [rulesError, setRulesError] = useState('')
  const [rulesAttempt, setRulesAttempt] = useState(0)
  const [difficulty, setDifficulty] = useState('medium')
  const [game, setGame] = useState(null)
  const [offense, setOffense] = useState('')
  const [defense, setDefense] = useState('')
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const [computerError, setComputerError] = useState('')
  const [busy, setBusy] = useState(false)
  const [hurryMode, setHurryMode] = useState(false)
  const [completeHistory, setCompleteHistory] = useState(false)
  const [revealedToss, setRevealedToss] = useState(null)
  const [control, setControl] = useState('home')
  const gameMenu = useRef(null)
  const inFlight = useRef(false)
  const automaticCount = useRef(0)
  const openingRevealed = Boolean(game && revealedToss === game.game_id)
  useEffect(() => {
    if (!game || game.view.phase !== "opening_choice" || openingRevealed) return
    const reveal = () => setRevealedToss(game.game_id)
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) { reveal(); return }
    const timer = setTimeout(reveal, 1000) // Presentation only; no engine command or dice.
    return () => clearTimeout(timer)
  }, [game?.game_id, game?.view.phase, openingRevealed])
  useEffect(() => {
    setOffense('')
    setDefense('')
  }, [game?.game_id, game?.view.state?.possession, control])
  useEffect(() => {
    listTeams()
      .then((data) => {
        setTeams(data.teams)
        setCatalogProblems(data.problems || [])
        if (data.teams.length) {
          const sides = initialSides(data.teams)
          setHome(sides.home)
          setAway(sides.away)
        }
      })
      .catch((error) => setError(browser ? error.message : 'The Bowl Bound server is not reachable.'))
  }, [])

  useEffect(() => {
    if (!home.season) { setRules(null); setRulesError(''); return }
    setRules(null)
    setRulesError('')
    let current = true
    getRules(home.season, gameType)
      .then((data) => { if (current) setRules(data) })
      .catch((error) => {
        if (!current) return
        setRules(null)
        setRulesError(error?.message || 'The rules summary could not be loaded.')
      })
    return () => { current = false }
  }, [home.season, gameType, rulesAttempt])

  const persist = async (active, humanSide) => {
    const link = linkedFixture.current
    if (!browser && !link) return
    const identity = saveIdentity.current
    setSaveStatus(null)
    try {
      const checkpoint = await saveGame(active.game_id)
      if (link) {
        const finished = active.view.finished
        const payload = {
          snapshot: link.season.snapshot,
          fixture_id: link.fixture.id,
          game_id: link.gameId,
        }
        const updated = finished ? await recordSeasonResult(active.game_id, payload) : {}
        const saved = await saveSeason({
          ...link.season,
          ...updated,
          games: {
            ...link.season.games,
            [link.fixture.id]: { checkpoint, humanSide, status: finished ? 'final' : 'in_progress', id: link.gameId },
          },
        })
        link.season = saved
        setSaveStatus({ message: finished ? 'Final result recorded.' : 'Game saved locally.' })
        return
      }
      const previous = savedGame.current
      savedGame.current = await writeSavedGame({
        id: identity.id, name: previous?.name ?? identity.name, checkpoint, humanSide,
      }, previous?.version)
      setSaveStatus({ message: 'Game saved locally.' })
    } catch (error) {
      setSaveStatus({ error: true, message: `Game could not be saved locally. ${error.message} ${link ? 'Retry saving before continuing.' : 'Export the game to keep your progress.'}` })
    }
  }
  const apply = async (result) => {
    setOffense('')
    setDefense('')
    setGame((current) => ({
      ...current,
      view: result.view,
      turn: result.turn,
      revision: result.revision ?? current.revision,
    }))
    if (result.report) setReport(result.report)
    else if (["halftime_choice", "overtime_choice", "final"].includes(result.view.phase)) {
      setReport(null)
    }
    await persist({ ...game, view: result.view }, control)
  }
  // All gameplay requests share one synchronous guard, including automatic turns.
  const run = async (work) => {
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true)
    setError('')
    try { return await work() } catch (e) {
      setError(e.message)
      if (game?.turn?.automatic) setComputerError(e.message)
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }
  const manualOrControlled = (fn, ...args) => control === 'manual' ? fn(...args) : fn(...args, control)
  // Start requires a rules response that matches the current selection and
  // reports support, so an unsupported matchup cannot be launched while the
  // summary is still loading or after it failed.
  const currentRules = rules && String(rules.season) === home.season && rules.game_type === gameType ? rules : null
  const rulesReady = Boolean(currentRules?.supported)
  const start = () => run(async () => {
    const payload = { home: home.teamId, away: away.teamId, mode: 'regulation', game_type: gameType, difficulty }
    const created = await (control === 'manual' ? newGame(payload) : newGame(payload, control))
    if (browser) {
      savedGame.current = null
      saveIdentity.current = { id: created.game_id, name: gameName(created) }
      setSaveStatus(null)
    }
    setRevealedToss(null)
    setGame(created)
    setReport(null)
    setHurryMode(false)
    setCompleteHistory(false)
    setOffense('')
    setDefense('')
    setComputerError('')
    automaticCount.current = 0
    await persist(created, control)
  })
  const play = (offensiveCall, defensiveCall) => run(async () => {
    if (linkedFixture.current && saveStatus?.error) return
    setOffense('')
    setDefense('')
    automaticCount.current = 0
    let expectedRevision = game.revision ?? 0
    // Apply a human preference only through a modifier the engine offers to that human.
    const canHurry = control === 'manual' || game.turn?.human_role === 'offense'
    if (canHurry && hurryMode && game.view.clock_modifiers?.some((c) => c.id === 'clock:hurry' && c.enabled)) {
      const hurried = await manualOrControlled(decide, game.game_id, 'clock:hurry')
      await apply(hurried)
      expectedRevision = hurried.revision ?? expectedRevision
    }
    await apply(await (control === 'manual' ? snap(game.game_id, offensiveCall, defensiveCall)
      : coachStep(game.game_id, control, expectedRevision, game.turn.human_role === 'offense' ? offensiveCall : defensiveCall)))
  })
  const special = (action, isGameAction = false) => run(async () => {
    if (linkedFixture.current && saveStatus?.error) return
    automaticCount.current = 0
    await apply(await manualOrControlled(isGameAction ? gameAction : kick, game.game_id, action))
  })
  const choose = (choice) => run(async () => {
    if (linkedFixture.current && saveStatus?.error) return
    automaticCount.current = 0
    await apply(await manualOrControlled(decide, game.game_id, choice))
  })
  useEffect(() => {
    if (saveStatus?.error && linkedFixture.current) return
    if (control === 'manual' || game?.view.review || !game?.turn?.automatic || game.view.finished || busy || error || computerError || (game.view.phase === "opening_choice" && !openingRevealed)) return
    const timer = setTimeout(() => {
      run(async () => {
        if (++automaticCount.current > 12) throw new Error('Computer stopped after 12 consecutive actions. Review the game before retrying.')
        await apply(await coachStep(game.game_id, control, game.revision ?? 0))
      })
    }, 200)
    return () => clearTimeout(timer)
  }, [game, control, busy, error, computerError, openingRevealed, saveStatus?.error])

  const loaded = async (created, humanSide = control, record = null, name = gameName(created)) => {
    if (browser || linkedFixture.current) {
      savedGame.current = record
      saveIdentity.current = { id: record?.id ?? created.game_id, name }
      setControl(humanSide)
      setSaveStatus(null)
    }
    setRevealedToss(null)
    setGame(created)
    if (gameMenu.current) gameMenu.current.open = false
    automaticCount.current = 0
    setReport(null)
    setHurryMode(false)
    setCompleteHistory(false)
    setError('')
    setComputerError('')
    setOffense('')
    setDefense('')
    if (!record && !linkedFixture.current) await persist(created, humanSide)
  }
  const resetGame = () => {
    if (inFlight.current) return
    linkedFixture.current = null
    setSaveStatus(null)
    setGame(null)
    setReport(null)
    setError('')
    setComputerError('')
    setOffense('')
    setDefense('')
    setHurryMode(false)
    setCompleteHistory(false)
  }
  const saveSeason = async (season) => {
    const saved = await writeSavedSeason({ ...season, id: season.snapshot.id }, season.version)
    setSeasonRecords((records) => [saved, ...records.filter((record) => record.id !== saved.id)])
    return saved
  }
  const openSeasons = () => run(async () => {
    const [catalog, records] = await Promise.all([listSeasonTemplates(), listSavedSeasons()])
    const seasons = await Promise.all(records.map(async (record) => ({
      ...record, ...await summarizeSeason(record.snapshot),
    })))
    setSeasonTemplates(catalog.templates)
    setConferences(catalog.conferences)
    setSeasonRecords(seasons)
    setShowSeasons(true)
  })
  const playFixture = (season, fixture, humanSide) => run(async () => {
    const checkpoint = season.games[fixture.id]
    const side = checkpoint?.humanSide ?? humanSide
    const created = checkpoint
      ? await loadGame(checkpoint.checkpoint, side)
      : await newGame({ home: fixture.home, away: fixture.away, mode: 'regulation', difficulty }, side)
    linkedFixture.current = { season, fixture, gameId: checkpoint?.id ?? created.game_id }
    await loaded(created, side)
    if (!checkpoint) await persist(created, side)
  })
  const resetFixture = (season, fixture) => run(async () => {
    const games = { ...season.games }
    delete games[fixture.id]
    const result = season.snapshot.results[fixture.id]
    const updated = result ? await removeSeasonResult({
      snapshot: season.snapshot, fixture_id: fixture.id, game_id: result.game_id,
    }) : {}
    await saveSeason({ ...season, ...updated, games })
  })
  const saves = linkedFixture.current
    ? <button type="button" className="play-button" disabled={busy}
        onClick={() => run(() => persist(game, control))}>Save game</button>
    : browser
    ? <BrowserSaves gameId={game?.game_id} humanSide={control} busy={busy} run={run} onLoaded={loaded}
        save={() => persist(game, control)} activeRecord={savedGame.current}
        name={saveIdentity.current?.name ?? gameName(game)} />
    : <SaveControls gameId={game?.game_id} humanSide={control} busy={busy} onLoaded={loaded}
    onBusyChange={(value) => { inFlight.current = value; setBusy(value) }} onError={setError} />
  const controls = <label className="block text-sm">Control mode
    <select className="block text-black p-1" value={control} disabled={busy || Boolean(game)} onChange={(e) => setControl(e.target.value)}>
      <option value="home">Human home / computer away</option>
      <option value="away">Human away / computer home</option>
      <option value="manual">Two-sided manual play</option>
    </select>
  </label>

  if (!game && showSeasons) {
    return (
      <main className="max-w-6xl mx-auto p-6 text-white space-y-4">
        <button type="button" className="play-button" disabled={busy} onClick={() => setShowSeasons(false)}>Exhibition</button>
        {error && <p role="alert">{error}</p>}
        <SeasonManager
          teams={(teams ?? []).map((team) => ({ ...team, conference: conferences[team.id] }))}
          templates={seasonTemplates}
          seasons={seasonRecords}
          busy={busy}
          onCreate={(payload) => run(async () => saveSeason({ ...await createSeason(payload), games: {} }))}
          onPlay={playFixture}
          onReset={resetFixture}
          onRemoveResult={resetFixture}
        />
      </main>
    )
  }

  if (!game) {
    return (
      <main className="max-w-xl mx-auto p-6 text-white" data-testid="team-select">
        <h1 className="text-3xl font-bold mb-4">Bowl Bound</h1>
        <p className="mb-4 text-sm">Play both sides manually or coach either team against the computer at your chosen difficulty. Simultaneous calls stay hidden until the play resolves.</p>
        <button type="button" className="play-button mb-4" disabled={busy || !teams?.length}
          onClick={openSeasons}>Seasons</button>
        {controls}
        {error && <div className="text-red-300 mb-3" role="alert">{error}</div>}
        {teams && teams.length === 0 && <div role="status">No teams were found in the seasons folder.</div>}
        <CatalogProblems problems={catalogProblems} />
        {teams && teams.length > 0 && (
          <div className="space-y-3">
            <MatchupBuilder
              teams={teams}
              home={home}
              away={away}
              onHomeChange={setHome}
              onAwayChange={setAway}
              onSwap={() => { setHome(away); setAway(home) }}
              onUseSameSeason={() => {
                const options = teams.filter((t) => String(t.season) === home.season)
                const carried = options.find((t) => t.id.split('/')[1] === away.teamId.split('/')[1])
                setAway({ season: home.season, teamId: carried ? carried.id : '' })
              }}
              disabled={busy}
              rules={currentRules}
              rulesError={rulesError}
              onRetryRules={() => setRulesAttempt((attempt) => attempt + 1)}
            >
            <label className="block">Game type
              <select className="block w-full text-black p-1" value={gameType} onChange={(e) => setGameType(e.target.value)}>
                <option value="regular">Regular season</option>
                <option value="postseason">Postseason</option>
              </select>
            </label>
            <label className="block">Difficulty
              <select className="block w-full text-black p-1" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                <option value="easy">Easy (0.3)</option>
                <option value="medium">Medium (0.5)</option>
                <option value="hard">Hard (0.7)</option>
              </select>
            </label>
            <p className="text-sm">Difficulty changes coaching decisions, never dice odds.</p>
            <button type="button" className="play-button text-black" disabled={busy || !home.teamId || !away.teamId || !rulesReady} onClick={start} data-testid="start-game">Start game</button>
            </MatchupBuilder>
          </div>
        )}
        {saves}
      </main>
    )
  }

  const view = game.view
  const turn = control === 'manual' ? null : game.turn
  const canSetHurry = control === 'manual' || !turn || turn.human_role === 'offense'
  const actions = turn?.actions || view.actions
  const pending = turn ? turn.pending : view.pending
  const clockChoice = pending && view.phase === 'clock_choice'
  const blocking = Boolean(view.review) || (Boolean(pending) && !view.clock_optional) || Boolean(turn?.automatic)
  const gameActions = (turn ? turn.game_actions : view.game_actions) || []
  const conditionalTimeouts = gameActions.filter((action) => action.key.startsWith("timeout_after:"))
  const timeoutActions = conditionalTimeouts.length ? conditionalTimeouts : gameActions.filter((action) => action.key.startsWith("timeout:"))
  const boundsActions = gameActions.filter((action) => action.key.startsWith("bounds:"))
  const boundsStatus = view.bounds_declaration === 'out_of_bounds'
    ? 'Out of bounds selected for the next play.'
    : view.bounds_declaration === 'in_bounds'
      ? 'Keep in bounds selected for the next play.'
      : 'No bounds instruction selected.'
  // Display abbreviations only: offered engine IDs and labels still own availability/behavior.
  const displayKeys = {
    punt: 'P', field_goal: 'F', kneel: 'K', kickoff: 'KO',
    onside_kickoff: 'O', hail_mary: 'HM', elect_safety: 'ES',
  }
  const extraPlays = [
    ...(actions.special || []).map((action) => ({ ...action, prefix: 'special', displayKey: displayKeys[action.key], shortLabel: action.key === 'field_goal' ? 'FG' : action.label })),
    ...gameActions.filter((action) => !action.key.startsWith("timeout:") && !action.key.startsWith("timeout_after:") && !action.key.startsWith("bounds:")).map((action) => ({ ...action, prefix: 'game', displayKey: displayKeys[action.key] })),
  ]
  const offensePlays = [...actions.offense, ...(!turn || turn.human_role === 'offense' ? extraPlays : [])]
  const defensePlays = [...actions.defense, ...(turn && turn.human_role !== 'offense' ? extraPlays : [])]
  const selectPlay = (role, key) => {
    if (view.finished || blocking || busy || inFlight.current) return
    const extra = extraPlays.find((action) => action.key === key)
    if (extra) { special(key, extra.prefix === 'game'); return }
    if (!actions[role].some((action) => action.key === key)) return
    const nextOffense = role === 'offense' ? key : offense
    const nextDefense = role === 'defense' ? key : defense
    setOffense(nextOffense)
    setDefense(nextDefense)
    if (turn || (actions.offense.some((action) => action.key === nextOffense)
      && actions.defense.some((action) => action.key === nextDefense))) {
      play(nextOffense, nextDefense)
    }
  }
  const playPanels = (offensePlays.length > 0 || defensePlays.length > 0) && <div className={offensePlays.length && defensePlays.length ? 'grid sm:grid-cols-2 gap-3' : ''}>
    {offensePlays.length > 0 && <PlaySelector title={"OFFENSE — " + (view.state?.possession_name || "")} prefix="offense" actions={offensePlays} selected={offense} onSelect={(key) => selectPlay('offense', key)} disabled={view.finished || blocking || busy} />}
    {defensePlays.length > 0 && <PlaySelector title={"DEFENSE — " + (view.defense_name || "—")} prefix="defense" actions={defensePlays} selected={defense} onSelect={(key) => selectPlay('defense', key)} disabled={view.finished || blocking || busy} />}
  </div>
  return (
    <main className={`${view.phase === "opening_choice" ? "max-w-xl" : "max-w-7xl"} mx-auto p-4 space-y-3 text-white`} data-testid={view.phase === "opening_choice" ? "opening-screen" : "playing-screen"}>
      <header className="flex items-center justify-between gap-3">
        <h1 className="font-bold">Bowl Bound</h1>
        <div className="flex items-center gap-3">
        <ChartViewer key={game.game_id} gameId={game.game_id} initialSide={control === 'away' ? 'away' : 'home'} initialChart={turn?.human_role === 'defense' ? 'defense' : 'offense'} />
        <details ref={gameMenu} className="relative" onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.currentTarget.open = false
            event.currentTarget.querySelector('summary').focus()
          }
        }}>
          <summary className="cursor-pointer text-sm rounded px-3 py-1 bg-gray-800">Game</summary>
          <div className="absolute right-0 top-full mt-2 z-50 w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-gray-500 bg-gray-900 p-3 shadow-xl space-y-3">
            <button type="button" className="play-button text-black" disabled={busy} onClick={resetGame} data-testid="new-drive">{linkedFixture.current ? 'Return to seasons' : 'New game'}</button>
            {saves}
            <div className="text-xs text-gray-400">Seed {game.seed}</div>
          </div>
        </details>
        </div>
      </header>
      {saveStatus && <p role={saveStatus.error ? 'alert' : 'status'} className="text-sm">{saveStatus.message}</p>}
      {saveStatus?.error && linkedFixture.current && <button type="button" className="play-button"
        disabled={busy} onClick={() => run(() => persist(game, control))}>Retry fixture save</button>}
      {(error || computerError) && <div className="text-red-300" role="alert">{error === 'no such game' ? <>
        The local server was restarted, so this unsaved game is no longer available.
        <button type="button" className="play-button ml-2" disabled={busy} onClick={resetGame}>Start new game</button>
      </> : <>{error || computerError}
        {turn?.automatic && !view.finished && <button type="button" className="play-button ml-2" disabled={busy} onClick={() => { automaticCount.current = 0; setComputerError(''); setError('') }}>Retry computer</button>}</>}
      </div>}
      {view.phase === "opening_choice" ? <>
        <p className="text-center font-bold">{view.home} vs {view.away}</p>
        {openingRevealed && <div role="status" className="text-sm" data-testid="session-status">{turn?.status || view.status}</div>}
        <CoinToss pending={pending} winner={view.pending?.chooser} revealed={openingRevealed} rolls={view.toss_dice} onChoose={choose} disabled={busy} />
      </> : view.finished ? <>
        <section aria-labelledby="final-heading" className="space-y-3 rounded-lg bg-slate-800 p-4 text-center">
          <h2 id="final-heading" className="text-xl font-bold">Final</h2>
          <div className="grid grid-cols-2 gap-4">
            <div><p className="font-semibold">{view.home}</p><p className="text-3xl font-bold text-yellow-400" data-testid="home-score">{view.score?.home ?? '—'}</p></div>
            <div><p className="font-semibold">{view.away}</p><p className="text-3xl font-bold text-yellow-400" data-testid="away-score">{view.score?.away ?? '—'}</p></div>
          </div>
          <p role="status" className="text-sm text-slate-300" data-testid="session-status">{turn?.status || view.status}</p>
          <div className="flex flex-wrap justify-center gap-3">
            <button type="button" className="play-button" disabled={busy} onClick={resetGame}>{linkedFixture.current ? 'Return to seasons' : 'New game'}</button>
            {view.log.length > 0 && <button type="button" className="play-button"
              aria-expanded={completeHistory} onClick={() => setCompleteHistory(!completeHistory)}>Show complete history</button>}
          </div>
        </section>
        <TeamStatistics home={view.home} away={view.away} statistics={view.statistics} final />
        <ScoringLedger events={view.scoring} />
        {completeHistory && <GamePlayLog entries={view.log} report={report} complete onClose={() => setCompleteHistory(false)} />}
      </> : <>
      <Scoreboard view={view} />
      <div role="status" className={!view.finished && ["scrimmage", "clock_choice"].includes(view.phase) ? "sr-only" : "text-sm"} data-testid="session-status">{turn?.status || view.status}</div>
      <FootballField state={view.state} home={view.home} away={view.away}
        kickLanding={view.pending?.kick_landing_from_left} />
      {view.review && (view.review.halftime
        ? <HalftimeReview review={view.review} busy={busy} onContinue={() => special(view.review.action.key, true)} />
        : <section role="region" aria-label={view.review.title} className="board-panel p-3 space-y-2">
          <h2 className="font-bold">{view.review.title}</h2>
          {view.review.lines.map((line, i) => <p key={i}>{line}</p>)}
          <button type="button" className="play-button" disabled={busy} onClick={() => special(view.review.action.key, true)}>{view.review.action.label}</button>
        </section>)}
      <div className="grid items-start gap-3 lg:items-stretch lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)_minmax(12rem,3fr)]" data-testid="play-area">
      <div className="order-1 min-w-0 space-y-3 rounded-lg border border-slate-600 bg-slate-800/80 p-3">
        <h2 className="text-sm font-semibold">Play selection</h2>
      <p className="text-xs text-gray-300">{hurryMode ? "Enabled until you turn it off; used only when the engine offers a legal hurry-up snap for your offense." : turn ? "Choose your play to resolve it. Computer calls stay hidden until resolution." : "Choose both calls to resolve the play. Required decisions come first."}</p>
      {turn?.human_role !== 'defense' && (view.toss_dice?.length > 0 || view.overtime_toss_dice?.length > 0) && <details className="text-xs"><summary>Toss dice audit</summary>
        <p>Opening toss</p>{view.toss_dice?.map((roll, i) => <DiceRoll key={`opening-${i}`} roll={roll} />)}
        {view.overtime_toss_dice?.length > 0 && <p>Overtime toss</p>}{view.overtime_toss_dice?.map((roll, i) => <DiceRoll key={`ot-${i}`} roll={roll} />)}
      </details>}
      {!clockChoice && pending && <PenaltyChoices pending={pending} onChoose={choose} disabled={busy} />}
        {view.fourth_down_guidance && <section aria-label="Fourth-down guidance" className="panel">
          <h2 className="font-bold">{view.fourth_down_guidance.label}</h2>
          <p>{view.fourth_down_guidance.summary}</p>
        </section>}
        {playPanels}
      </div>
      <GamePlayLog entries={view.log} report={report} complete={completeHistory} onClose={() => setCompleteHistory(false)} />
      <aside className="order-2 min-w-0 rounded-lg border border-slate-600 bg-slate-800/80 p-3 lg:order-3">
      <section aria-label="Play modifiers" className="play-modifiers space-y-3 text-sm" data-testid="modifier-card">
        <h2 className="text-sm font-semibold">GAME CONTROLS</h2>
        {canSetHurry && <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-slate-600 pt-2">
          <span className="font-bold">Pace</span>
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" checked={hurryMode} disabled={busy} onChange={(e) => setHurryMode(e.target.checked)} />
            Enable/Disable Hurry-Up
          </label>
        </div>}
        {(clockChoice || timeoutActions.length > 0) && <div className="space-y-2 border-t border-slate-600 pt-2">
          <h3 className="font-bold">Clock</h3>
          {clockChoice && view.clock_timing_label && <p className="truncate text-xs text-gray-300" title={view.clock_timing_label}>{view.clock_timing_label}</p>}
          <div className="flex flex-wrap items-center gap-2">
            {clockChoice && <ClockChoices pending={pending} modifiers={turn ? view.clock_modifiers?.filter((c) => pending.choices.some((offered) => offered.id === c.id)) : view.clock_modifiers} onChoose={choose} disabled={busy} />}
            {timeoutActions.map((action) => <button key={action.key} type="button" className="play-button px-2 py-1 text-xs"
              disabled={busy || blocking || view.finished} title={action.label} data-testid={'game-play-' + action.key}
              onClick={() => special(action.key, true)}>{action.label}</button>)}
          </div>
        </div>}
        {view.armed_timeout_label && <p role="status">{view.armed_timeout_label}</p>}
        {boundsActions.length > 0 && <div role="group" aria-label="Next-play result instruction" className="border-t border-slate-600 pt-2">
          <span className="font-bold">Next-play result</span>
          <div className="mt-2 grid grid-cols-2 gap-2" data-testid="bounds-actions">
            {boundsActions.map((action) => {
              const declaration = action.key === 'bounds:oob' ? 'out_of_bounds' : 'in_bounds'
              const rule = view.play_modifiers?.find((choice) => choice.id === action.key)
              const selected = view.bounds_declaration === declaration
              const label = declaration === 'out_of_bounds' ? 'Out of bounds' : 'Keep in bounds'
              return <button key={action.key} type="button" className={`play-button w-full px-2 py-1 text-xs leading-tight ${selected ? 'play-button-selected' : ''}`}
                disabled={busy || blocking || view.finished || rule?.enabled === false}
                aria-pressed={selected}
                title={rule?.reason || action.label} data-testid={'bounds-' + declaration}
                onClick={() => special(action.key, true)}>{label}</button>
            })}
          </div>
          <span className="mt-2 block text-xs text-gray-300" data-testid="bounds-status">{boundsStatus}</span>
        </div>}
        {(report || view.log.length > 0) && <button type="button" className="play-button px-2 py-1 text-xs"
          aria-expanded={completeHistory} onClick={() => setCompleteHistory(!completeHistory)}>Show complete history</button>}
      </section>
      </aside>
      </div>
      <ScoringLedger events={view.scoring} />
      <TeamStatistics home={view.home} away={view.away} statistics={view.statistics} />
      </>}
    </main>
  )
}
