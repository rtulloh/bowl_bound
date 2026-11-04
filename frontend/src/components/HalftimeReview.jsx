// The engine supplies scores, period breakdown, statistics and the lead/tie summary.
export default function HalftimeReview({ review, busy = false, onContinue }) {
  const recap = review.halftime
  return (
    <section role="region" aria-label={review.title} className="board-panel p-6 sm:p-8 space-y-6 text-center" data-testid="halftime-review">
      <header className="space-y-6">
        <h2 className="text-3xl font-bold text-gray-800">{review.title}</h2>
        <p className="text-base text-gray-600">End of 2nd Quarter</p>
        <div className="flex justify-center items-center gap-6">
          <div className="min-w-0 flex-1 max-w-64">
            <div aria-hidden="true" data-testid="halftime-team-badge" className="w-14 h-14 mx-auto mb-2 rounded-full flex items-center justify-center bg-gray-600 text-white text-lg font-bold">HM</div>
            <p className="font-bold text-gray-800 break-words">{recap.home.name}</p>
            <p className="text-3xl font-bold text-gray-700 mt-1 tabular-nums" data-testid="halftime-home-score">{recap.home.total}</p>
          </div>
          <span className="text-xl text-gray-400 font-bold" aria-hidden="true">–</span>
          <div className="min-w-0 flex-1 max-w-64">
            <div aria-hidden="true" data-testid="halftime-team-badge" className="w-14 h-14 mx-auto mb-2 rounded-full flex items-center justify-center bg-gray-600 text-white text-lg font-bold">AW</div>
            <p className="font-bold text-gray-800 break-words">{recap.away.name}</p>
            <p className="text-3xl font-bold text-gray-700 mt-1 tabular-nums" data-testid="halftime-away-score">{recap.away.total}</p>
          </div>
        </div>
        <p className="text-base text-gray-600">{recap.summary}</p>
        {recap.result && <p className="font-semibold">{recap.result}</p>}
      </header>

      <button type="button" className="play-button text-base px-6 py-3" disabled={busy} onClick={onContinue}>{review.action.label}</button>

      <details className="text-left text-sm">
        <summary className="cursor-pointer text-gray-700">First-half details</summary>
        <div className="mt-4 space-y-6">
          <div className="overflow-x-auto">
            <table aria-label="First-half score" className="w-full text-sm tabular-nums">
              <thead className="border-b-2 border-gray-500"><tr>
                <th scope="col" className="text-left py-2 pr-3">TEAM</th>
                <th scope="col" className="px-2">Q1</th>
                <th scope="col" className="px-2">Q2</th>
                <th scope="col" className="px-2">TOTAL</th>
              </tr></thead>
              <tbody>{[recap.away, recap.home].map((team, i) => <tr key={i} className="border-b border-gray-400">
                <th scope="row" className="text-left py-2 pr-3 break-words">{team.name}</th>
                <td className="text-center px-2">{team.first}</td>
                <td className="text-center px-2">{team.second}</td>
                <td className="text-center px-2 font-bold">{team.total}</td>
              </tr>)}</tbody>
            </table>
          </div>

          <section className="space-y-2">
            <h3 className="font-bold border-b-2 border-gray-500 pb-2">SCORING SUMMARY</h3>
            <ul className="space-y-1 text-sm">{recap.scoring.map((line, i) => <li key={i}>{line}</li>)}</ul>
          </section>

          <section className="space-y-2">
            <h3 className="font-bold border-b-2 border-gray-500 pb-2">TEAM STATISTICS</h3>
            <div className="overflow-x-auto">
              <table aria-label="First-half team statistics" className="w-full text-sm tabular-nums">
                <thead className="border-b border-gray-400"><tr>
                  <th scope="col" className="text-left py-2 pr-3">Statistic</th>
                  <th scope="col" className="px-2 break-words">{recap.away.name}</th>
                  <th scope="col" className="px-2 break-words">{recap.home.name}</th>
                </tr></thead>
                <tbody>{recap.statistics.map((row) => <tr key={row.label} className="border-b border-gray-300">
                  <th scope="row" className="text-left font-normal py-1 pr-3">{row.label}</th>
                  <td className="text-center px-2">{row.away}</td>
                  <td className="text-center px-2">{row.home}</td>
                </tr>)}</tbody>
              </table>
            </div>
          </section>

          <p>{recap.kickoff}</p>
        </div>
      </details>
    </section>
  )
}
