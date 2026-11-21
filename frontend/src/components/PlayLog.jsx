// Displays recorded engine context and observed traces without reinterpreting results.
import { useEffect, useRef, useState } from 'react'
import PlayHighlights from './PlayHighlights'
import ResultPanel from './ResultPanel'

export function GamePlayLog({ entries, report, complete, onClose }) {
  const log = useRef(null)
  const latestPlay = useRef(null)
  const hasPlay = Boolean(report || entries.length)
  const latest = entries.at(-1)
  const current = report && (report.number == null || !latest || report.number >= latest.number) ? report : latest
  const matchesLatest = current === latest || (latest && current &&
    (current.number != null ? current.number === latest.number : current.description === latest.description))
  const earlier = matchesLatest ? entries.slice(0, -1) : [...entries]
  const plays = current ? [matchesLatest ? { ...latest, ...current } : current, ...earlier.reverse()] : []
  const latestNumber = latest?.number

  useEffect(() => {
    if (log.current) log.current.scrollTop = 0
  }, [latestNumber, report, complete])

  useEffect(() => {
    const panel = log.current
    const entry = latestPlay.current
    if (!hasPlay || complete || !panel || !entry || typeof ResizeObserver === 'undefined') return
    const fitLatestPlay = () => {
      const border = panel.offsetHeight - panel.clientHeight
      panel.style.setProperty('--latest-play-height', `${entry.offsetHeight + border}px`)
    }
    fitLatestPlay()
    const observer = new ResizeObserver(fitLatestPlay)
    observer.observe(entry, { box: 'border-box' })
    return () => observer.disconnect()
  }, [hasPlay, complete])
  return (
    <section aria-label="Latest play" className={complete
      ? 'fixed inset-y-0 right-0 z-40 flex w-full max-w-xl flex-col bg-slate-900 p-3 shadow-xl'
      : 'order-3 min-w-0 rounded-lg border border-slate-600 bg-slate-800/80 p-3 lg:order-2'}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">Play log</h2>
        {complete && <button type="button" className="play-button" onClick={onClose}>Close history</button>}
      </div>
      {plays.length ? (
        <div ref={log} tabIndex={0} role="region" aria-label="Play history entries" data-testid="play-log"
          className={`board-panel overflow-y-auto overscroll-contain ${complete ? 'min-h-0 flex-1' : 'h-[min(var(--latest-play-height,12rem),clamp(12rem,calc(100dvh-24rem),30rem))] min-h-24 max-h-[80dvh] resize-y'}`}>
          <ol className="divide-y divide-amber-900/30">
            {plays.map((play, index) => (
              <li ref={index === 0 ? latestPlay : undefined} key={index === 0 ? 'latest' : play.number} data-testid={play.pending ? undefined : "log-entry"}>
                <ResultPanel report={play} logEntry={index > 0} embedded />
                <div className="space-y-1 px-2 pb-2 text-xs">
                  {play.announcements?.map((line, i) => <p key={i} className="font-semibold">{line}</p>)}
                  {play.state_before && <p>Before: {play.state_before.possession_name} · {play.state_before.situation} at {play.state_before.spot}</p>}
                  {play.yards != null && <p>Recorded yardage: {play.yards}</p>}
                  {play.state_after && <p>After: {play.state_after.possession_name} · {play.state_after.situation} at {play.state_after.spot}</p>}
                </div>
              </li>
            ))}
          </ol>
        </div>
      ) : <ResultPanel report={null} />}
    </section>
  )
}

export default function PlayLog({ entries, expanded: controlledExpanded, onExpandedChange }) {
  const [localExpanded, setLocalExpanded] = useState(true)
  const [complete, setComplete] = useState(false)
  const [newEntries, setNewEntries] = useState(false)
  const followLatest = useRef(true)
  const logRef = useRef(null)
  const latestEntryNumber = entries[entries.length - 1]?.number
  const expanded = controlledExpanded ?? localExpanded
  const setExpanded = (value) => {
    setLocalExpanded(value)
    onExpandedChange?.(value)
  }

  useEffect(() => {
    if (!expanded || complete || !logRef.current) return
    if (followLatest.current) logRef.current.scrollTop = logRef.current.scrollHeight
    else setNewEntries(true)
  }, [expanded, complete, latestEntryNumber])

  const scrolled = () => {
    if (complete || !logRef.current) return
    const { scrollHeight, scrollTop, clientHeight } = logRef.current
    followLatest.current = scrollHeight - scrollTop - clientHeight <= 8
    if (followLatest.current) setNewEntries(false)
  }
  const showLatest = () => {
    followLatest.current = true
    setNewEntries(false)
    logRef.current.scrollTop = logRef.current.scrollHeight
    logRef.current.focus()
  }

  if (!entries.length) return null
  return (
    <details className="min-w-0" data-testid="play-history" open={expanded} onToggle={(event) => setExpanded(event.currentTarget.open)}>
      <summary className="cursor-pointer py-1 text-sm font-semibold text-slate-100">
        Play history
      </summary>
      <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
        <span>{entries.length} recorded plays</span>
        <button type="button" className="play-button" aria-pressed={complete} onClick={() => setComplete(!complete)}>
          {complete ? 'Use compact history' : 'Show complete history'}
        </button>
        {!complete && newEntries && <button type="button" className="play-button" onClick={showLatest}>Show latest plays</button>}
      </div>
      <div ref={logRef} role="region" aria-label="Play history entries" tabIndex={0} onScroll={scrolled}
        className={`board-panel mt-1 min-w-0 break-words p-2 text-xs ${complete ? '' : 'max-h-64 overflow-y-auto'}`} data-testid="play-log">
      <ol className="space-y-3">
        {entries.map((entry) => (
          <li key={entry.number} className="min-w-0" data-testid="log-entry">
            <div className="min-w-0 break-all">{entry.number}. {entry.commentary ?? entry.description}</div>
            {entry.announcements?.map((line, i) => <p key={i} className="font-semibold">{line}</p>)}
            <PlayHighlights report={entry} />
            {entry.timing_label && <p>{entry.timing_label}</p>}
            {entry.state_before && <p>Before: {entry.state_before.possession_name} — {entry.state_before.situation} at {entry.state_before.spot}</p>}
            {entry.state_after && <p>After: {entry.state_after.possession_name} — {entry.state_after.situation} at {entry.state_after.spot}</p>}
            {entry.yards != null && <p>Recorded yardage: {entry.yards}</p>}
            {entry.trace?.length > 0 && <p aria-label="Recorded dice" className="font-mono break-words">
              {entry.trace.map((step, i) => <span key={i}>
                {i > 0 ? ' · ' : ''}{step.section}: [{step.roll.faces.join(', ')}] → {step.roll.total}
              </span>)}
            </p>}
            {entry.trace?.length > 0 && <details>
              <summary className="cursor-pointer">Dice and chart audit</summary>
              <ul className="font-mono">
                {entry.trace.map((step, i) => <li key={i}>
                  {step.section}: {step.team} {step.play}{step.formation ? ` / ${step.formation}` : ''} — dice {step.roll.faces.join('+')} = {step.roll.total}, cell {step.cell || '(blank)'}
                </li>)}
              </ul>
            </details>}
          </li>
        ))}
      </ol>
      </div>
    </details>
  )
}
