import { useEffect, useState } from 'react'
import { loadGame, saveGame } from '../api'
import { deleteSavedGame, listSavedGames, writeSavedGame } from '../runtime/gameLibrary'
import { decodeGameExport, downloadGame, encodeGameExport } from '../runtime/gameExport'

function SavedGame({ record, busy, run, restore, refresh }) {
  const [name, setName] = useState(record.name)
  return (
    <li className="space-y-1 border-t border-gray-500 pt-2">
      <form className="flex flex-wrap gap-2" onSubmit={(event) => {
        event.preventDefault()
        run(async () => {
          await writeSavedGame({ ...record, name: name.trim() }, record.version)
          await refresh()
        })
      }}>
        <label className="block">Game name
          <input className="block text-black" value={name} onChange={(event) => setName(event.target.value)} maxLength={160} required />
        </label>
        <button className="play-button" type="submit" disabled={busy || !name.trim() || name.trim() === record.name}>Rename</button>
      </form>
      <div className="flex flex-wrap gap-2">
        <button className="play-button" type="button" disabled={busy} onClick={() => run(() => restore(record))}>Resume {record.name}</button>
        <button className="play-button" type="button" onClick={() => run(async () => { downloadGame(encodeGameExport(record)) })}>Export {record.name}</button>
        <button className="play-button" type="button" disabled={busy} onClick={() => run(async () => {
          await deleteSavedGame(record)
          await refresh()
        })}>Delete {record.name}</button>
      </div>
    </li>
  )
}

export default function BrowserSaves({ gameId, humanSide, busy, run, onLoaded, save, activeRecord, name }) {
  const [records, setRecords] = useState([])
  const [libraryError, setLibraryError] = useState('')
  const refresh = async () => {
    try {
      setRecords(await listSavedGames())
      setLibraryError('')
    } catch (error) {
      setLibraryError(error.message)
    }
  }
  useEffect(() => {
    if (!gameId) void refresh()
  }, [gameId])

  const restore = async (record) => {
    const created = await loadGame(record.checkpoint, record.humanSide)
    await onLoaded(created, record.humanSide, record.id ? record : null, record.name)
  }
  const importGame = (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    run(async () => {
      if (file.size > 12 * 1024 * 1024) throw new Error('Browser save file is too large.')
      await restore(decodeGameExport(await file.text(), humanSide))
    })
  }
  return (
    <section aria-label="Save and resume" className="text-sm space-y-2">
      {gameId && <div className="flex flex-wrap gap-2">
        <button className="play-button" type="button" disabled={busy} onClick={() => run(save)}>Save game</button>
        <button className="play-button" type="button" disabled={busy} onClick={() => run(async () => {
          const checkpoint = await saveGame(gameId)
          downloadGame(encodeGameExport({ checkpoint, humanSide, name: activeRecord?.name ?? name }))
        })}>Export game</button>
      </div>}
      {!gameId && <details className="space-y-2">
        <summary className="cursor-pointer">Saved games</summary>
        {libraryError && <p role="alert">Saved games are unavailable. {libraryError}</p>}
        {!libraryError && records.length === 0 && <p>No saved games.</p>}
        <ul className="space-y-2">
          {records.map((record) => <SavedGame key={record.version} record={record} busy={busy} run={run} restore={restore} refresh={refresh} />)}
        </ul>
      </details>}
      <label className="block">Import saved game
        <input type="file" accept=".json,application/json" className="block w-full" disabled={busy} onChange={importGame} />
      </label>
    </section>
  )
}
