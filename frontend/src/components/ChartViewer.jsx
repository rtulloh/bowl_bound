import { useEffect, useRef, useState } from 'react'
import { getCharts } from '../api'

const CHART_TYPES = [['offense', 'Offense'], ['defense', 'Defense'], ['special_teams', 'Special Teams'], ['priority', 'Priority']]

export default function ChartViewer({ gameId, initialSide = 'home', initialChart = 'offense' }) {
  const [open, setOpen] = useState(false)
  const trigger = useRef(null)
  return <>
    <button ref={trigger} type="button" className="play-button" onClick={() => setOpen(true)}>Charts</button>
    {open && <ChartDialog gameId={gameId} initialSide={initialSide} initialChart={initialChart} onClose={() => { setOpen(false); trigger.current?.focus() }} />}
  </>
}

function ChartDialog({ onClose, ...props }) {
  const dialog = useRef(null)
  useEffect(() => {
    const element = dialog.current
    element.showModal()
    return () => element.close()
  }, [])
  const dismiss = () => {
    dialog.current.close()
    onClose()
  }
  return <dialog ref={dialog} className="chart-dialog" aria-labelledby="charts-title" onCancel={(event) => { event.preventDefault(); dismiss() }}>
    <ChartPanel {...props} onClose={dismiss} />
  </dialog>
}

export function DetachedCharts({ gameId, initialSide = 'home', initialChart = 'offense' }) {
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(gameId || '')) {
    return <main className="detached-charts chart-book"><p role="alert">This chart link is invalid. Open charts from your active game.</p></main>
  }
  return <main className="detached-charts" data-testid="detached-charts">
    <ChartPanel gameId={gameId} initialSide={initialSide} initialChart={initialChart} />
  </main>
}

function chartUrl(gameId, side, chart) {
  const url = new URL(window.location.href)
  url.search = ''
  url.hash = ''
  url.searchParams.set('charts', gameId)
  url.searchParams.set('side', side)
  url.searchParams.set('view', chart)
  return url.href
}

function ChartPanel({ gameId, initialSide, initialChart, onClose }) {
  const [side, setSide] = useState(initialSide === 'away' ? 'away' : 'home')
  const [chart, setChart] = useState(CHART_TYPES.some(([key]) => key === initialChart) ? initialChart : 'offense')
  const [books, setBooks] = useState(null)
  const [error, setError] = useState('')
  const [launchError, setLaunchError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let current = true
    setBooks(null)
    setError('')
    Promise.all([getCharts(gameId, 'home'), getCharts(gameId, 'away')])
      .then(([home, away]) => { if (current) setBooks({ home, away }) })
      .catch((failure) => {
        if (current) setError(failure.message === 'no such game'
          ? 'This game is no longer available. Open charts from your active game.'
          : 'Charts could not be loaded. Check that the game is still running and retry.')
      })
    return () => { current = false }
  }, [gameId, retry])
  const book = books?.[side]
  const priority = chart === 'priority'
  const reference = book?.priority
  const table = priority ? reference?.table : book?.[chart]
  const legend = table?.legend?.length ? table.legend : book?.legend
  const symbols = table?.symbols?.length ? table.symbols : book?.symbols
  const detachedUrl = chartUrl(gameId, side, chart)
  const openWindow = () => {
    setLaunchError('')
    let child
    try {
      // Isolate the empty same-origin window before loading any application script.
      child = window.open('about:blank', '_blank', 'popup=yes,width=1400,height=1000,resizable=yes,scrollbars=yes')
      if (!child) {
        setLaunchError('The separate window could not open. Use Open in new tab or allow windows for this game.')
        return
      }
      child.opener = null
      child.location.replace(detachedUrl)
      onClose?.()
    } catch {
      child?.close()
      setLaunchError('The separate window could not open. Use Open in new tab.')
    }
  }
  return <div className="chart-book">
    <div className="chart-topbar">
      <header className="chart-identity">
        <p className="chart-eyebrow">{priority ? 'SHARED REFERENCE' : 'TEAM CHARTS'}</p>
        <h2 id="charts-title">{priority ? 'Priority chart' : book ? `${book.season} ${book.team}` : 'Team charts'}</h2>
      </header>
      {onClose && <button type="button" className="play-button chart-close" autoFocus onClick={onClose}>Close charts</button>}
      <div className="chart-controls">
        {books && !priority && <label>Chart team
          <select value={side} onChange={(event) => setSide(event.target.value)}>
            <option value="home">{books.home.team} (home)</option>
            <option value="away">{books.away.team} (away)</option>
          </select>
        </label>}
        <div className="chart-tabs" role="group" aria-label="Chart type">
          {CHART_TYPES.map(([key, label]) => <button type="button" key={key} className={`play-button ${chart === key ? 'play-button-selected' : ''}`} aria-pressed={chart === key} onClick={() => setChart(key)}>{label}</button>)}
        </div>
      </div>
    </div>
    {error ? <div role="alert">{error} <button type="button" className="play-button" onClick={() => setRetry((value) => value + 1)}>Retry charts</button></div> : !book ? <p role="status">Loading charts…</p> : <>
      <div className="chart-reference-bar">
        <p className="chart-note">{priority ? reference.note : book.note}</p>
        <div className="chart-launchers">
          <a className="play-button" href={detachedUrl} target="_blank" rel="noopener noreferrer" onClick={() => onClose?.()}>Open in new tab</a>
          <button type="button" className="play-button" onClick={openWindow}>Open in separate window</button>
        </div>
      </div>
      {launchError && <p role="alert" className="chart-launch-error">{launchError}</p>}
      {chart === 'defense' && <p className="chart-formations">{book.formations?.map((formation) => formation.label).join('  /  ')}</p>}
      <ChartTables table={table} team={priority ? null : book.team} />
      <details key={chart} className="chart-key">
        <summary>{priority ? 'How to read Priority' : 'How to read the charts'}</summary>
        {!priority && <div className="chart-colors">{legend.map((entry) => <span key={entry.color}><span className={`chart-swatch chart-cell-${entry.color}`} aria-hidden="true" />{entry.label}</span>)}</div>}
        <div className="chart-legend">
          {chart === 'defense' && <p className="chart-rule-note">For generated teams, formation tradeoffs are experimental Bowl Bound estimates, separate from measured team strength. The source does not identify historical defensive formations.</p>}
          {(priority ? reference.legend : [...legend, ...symbols]).map((entry) => <p key={entry.label}><strong>{entry.label}:</strong> {entry.description}</p>)}
          {priority && reference.notes.map((note) => <p className="chart-rule-note" key={note}>{note}</p>)}
        </div>
      </details>
    </>}
  </div>
}

