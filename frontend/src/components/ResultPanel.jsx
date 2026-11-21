// Shows the engine's own description and trace; it never interprets chart values.
import DiceRoll from './DiceRoll'
import PlayHighlights from './PlayHighlights'

const traceLabels = new Map([
  ['offense', 'OFF'], ['defense', 'DEF'], ['kickoff', 'KO'],
  ['kickoff_return', 'RT'], ['punt_return', 'RT'], ['punt', 'PUNT'],
  ['field_goal', 'FG'], ['pat', 'PAT'], ['interception_return', 'INT RT'],
  ['supplemental:B', 'B'], ['supplemental:QR', 'QR'], ['supplemental:QT', 'QT'],
])

export default function ResultPanel({ report, embedded = false, logEntry = false }) {
  if (!report) return <div className="board-panel p-2 text-sm" data-testid="result-empty">Follow the next-action guidance above.</div>
  return (
    <div className={embedded ? 'min-w-0 p-2' : 'board-panel max-h-44 min-w-0 overflow-y-auto p-2'} data-testid={logEntry ? undefined : 'result-panel'}>
      <div className="min-w-0 [overflow-wrap:anywhere] text-sm font-bold" role={logEntry ? undefined : 'status'} aria-atomic={logEntry ? undefined : true} data-testid={logEntry ? undefined : 'result-description'}>{report.commentary ?? report.description}</div>
      <PlayHighlights report={report} />
      {report.timing_label && <p className="text-xs mt-1">{report.timing_label}</p>}
      {!report.supported && (
        <div className="mt-1 text-xs font-bold text-red-800" data-testid="unsupported-notice">
          Not yet supported: {report.unsupported_reason}. The play was not applied and the situation is unchanged.
        </div>
      )}
      <p className="mt-1 text-xs">
        Offense: {report.called_play}{report.defense && report.defense !== 'No formation' && ` · Defense: ${report.defense}`}
      </p>
      {report.called_play !== report.resolved_play && (
        <div className="mt-1 text-xs" data-testid="resolved-play">Called {report.called_play}; resolved as {report.resolved_play}.</div>
      )}
      <ul className="my-2 flex flex-wrap gap-4" aria-label={logEntry ? 'Recorded dice' : 'Observed play dice'} data-testid={logEntry ? undefined : 'trace'}>
        {report.trace.map((entry, i) => (
          <li key={i} className="text-xs">
            <div>{traceLabels.get(entry.section) ?? entry.section}</div>
            <DiceRoll roll={entry.roll} showTotal={false} />
          </li>
        ))}
      </ul>
      {report.trace.length > 0 && <p className="text-xs font-mono">
        ({report.trace.map(({ section, roll, cell }) => `${traceLabels.get(section) ?? section}:${roll.total}→"${cell}"`).join(' | ')})
      </p>}
    </div>
  )
}
