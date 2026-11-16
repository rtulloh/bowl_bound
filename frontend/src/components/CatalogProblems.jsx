import { useMemo } from 'react'

/**
 * Surface team folders that could not be read, grouped by season.
 *
 * Renders independently of the matchup builder so diagnostics remain visible
 * when every discovered team is unreadable.
 */
export default function CatalogProblems({ problems = [] }) {
  const bySeason = useMemo(() => {
    const grouped = new Map()
    for (const problem of problems) {
      const [season, slug] = String(problem.id || '').split('/')
      if (!season) continue
      if (!grouped.has(season)) grouped.set(season, [])
      grouped.get(season).push({ slug: slug || problem.id, reason: problem.reason })
    }
    return [...grouped.entries()].sort((a, b) => String(b[0]).localeCompare(String(a[0])))
  }, [problems])

  if (!problems.length) return null

  return (
    <details className="rounded border border-yellow-700 bg-yellow-950/30 p-3 text-sm" data-testid="catalog-problems">
      <summary className="cursor-pointer font-bold">Unavailable teams ({problems.length})</summary>
      <p className="mt-1">These team folders could not be read. They are not selectable.</p>
      <ul className="mt-2 space-y-1">
        {bySeason.map(([season, entries]) => (
          <li key={season}>
            <span className="font-bold">{season}</span>
            <ul className="ml-4 list-disc">
              {entries.map((entry) => (
                <li key={`${season}/${entry.slug}`}>
                  {entry.slug}: {entry.reason}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </details>
  )
}