function ChartTables({ table, team }) {
  const groups = table.column_groups || []
  const separate = groups.filter((group) => group.separate)
  if (!separate.length) return <ChartGrid table={table} team={team} groups={groups} />
  return <div className="chart-offense-layout">
    <ChartGrid table={table} team={team} groups={groups.filter((group) => !group.separate)} />
    {separate.map((group) => <ChartGrid key={group.key} table={table} team={team} groups={[group]} title={group.label} />)}
  </div>
}

function ChartGrid({ table, team, groups = [], title = table.title }) {
  const columns = groups.length ? groups.flatMap((group) => table.columns.slice(group.start, group.start + group.count)) : table.columns
  const sections = table.row_groups?.length ? table.row_groups : [{ key: table.key, start: 0, count: table.rows.length }]
  const grouped = Boolean(table.row_groups?.length)
  const rowClass = table.key === 'priority' ? 'chart-row-label' : 'chart-die'
  const edges = new Set()
  let end = 0
  groups.forEach((group) => { end += group.count; edges.add(end - 1) })
  const headings = (span = 1) => <>
    {grouped && <th scope="col" rowSpan={span} className="chart-formation-heading">{table.group_label}</th>}
    <th scope="col" rowSpan={span} className={rowClass} aria-label={table.roll_description || table.roll_label}>{table.roll_label}</th>
  </>
  return <div className="chart-scroll" role="region" aria-label={`${title} chart grid`} tabIndex={0}>
    <table className="chart-grid" data-chart={table.key} data-section={groups.some((group) => group.separate) ? 'supplemental' : 'main'}>
      <caption>{team ? `${title} · ${team}` : title}</caption>
      <thead>
        {groups.length > 0 && <tr className="chart-bands">{headings(2)}{groups.map((group) => <th scope="colgroup" colSpan={group.count} key={group.key} className="chart-group-end">{group.label}</th>)}</tr>}
        <tr className="chart-play-headings">
          {!groups.length && headings()}
          {columns.map((column, i) => <th scope="col" key={column.key} className={edges.has(i) ? 'chart-group-end' : ''} aria-label={column.label}>
            {column.number ? <><span className="chart-play-number">{column.number}</span><span className="chart-play-name">{column.name}</span></> : column.label}
          </th>)}
        </tr>
      </thead>
      {sections.map((section) => <tbody key={section.key} data-formation={grouped ? section.key : undefined}>
        {table.rows.slice(section.start, section.start + section.count).map((row, rowIndex) => {
          const cells = groups.length ? groups.flatMap((group) => row.cells.slice(group.start, group.start + group.count)) : row.cells
          return <tr key={row.label}>
            {grouped && rowIndex === 0 && <th scope="rowgroup" rowSpan={section.count} className="chart-formation"><span className="chart-formation-letter">{section.key}</span><span className="chart-formation-name">{section.label}</span></th>}
            <th scope="row" className={rowClass} title={row.description}>
              <span className={table.key === 'priority' ? '' : 'chart-die-face'}>{row.dice_label || row.label}</span><span className="sr-only"> — {row.description}</span>
            </th>
            {cells.map((cell, index) => <td key={columns[index].key} className={`chart-cell-${cell.color} ${edges.has(index) ? 'chart-group-end' : ''}`} title={cell.description}>
              <span>{cell.label}</span><span className="sr-only"> — {cell.description}</span>
            </td>)}
          </tr>
        })}
      </tbody>)}
    </table>
  </div>
}
