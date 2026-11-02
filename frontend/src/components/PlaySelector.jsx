// Adapted from Paydirt's OffensePlays/DefensePlays (MIT, rtulloh): see docs/ATTRIBUTION.md.
// Keys and labels come from the backend; this component holds no play list of its own.
export default function PlaySelector({ title, actions, selected, onSelect, disabled, prefix }) {
  if (!actions.length) return null

  return (
    <div className="board-panel p-2" data-testid={`${prefix}-plays`}>
      <div className="mb-1 bg-panel-bg py-1 text-center text-xs font-bold text-panel-border">{title}</div>
      <div className="grid grid-cols-3 gap-1 lg:grid-cols-4" data-testid={`${prefix}-play-grid`}>
        {actions.map((action) => (
          <button
            key={action.key}
            type="button"
            disabled={disabled}
            title={action.label}
            aria-label={action.shortLabel ? `${action.displayKey || action.key}: ${action.label}` : undefined}
            onClick={() => onSelect(action.key)}
            aria-pressed={selected === action.key}
            className={`play-button flex flex-col items-center px-2 py-0.5 ${selected === action.key ? 'play-button-selected' : ''} ${disabled ? 'cursor-not-allowed' : ''}`}
            data-testid={`${action.prefix || prefix}-play-${action.key.toLowerCase()}`}
          >
            <span className="text-sm font-bold">{action.displayKey || action.key}</span>
            <span className="text-[9px] leading-tight">{action.shortLabel || action.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
