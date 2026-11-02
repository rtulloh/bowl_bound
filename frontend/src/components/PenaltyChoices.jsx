import { useEffect, useRef } from 'react'

function RazzleDazzleChoices({ choices, disabled, onChoose }) {
  const columns = [...new Set(choices.map((choice) => choice.presentation_column))]
  const rows = [...new Set(choices.map((choice) => choice.presentation_row))]
  const cells = new Map(choices.map((choice) => [`${choice.presentation_row}:${choice.presentation_column}`, choice]))
  return <>
    <p className="mb-2 text-sm">Choose one result. Each row is a play; each column is one rolled total.</p>
    <div role="grid" aria-label="Razzle-Dazzle choices" className="grid items-center gap-2"
      style={{ gridTemplateColumns: `minmax(5rem, auto) repeat(${columns.length}, minmax(0, 1fr))` }}>
      <div role="columnheader" className="font-bold">Play</div>
      {columns.map((column) => <div key={column} role="columnheader" className="text-center font-bold">{column}</div>)}
      {rows.flatMap((row) => [
        <div key={row} role="rowheader" className="font-bold">{row}</div>,
        ...columns.map((column) => {
          const choice = cells.get(`${row}:${column}`)
          if (!choice) return <div key={`${row}:${column}`} role="gridcell" className="text-center">—</div>
          return <div key={choice.id} role="gridcell">
            <button type="button" className="play-button w-full" disabled={disabled || !choice.enabled}
              onClick={() => onChoose(choice.id)} data-testid={'penalty-choice-' + choice.id}
              aria-label={choice.label} aria-describedby={choice.reason ? 'reason-' + choice.id : undefined}>
              {choice.presentation_value}
            </button>
            {choice.reason && <div id={'reason-' + choice.id} className="text-xs text-gray-700 mt-1" data-testid={'penalty-choice-' + choice.id + '-reason'}>{choice.reason}</div>}
          </div>
        }),
      ])}
    </div>
  </>
}

export default function PenaltyChoices({ pending, onChoose, disabled = false }) {
  const panel = useRef(null)
  const choicesKey = pending.choices.map((c) => c.id + ':' + c.enabled).join('|')
  useEffect(() => {
    if (!disabled) panel.current?.querySelector('button:not(:disabled)')?.focus()
  }, [pending.chooser, choicesKey, disabled])
  const razzleDazzle = pending.choices.length > 0 && pending.choices.every((choice) => choice.presentation === 'razzle_dazzle')
  return (
    <section ref={panel} className="board-panel p-3" aria-label={pending.chooser ? pending.chooser + ': choose' : 'Required decision'} data-testid="penalty-choices">
      <h2 className="font-bold mb-2">{pending.chooser ? pending.chooser + (razzleDazzle ? ': choose a Razzle-Dazzle result' : ': choose') : 'Required decision'}</h2>
      {razzleDazzle ? <RazzleDazzleChoices choices={pending.choices} disabled={disabled} onChoose={onChoose} /> : <div className="flex flex-wrap gap-3">
        {pending.choices.map((choice) => (
          <div key={choice.id}>
            <button type="button" className="play-button" disabled={disabled || !choice.enabled}
              onClick={() => onChoose(choice.id)} data-testid={'penalty-choice-' + choice.id}
              aria-describedby={choice.reason ? 'reason-' + choice.id : undefined}>
              {choice.label}
            </button>
            {choice.reason && <div id={'reason-' + choice.id} className="text-xs text-gray-700 mt-1" data-testid={'penalty-choice-' + choice.id + '-reason'}>{choice.reason}</div>}
          </div>
        ))}
      </div>}
    </section>
  )
}
