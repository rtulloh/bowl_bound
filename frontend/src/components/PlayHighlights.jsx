// Visual emphasis for existing engine outcomes, statistics and recorded procedures only.
export default function PlayHighlights({ report }) {
  if (!report.supported) return null
  const highlights = []
  const sections = (report.trace || []).map((step) => step.section)
  const turnover = 'border-red-800 bg-red-100 text-red-900'
  const score = 'border-green-800 bg-green-100 text-green-900'
  const notable = 'border-amber-800 bg-amber-100 text-amber-900'
  if (report.outcome === 'interception_pending') {
    highlights.push(['Interception decision', turnover])
  } else if (report.statistics?.kind === 'interception') {
    highlights.push(['Interception', turnover])
  }
  if (sections.includes('fumble_recovery')) highlights.push(['Fumble', turnover])
  if (['touchdown', 'offensive_touchdown', 'defensive_touchdown'].includes(report.outcome)) {
    highlights.push([report.timing?.conversion ? 'Conversion' : 'Touchdown', score])
  }
  if (sections.includes('supplemental:B')) highlights.push(['Breakaway roll', notable])
  if (report.outcome === 'touchback') highlights.push(['Touchback', notable])
  if (!highlights.length) return null
  return (
    <div aria-label="Play highlights" className="my-2 flex flex-wrap gap-2">
      {highlights.map(([label, colors]) => <span key={label}
        className={`rounded border-2 px-2 py-1 text-sm font-extrabold uppercase ${colors}`}>
        {label}
      </span>)}
    </div>
  )
}
