// Displays committed engine awards; totals and scoring rules stay in the engine.
export default function ScoringLedger({ events = [] }) {
  if (!events.length) return null
  return (
    <section className="board-panel p-3 text-black text-sm" data-testid="scoring-ledger">
      <h2 className="font-bold">Scoring</h2>
      <ol>
        {events.map((event) => (
          <li key={event.number} data-testid="scoring-event">
            Play {event.play_number}: {event.team} — {event.kind} ({event.points})
          </li>
        ))}
      </ol>
    </section>
  )
}
