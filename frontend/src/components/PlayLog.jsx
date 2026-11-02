// Displays recorded engine context and observed traces without reinterpreting results.
import { useEffect, useRef, useState } from 'react'
import PlayHighlights from './PlayHighlights'

export default function PlayLog({ entries, expanded: controlledExpanded, onExpandedChange }) {
  const [localExpanded, setLocalExpanded] = useState(true)
  const logRef = useRef(null)
  const latestEntryNumber = entries[entries.length - 1]?.number
  const expanded = controlledExpanded ?? localExpanded
  const setExpanded = (value) => {
    setLocalExpanded(value)
    onExpandedChange?.(value)
  }

  useEffect(() => {
    if (expanded && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [expanded, latestEntryNumber])

  if (!entries.length) return null
  return (
    <details className="min-w-0" data-testid="play-history" open={expanded} onToggle={(event) => setExpanded(event.currentTarget.open)}>
      <summary className="cursor-pointer py-1 text-sm font-semibold text-slate-100">Play history</summary>
      <ol ref={logRef} className="board-panel mt-1 min-w-0 break-words p-2 text-xs max-h-64 overflow-y-auto space-y-3" data-testid="play-log">
        {entries.map((entry) => (
          <li key={entry.number} data-testid="log-entry">
            <div>{entry.number}. {entry.commentary ?? entry.description}</div>
            <PlayHighlights report={entry} />
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
    </details>
  )
}
