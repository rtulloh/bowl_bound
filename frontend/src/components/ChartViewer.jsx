import { useEffect, useRef, useState } from 'react'
import { getCharts } from '../api'

export default function ChartViewer({ gameId, home, away, initialSide = 'home', initialChart = 'offense' }) {
  const [open, setOpen] = useState(false)
  const trigger = useRef(null)
  return <>
    <button ref={trigger} type="button" className="play-button" onClick={() => setOpen(true)}>Charts</button>
    {open && <ChartDialog gameId={gameId} home={home} away={away} initialSide={initialSide} initialChart={initialChart} onClose={() => { setOpen(false); trigger.current?.focus() }} />}
  </>
}

function ChartDialog({ gameId, home, away, initialSide, initialChart, onClose }) {
  const dialog = useRef(null)
  const [side, setSide] = useState(initialSide)
  const [chart, setChart] = useState(initialChart)
  const [book, setBook] = useState(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const element = dialog.current
    element.showModal()
    return () => element.close()
  }, [])
  useEffect(() => {
    let current = true
    setBook(null)
    setError('')
    getCharts(gameId, side)
      .then((data) => { if (current) setBook(data) })
      .catch((failure) => { if (current) setError(failure.message) })
    return () => { current = false }
  }, [gameId, side, retry])
  const dismiss = () => {
    dialog.current.close()
    onClose()
  }
  const table = book?.[chart]
  return <dialog ref={dialog} className="chart-dialog" aria-labelledby="charts-title" onCancel={(event) => { event.preventDefault(); dismiss() }}>
    <div className="chart-book">
      <header className="chart-toolbar">
        <div><p className="chart-eyebrow">TEAM CHARTS</p><h2 id="charts-title">{book ? `${book.season} ${book.team}` : 'Team charts'}</h2></div>
        <button type="button" className="play-button" autoFocus onClick={dismiss}>Close charts</button>
      </header>
      <div className="chart-toolbar">
        <label>Chart team
          <select value={side} onChange={(event) => setSide(event.target.value)}>
            <option value="home">{home} (home)</option>
            <option value="away">{away} (away)</option>
          </select>
        </label>
        <div className="flex gap-2" role="group" aria-label="Chart type">
          {['offense', 'defense'].map((key) => <button type="button" key={key} className={`play-button ${chart === key ? 'play-button-selected' : ''}`} aria-pressed={chart === key} onClick={() => setChart(key)}>{key === 'offense' ? 'Offense' : 'Defense'}</button>)}
        </div>
      </div>
      {error ? <div role="alert">{error} <button type="button" className="play-button" onClick={() => setRetry((value) => value + 1)}>Retry charts</button></div> : !book ? <p role="status">Loading charts…</p> : <>
        <p className="chart-note">{book.note}</p>
        <div className="chart-colors" aria-label="Chart colors">{book.legend.map((entry) => <span key={entry.color} title={entry.description}><span className={`chart-swatch chart-cell-${entry.color}`} aria-hidden="true" />{entry.label}</span>)}</div>
        {chart === 'defense' && <p className="chart-note">{book.formations?.map((formation) => formation.label).join('  /  ')}</p>}
        <div className="chart-scroll" role="region" aria-label={`${table.title} chart grid`} tabIndex={0}>
          <table className="chart-grid">
            <caption>{table.title} · {book.team}</caption>
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
        <details className="chart-key" open><summary>How to read the charts</summary><div className="chart-legend">
          {book.legend.map((entry) => <p key={entry.color}><strong>{entry.label}:</strong> {entry.description}</p>)}
          {book.symbols.map((entry) => <p key={entry.label}><strong>{entry.label}:</strong> {entry.description}</p>)}
        </div></details>
      </>}
    </div>
  </dialog>
}
