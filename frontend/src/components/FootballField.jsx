// Adapted from Paydirt's FootballField (MIT, rtulloh): see docs/ATTRIBUTION.md.
// This component only draws. Every coordinate comes from the engine; it does no football math.
const END_ZONE = 8.4
const YARD = 0.84
const toPct = (fromLeft) => END_ZONE + fromLeft * YARD

export default function FootballField({ state, home, away }) {
  if (!state) return <div className="board-panel p-4 text-center" data-testid="football-field-empty">Drive complete</div>
  const attackingRight = state.attacking === 'right'
  const ballStyle = {
    left: `${toPct(state.ball_from_left)}%`,
    transform: attackingRight ? 'translateX(calc(-100% + 2px))' : 'scaleX(-1)',
    transition: 'left 0.6s ease-out',
  }
  return (
    <div
      className="relative w-full h-48 rounded-lg overflow-hidden shadow-xl border-2 border-white bg-green-700"
      data-testid="football-field"
    >
      <div className="absolute left-0 top-0 bottom-0 flex items-center justify-center bg-red-900" style={{ width: `${END_ZONE}%` }}>
        <span className="text-white text-xs font-bold" style={{ writingMode: 'vertical-rl' }}>{home}</span>
      </div>
      <div className="absolute right-0 top-0 bottom-0 flex items-center justify-center bg-blue-900" style={{ width: `${END_ZONE}%` }}>
        <span className="text-white text-xs font-bold" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>{away}</span>
      </div>
      {[10, 20, 30, 40, 50, 60, 70, 80, 90].map((yard) => (
        <div key={yard} className="absolute top-0 bottom-0" style={{ left: `${toPct(yard)}%` }}>
          <div className="w-0.5 h-full bg-white" />
        </div>
      ))}
      <div className="absolute z-20 top-0 bottom-0" style={{ left: `${toPct(state.first_down_from_left)}%` }} data-testid="first-down-marker">
        <div className="absolute left-1/2 -translate-x-1/2 top-2 w-1 h-full bg-yellow-400 rounded-full" />
      </div>
      <div className="absolute top-1/2 -translate-y-1/2 z-30" style={ballStyle} data-testid="ball-marker">
        <svg viewBox="0 0 40 24" className="w-10 h-6">
          <ellipse cx="20" cy="12" rx="18" ry="10" fill="#8B4513" />
          <ellipse cx="20" cy="12" rx="16" ry="8" fill="#A0522D" />
          <path d="M8 12 L32 12" stroke="white" strokeWidth="1.5" />
        </svg>
      </div>
    </div>
  )
}
