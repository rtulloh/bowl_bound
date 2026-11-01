const HIGHLIGHT_PRESENTATION = {
  interception_pending: ['Interception decision', 'border-red-800 bg-red-100 text-red-900'],
  interception: ['Interception', 'border-red-800 bg-red-100 text-red-900'],
  fumble: ['Fumble', 'border-red-800 bg-red-100 text-red-900'],
  touchdown: ['Touchdown', 'border-green-800 bg-green-100 text-green-900'],
  conversion: ['Conversion', 'border-green-800 bg-green-100 text-green-900'],
  breakaway: ['Breakaway roll', 'border-amber-800 bg-amber-100 text-amber-900'],
  touchback: ['Touchback', 'border-amber-800 bg-amber-100 text-amber-900'],
}

export default function PlayHighlights({ report }) {
  const highlights = (report.highlights ?? [])
    .map((tag) => HIGHLIGHT_PRESENTATION[tag])
    .filter(Boolean)
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
