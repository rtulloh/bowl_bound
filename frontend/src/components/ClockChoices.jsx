import { useId } from 'react'

// Presentation only: labels and availability are engine-owned; normal timing is implicit.
export default function ClockChoices({ pending, modifiers, onChoose, disabled = false }) {
  const id = useId()
  const options = modifiers ?? pending.choices
  if (!options.length) return null
  return (
    <section className="contents" aria-label="Clock controls" data-testid="clock-controls">
      <fieldset disabled={disabled} className="contents text-sm">
        <legend className="sr-only">{pending.chooser && pending.chooser + ": "}Clock modifiers for this play</legend>
        {options.map((option) => (
          <label key={option.id} className="inline-flex items-center gap-1" title={[pending.choices.find((c) => c.id === option.id)?.label, option.reason].filter(Boolean).join(" — ")}>
            <input type="radio" name={id} value={option.id} aria-label={option.label}
              disabled={disabled || !option.enabled}
              aria-describedby={option.reason ? `${id}-${option.id}` : undefined}
              onChange={() => { if (!disabled && option.enabled) onChoose(option.id) }} />
            {option.label}
            {option.reason && <span id={`${id}-${option.id}`} className="sr-only">{option.reason}</span>}
          </label>
        ))}
      </fieldset>
    </section>
  )
}
