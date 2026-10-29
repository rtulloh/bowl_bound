import { useEffect, useRef } from 'react'

export default function PenaltyChoices({ pending, onChoose, disabled = false }) {
  const panel = useRef(null)
  const choicesKey = pending.choices.map((c) => c.id + ':' + c.enabled).join('|')
  useEffect(() => {
    if (!disabled) panel.current?.querySelector('button:not(:disabled)')?.focus()
  }, [pending.chooser, choicesKey, disabled])
  return (
    <section ref={panel} className="board-panel p-3" aria-label={pending.chooser ? pending.chooser + ': choose' : 'Required decision'} data-testid="penalty-choices">
      <h2 className="font-bold mb-2">{pending.chooser ? pending.chooser + ': choose' : 'Required decision'}</h2>
      <div className="flex flex-wrap gap-3">
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
      </div>
    </section>
  )
}
