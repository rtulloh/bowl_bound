// Shows the engine's own description and trace; it never interprets chart values.
import DiceRoll from './DiceRoll'
import PlayHighlights from './PlayHighlights'
export default function ResultPanel({ report }) {
  if (!report) return <div className="board-panel p-3 text-sm" data-testid="result-empty">Follow the next-action guidance above.</div>
  return (
    <div className="board-panel min-w-0 p-3" data-testid="result-panel">
      <div className="text-sm font-bold break-words" role="status" aria-atomic="true" data-testid="result-description">{report.commentary ?? report.description}</div>
      <PlayHighlights report={report} />
      {!report.supported && (
        <div className="mt-1 text-xs font-bold text-red-800" data-testid="unsupported-notice">
          Not yet supported: {report.unsupported_reason}. The play was not applied and the situation is unchanged.
        </div>
      )}
      {report.called_play !== report.resolved_play && (
        <div className="mt-1 text-xs" data-testid="resolved-play">Called {report.called_play}; resolved as {report.resolved_play}.</div>
      )}
      <div className="my-2 flex flex-wrap gap-4" aria-label="Observed play dice">
        {report.trace.map((entry, i) => <div key={i} className="text-xs"><div>{entry.section}</div><DiceRoll roll={entry.roll} /></div>)}
      </div>
      <details className="mt-2"><summary className="cursor-pointer text-sm">Detailed dice and chart audit</summary>
      <ul className="mt-2 text-xs font-mono" data-testid="trace">
        {report.trace.map((entry, i) => (
          <li key={i}>
            {entry.section}: {entry.team} {entry.play}{entry.formation ? ` / ${entry.formation}` : ''} - dice {entry.roll.faces.join('+')} = {entry.roll.total}, cell {entry.cell || '(blank)'}
          </li>
        ))}
      </ul></details>
    </div>
  )
}
