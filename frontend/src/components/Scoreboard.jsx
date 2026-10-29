// Adapted from Paydirt's Scoreboard (MIT, rtulloh): see docs/ATTRIBUTION.md.
// Shows only engine-provided text, including the score.
export default function Scoreboard({ view }) {
  const state = view.state
  const score = view.score || { home: 0, away: 0 }
  return (
    <div className="px-6 py-3 bg-gray-800" data-testid="scoreboard">
      <div className="flex flex-wrap gap-4 items-center justify-between max-w-4xl mx-auto text-center">
        <div>
          <div className="text-xs text-gray-500">HOME</div>
          <div className="text-lg font-bold text-white" data-testid="home-name">{view.home}</div>
          <div className="text-2xl font-bold text-yellow-400" data-testid="home-score">{score.home}</div>
          {view.clock && <div className="text-xs text-gray-300" data-testid="home-timeouts">Timeouts: {view.clock.timeouts[0]}</div>}
        </div>
        {view.clock && <div aria-label="Game time">
          <div className="text-sm text-gray-300" data-testid="quarter">{view.clock.quarter_label}</div>
          <div className="text-2xl font-mono font-bold text-white" data-testid="game-clock">{view.clock.label}</div>
        </div>}
        <div>
          <div className="text-xs text-gray-500">DOWN &amp; DISTANCE</div>
          <div className="text-lg font-bold text-white" data-testid="situation">{state ? state.situation : view.status}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">BALL ON</div>
          <div className="text-lg font-bold text-yellow-400" data-testid="spot">{state ? state.spot : '-'}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">POSSESSION</div>
          <div className="text-lg font-bold text-yellow-400" data-testid="possession">{state ? state.possession_name : '-'}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">AWAY</div>
          <div className="text-lg font-bold text-white" data-testid="away-name">{view.away}</div>
          <div className="text-2xl font-bold text-yellow-400" data-testid="away-score">{score.away}</div>
          {view.clock && <div className="text-xs text-gray-300" data-testid="away-timeouts">Timeouts: {view.clock.timeouts[1]}</div>}
        </div>
      </div>
    </div>
  )
}
