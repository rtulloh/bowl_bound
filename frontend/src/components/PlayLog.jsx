// Displays recorded engine context and observed traces without reinterpreting results.
import PlayHighlights from './PlayHighlights'

export default function PlayLog({ entries }) {
  if (!entries.length) return null
  return (
    <ol className="board-panel min-w-0 break-words p-2 text-xs max-h-64 overflow-y-auto space-y-3" data-testid="play-log">
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
  )
}
