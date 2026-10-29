import { useEffect, useId, useRef } from 'react'

// Presentation only: labels, availability and default-continuation safety are engine-owned.
export default function ClockChoices({ pending, modifiers, optional = false, onChoose, disabled = false, hurryMode = false }) {
  const id = useId()
  const continuation = useRef(null)
  const choicesKey = pending.choices.map((c) => c.id + ":" + c.enabled).join("|")
  useEffect(() => {
    if (!optional && !disabled) continuation.current?.focus()
  }, [optional, disabled, choicesKey])
  const options = modifiers?.length ? modifiers : pending.choices
  const hurry = hurryMode && pending.choices.some((c) => c.id === "clock:hurry" && c.enabled)
  return (
    <section className="contents" aria-label="Clock controls" data-testid="clock-controls">
      <fieldset disabled={disabled} className="contents text-sm">
        <legend className="sr-only">{pending.chooser && pending.chooser + ": "}Clock modifiers for this play</legend>
        {options.map((option) => (
          <label key={option.id} className="inline-flex items-center gap-1" title={[pending.choices.find((c) => c.id === option.id)?.label, option.reason].filter(Boolean).join(" — ")}>
            <input type="radio" name={id} value={option.id} aria-label={option.label}
              checked={option.id === 'clock:runoff'} disabled={disabled || !option.enabled}
              aria-describedby={option.reason ? `${id}-${option.id}` : undefined}
              onChange={() => { if (!disabled && option.enabled && option.id !== 'clock:runoff') onChoose(option.id) }} />
            {option.label}
            {option.reason && <span id={`${id}-${option.id}`} className="sr-only">{option.reason}</span>}
          </label>
        ))}
        {!optional && <button ref={continuation} type="button" className="play-button text-black text-sm"
          disabled={disabled || !options.find((o) => o.id === 'clock:runoff')?.enabled}
          onClick={() => onChoose(hurry ? 'clock:hurry' : 'clock:runoff')} data-testid="clock-continue">{hurry ? "Continue with hurry-up" : "Continue"}</button>}
      </fieldset>
    </section>
  )
}
