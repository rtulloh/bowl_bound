// Labels and values are supplied by the engine, including totals and sack accounting.
export default function TeamStatistics({ home, away, statistics }) {
  if (!statistics?.rows?.length) return null
  return (
    <details className="bg-gray-800 p-3 rounded" data-testid="team-statistics">
      <summary className="cursor-pointer font-bold">Team statistics</summary>
      <table className="w-full text-sm mt-2">
        <thead><tr>
          <th scope="col" className="text-left">Statistic</th>
          <th scope="col">{home}</th>
          <th scope="col">{away}</th>
        </tr></thead>
        <tbody>{statistics.rows.map((row) => (
          <tr key={row.label}>
            <th scope="row" className="text-left font-normal">{row.label}</th>
            <td className="text-center">{row.home}</td>
            <td className="text-center">{row.away}</td>
          </tr>
        ))}</tbody>
      </table>
    </details>
  )
}
