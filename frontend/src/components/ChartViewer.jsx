import { useEffect, useRef, useState } from 'react'
import { getCharts } from '../api'

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
  const [chart, setChart] = useState(['offense', 'defense', 'priority'].includes(initialChart) ? initialChart : 'offense')
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
          {['offense', 'defense', 'priority'].map((key) => <button type="button" key={key} className={`play-button ${chart === key ? 'play-button-selected' : ''}`} aria-pressed={chart === key} onClick={() => setChart(key)}>{key[0].toUpperCase() + key.slice(1)}</button>)}
        </div>
      </div>
    </div>
    {error ? <div role="alert">{error} <button type="button" className="play-button" onClick={() => setRetry((value) => value + 1)}>Retry charts</button></div> : !book ? <p role="status">Loading charts…</p> : <>
      <div className="chart-reference-bar">
        <p className="chart-note">{priority ? reference.note : book.note}</p>
        <div className="chart-launchers">
          <a href={detachedUrl} target="_blank" rel="noopener noreferrer" onClick={() => onClose?.()}>Open in new tab</a>
          <button type="button" onClick={openWindow}>Open in separate window</button>
        </div>
      </div>
      {launchError && <p role="alert" className="chart-launch-error">{launchError}</p>}
      {chart === 'defense' && <p className="chart-formations">{book.formations?.map((formation) => formation.label).join('  /  ')}</p>}
      <ChartGrid table={table} team={priority ? null : book.team} />
      <details key={chart} className="chart-key">
        <summary>{priority ? 'How to read Priority' : 'How to read the charts'}</summary>
        {!priority && <div className="chart-colors">{book.legend.map((entry) => <span key={entry.color}><span className={`chart-swatch chart-cell-${entry.color}`} aria-hidden="true" />{entry.label}</span>)}</div>}
        <div className="chart-legend">
          {(priority ? reference.legend : [...book.legend, ...book.symbols]).map((entry) => <p key={entry.label}><strong>{entry.label}:</strong> {entry.description}</p>)}
          {priority && reference.notes.map((note) => <p className="chart-rule-note" key={note}>{note}</p>)}
        </div>
      </details>
    </>}
  </div>
}

function ChartGrid({ table, team }) {
  return <div className="chart-scroll" role="region" aria-label={`${table.title} chart grid`} tabIndex={0}>
    <table className="chart-grid">
      <caption>{team ? `${table.title} · ${team}` : table.title}</caption>
      <thead><tr>
        <th scope="col">{table.roll_label}</th>
        {table.columns.map((column) => <th scope="col" key={column.key}>{column.label}</th>)}
      </tr></thead>
      <tbody>{table.rows.map((row) => <tr key={row.label}>
        <th scope="row" title={row.description}>
          {row.label}<span className="sr-only"> — {row.description}</span>
        </th>
        {row.cells.map((cell, index) =>
          <td key={table.columns[index].key} className={`chart-cell-${cell.color}`} title={cell.description}>
            <span>{cell.label}</span><span className="sr-only"> — {cell.description}</span>
          </td>)}
      </tr>)}</tbody>
    </table>
  </div>
}
