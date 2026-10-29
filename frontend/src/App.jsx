import { useEffect, useRef, useState } from 'react'
import { coachStep, decide, gameAction, getGame, kick, listTeams, newGame, snap } from './api'
import FootballField from './components/FootballField'
import PlayLog from './components/PlayLog'
import PlaySelector from './components/PlaySelector'
import ResultPanel from './components/ResultPanel'
import Scoreboard from './components/Scoreboard'
import PenaltyChoices from './components/PenaltyChoices'
import ScoringLedger from './components/ScoringLedger'
import ClockChoices from './components/ClockChoices'
import TeamStatistics from './components/TeamStatistics'
import SaveControls from './components/SaveControls'
import CoinToss from './components/CoinToss'
import DiceRoll from './components/DiceRoll'

export default function App() {
  const [teams, setTeams] = useState(null)
  const [home, setHome] = useState('')
  const [away, setAway] = useState('')
  const [gameType, setGameType] = useState('regular')
  const [difficulty, setDifficulty] = useState('medium')
  const [game, setGame] = useState(null)
  const [offense, setOffense] = useState('')
  const [defense, setDefense] = useState('')
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const [computerError, setComputerError] = useState('')
  const [busy, setBusy] = useState(false)
  const [hurryMode, setHurryMode] = useState(false)
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
        if (data.teams.length) {
          const sampleHome = data.teams.find((t) => t.id === "2007/cedar-valley")
          const sampleAway = data.teams.find((t) => t.id === "2007/harbor-tech")
          setHome((sampleHome || data.teams[0]).id)
          setAway((sampleAway || data.teams[data.teams.length > 1 ? 1 : 0]).id)
        }
      })
      .catch(() => setError('The Bowl Bound server is not reachable.'))
  }, [])

  const apply = (result) => {
    setOffense('')
    setDefense('')
    setGame((current) => ({ ...current, view: result.view, turn: result.turn }))
    if (result.report) setReport(result.report)
  }
  // All gameplay requests share one synchronous guard, including automatic turns.
  const run = async (work) => {
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true)
    setError('')
    try { await work() } catch (e) {
      setError(e.message)
      if (game?.turn?.automatic) setComputerError(e.message)
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }
  const manualOrControlled = (fn, ...args) => control === 'manual' ? fn(...args) : fn(...args, control)
  const start = () => run(async () => {
    const payload = { home, away, mode: 'regulation', game_type: gameType, difficulty }
    const created = await (control === 'manual' ? newGame(payload) : newGame(payload, control))
    setRevealedToss(null)
    setGame(created)
    setReport(null)
    setHurryMode(false)
    setOffense('')
    setDefense('')
    setComputerError('')
    automaticCount.current = 0
  })
  const play = (offensiveCall, defensiveCall) => run(async () => {
    setOffense('')
    setDefense('')
    automaticCount.current = 0
    // Apply a human preference only through a modifier the engine offers to that human.
    const canHurry = control === 'manual' || game.turn?.human_role === 'offense'
    if (canHurry && hurryMode && game.view.clock_modifiers?.some((c) => c.id === 'clock:hurry' && c.enabled)) {
      apply(await manualOrControlled(decide, game.game_id, 'clock:hurry'))
    }
    apply(await (control === 'manual' ? snap(game.game_id, offensiveCall, defensiveCall)
      : coachStep(game.game_id, control, game.turn.human_role === 'offense' ? offensiveCall : defensiveCall)))
  })
  const special = (action, isGameAction = false) => run(async () => {
    automaticCount.current = 0
    apply(await manualOrControlled(isGameAction ? gameAction : kick, game.game_id, action))
  })
  const choose = (choice) => run(async () => {
    automaticCount.current = 0
    apply(await manualOrControlled(decide, game.game_id, choice))
  })
  useEffect(() => {
    if (control === 'manual' || !game?.turn?.automatic || game.view.finished || busy || error || computerError || (game.view.phase === "opening_choice" && !openingRevealed)) return
    const timer = setTimeout(() => {
      run(async () => {
        if (++automaticCount.current > 12) throw new Error('Computer stopped after 12 consecutive actions. Review the game before retrying.')
        apply(await coachStep(game.game_id, control))
      })
    }, 200)
    return () => clearTimeout(timer)
  }, [game, control, busy, error, computerError, openingRevealed])

  const loaded = async (created) => {
    // Apply the explicitly chosen browser mode before replacing the visible game.
    const prepared = control === 'manual' ? created : await getGame(created.game_id, control)
    setRevealedToss(null)
    setGame(prepared)
    if (gameMenu.current) gameMenu.current.open = false
    automaticCount.current = 0
    setReport(null)
    setHurryMode(false)
    setError('')
    setComputerError('')
    setOffense('')
    setDefense('')
  }
  const saves = <SaveControls gameId={game?.game_id} busy={busy} onLoaded={loaded}
    onBusyChange={(value) => { inFlight.current = value; setBusy(value) }} onError={setError} />
  const controls = <label className="block text-sm">Control mode
    <select className="block text-black p-1" value={control} disabled={busy} onChange={(e) => setControl(e.target.value)}>
      <option value="home">Human home / computer away</option>
      <option value="away">Human away / computer home</option>
      <option value="manual">Two-sided manual play</option>
    </select>
  </label>

  if (!game) {
    return (
      <main className="max-w-xl mx-auto p-6 text-white" data-testid="team-select">
        <h1 className="text-3xl font-bold mb-4">Bowl Bound</h1>
        <p className="mb-4 text-sm">Play both sides manually or coach either team against the computer at your chosen difficulty. Simultaneous calls stay hidden until the play resolves.</p>
        {controls}
        {error && <div className="text-red-300 mb-3" role="alert">{error}</div>}
        {teams && teams.length === 0 && <div role="status">No teams were found in the seasons folder.</div>}
        {teams && teams.length > 0 && (
          <div className="space-y-3">
            <label className="block">Home
              <select className="block w-full text-black p-1" value={home} onChange={(e) => setHome(e.target.value)} data-testid="home-select">
                {teams.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.season})</option>)}
              </select>
            </label>
            <label className="block">Away
              <select className="block w-full text-black p-1" value={away} onChange={(e) => setAway(e.target.value)} data-testid="away-select">
                {teams.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.season})</option>)}
              </select>
            </label>
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
            <button type="button" className="play-button text-black" disabled={busy} onClick={start} data-testid="start-game">Start game</button>
          </div>
        )}
        {saves}
      </main>
    )
  }

  const view = game.view
  const turn = control === 'manual' ? null : game.turn
  const actions = turn?.actions || view.actions
  const pending = turn ? turn.pending : view.pending
  const clockChoice = pending && view.phase === 'clock_choice'
  const blocking = (Boolean(pending) && !view.clock_optional) || Boolean(turn?.automatic)
  const gameActions = (turn ? turn.game_actions : view.game_actions) || []
  const timeoutActions = gameActions.filter((action) => action.key.startsWith("timeout:"))
  // Display abbreviations only: offered engine IDs and labels still own availability/behavior.
  const displayKeys = { punt: 'P', field_goal: 'F', kneel: 'K', kickoff: 'KO', hail_mary: 'HM', 'timeout:home': 'TO', 'timeout:away': 'TO' }
  const extraPlays = [
    ...(actions.special || []).map((action) => ({ ...action, prefix: 'special', displayKey: displayKeys[action.key], shortLabel: action.key === 'field_goal' ? 'FG' : action.label })),
    ...gameActions.filter((action) => !action.key.startsWith("timeout:")).map((action) => ({ ...action, prefix: 'game', displayKey: displayKeys[action.key] })),
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
    {defensePlays.length > 0 && <PlaySelector title={"DEFENSE — " + (view.state?.possession === "home" ? view.away : view.home)} prefix="defense" actions={defensePlays} selected={defense} onSelect={(key) => selectPlay('defense', key)} disabled={view.finished || blocking || busy} />}
  </div>
  return (
    <main className={`${view.phase === "opening_choice" ? "max-w-xl" : "max-w-4xl"} mx-auto p-4 space-y-3 text-white`} data-testid={view.phase === "opening_choice" ? "opening-screen" : "playing-screen"}>
      <header className="flex items-center justify-between gap-3">
        <h1 className="font-bold">Bowl Bound</h1>
        <details ref={gameMenu} className="relative" onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.currentTarget.open = false
            event.currentTarget.querySelector('summary').focus()
          }
        }}>
          <summary className="cursor-pointer text-sm rounded px-3 py-1 bg-gray-800">Game</summary>
          <div className="absolute right-0 top-full mt-2 z-50 w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-gray-500 bg-gray-900 p-3 shadow-xl space-y-3">
            <button type="button" className="play-button text-black" disabled={busy} onClick={() => { setGame(null); setReport(null); setError(''); setComputerError(''); setOffense(''); setDefense(''); setHurryMode(false) }} data-testid="new-drive">New game</button>
            {saves}
            <div className="text-xs text-gray-400">Seed {game.seed}</div>
          </div>
        </details>
      </header>
      {(error || computerError) && <div className="text-red-300" role="alert">{error || computerError}
        {turn?.automatic && !view.finished && <button type="button" className="play-button ml-2" disabled={busy} onClick={() => { automaticCount.current = 0; setComputerError(''); setError('') }}>Retry computer</button>}
      </div>}
      {view.phase === "opening_choice" ? <>
        <p className="text-center font-bold">{view.home} vs {view.away}</p>
        {openingRevealed && <div role="status" className="text-sm" data-testid="session-status">{turn?.status || view.status}</div>}
        <CoinToss pending={pending} winner={view.pending?.chooser} revealed={openingRevealed} rolls={view.toss_dice} onChoose={choose} disabled={busy} />
      </> : <>
      <Scoreboard view={view} />
      <div role="status" className={!view.finished && ["scrimmage", "clock_choice"].includes(view.phase) ? "sr-only" : "text-sm"} data-testid="session-status">{turn?.status || view.status}</div>
      {view.phase === "kickoff" && playPanels}
      <FootballField state={view.state} home={view.home} away={view.away} />
      <ResultPanel report={report} />
      <section aria-label="Play modifiers" className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" checked={hurryMode} disabled={busy} onChange={(e) => setHurryMode(e.target.checked)} />
          Hurry-up mode
        </label>
        {clockChoice && <ClockChoices pending={pending} modifiers={turn ? view.clock_modifiers?.filter((c) => pending.choices.some((offered) => offered.id === c.id)) : view.clock_modifiers} optional={view.clock_optional} hurryMode={hurryMode} onChoose={choose} disabled={busy} />}
        {!clockChoice && <>
          {timeoutActions.map((action) => <button key={action.key} type="button" className="play-button"
            disabled={busy || blocking || view.finished} title={action.label} data-testid={'game-play-' + action.key}
            onClick={() => special(action.key, true)}>{action.label}</button>)}
          {!timeoutActions.length && <button type="button" className="play-button" disabled title="Available when the engine offers a timeout after an eligible play.">Timeout</button>}
          <button type="button" className="play-button" disabled title="Available when the engine offers a spike after an eligible play.">Spike</button>
        </>}
        <button type="button" className="play-button" disabled title="Per-play out-of-bounds declaration; engine support is not implemented yet.">OOB</button>
        <button type="button" className="play-button" disabled title="Per-play in-bounds declaration; engine support is not implemented yet.">IB</button>
      </section>
      <p className="text-xs text-gray-300">{hurryMode ? "Enabled until you turn it off; used only when the engine offers a legal hurry-up snap for your offense." : turn ? "Choose your play to resolve it. Computer calls stay hidden until resolution." : "Choose both calls to resolve the play. Required decisions come first."}</p>
      {(view.toss_dice?.length > 0 || view.overtime_toss_dice?.length > 0) && <details className="text-xs"><summary>Toss dice audit</summary>
        <p>Opening toss</p>{view.toss_dice?.map((roll, i) => <DiceRoll key={`opening-${i}`} roll={roll} />)}
        {view.overtime_toss_dice?.length > 0 && <p>Overtime toss</p>}{view.overtime_toss_dice?.map((roll, i) => <DiceRoll key={`ot-${i}`} roll={roll} />)}
      </details>}
      {!clockChoice && pending && <PenaltyChoices pending={pending} onChoose={choose} disabled={busy} />}
      {view.phase !== "kickoff" && playPanels}
      <ScoringLedger events={view.scoring} />
      <TeamStatistics home={view.home} away={view.away} statistics={view.statistics} />
      <PlayLog entries={view.log} />
      </>}
    </main>
  )
}
