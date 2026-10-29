import { useRef } from 'react'
import { loadGame, saveGame } from '../api'

// Saves are opaque engine documents. Never infer a phase or execute a pending choice.
export default function SaveControls({ gameId, busy = false, onLoaded, onBusyChange, onError }) {
  const inFlight = useRef(false)
  const perform = async (work) => {
    if (busy || inFlight.current) return
    inFlight.current = true
    onBusyChange(true)
    onError('')
    try { await work() } catch (error) { onError(error.message) } finally {
      inFlight.current = false
      onBusyChange(false)
    }
  }
  const save = () => perform(async () => {
    const data = await saveGame(gameId)
    const url = URL.createObjectURL(new Blob([data], { type: 'application/json' }))
    const link = document.createElement('a')
    try {
      link.href = url
      link.download = 'bowl-bound-save.json'
      document.body.appendChild(link)
      link.click()
    } finally {
      link.remove()
      URL.revokeObjectURL(url)
    }
  })
  const load = (event) => {
    const file = event.target.files?.[0]
    event.target.value = '' // Allow retrying the same file after a failed upload.
    if (!file) return
    perform(async () => {
      if (file.size > 2 * 1024 * 1024) throw new Error('Save exceeds the 2 MiB limit.')
      await onLoaded(await loadGame(await file.text()))
    })
  }
  return (
    <section aria-label="Save and resume" className="text-sm space-y-2">
      <div className="flex flex-wrap gap-3 items-center">
        {gameId && <button type="button" className="play-button text-black" disabled={busy} onClick={save}>Save game</button>}
        <label className="min-w-0 w-full">Load saved game
          <input type="file" accept=".json,application/json" className="block w-full min-w-0 max-w-full" disabled={busy} onChange={load} />
        </label>
      </div>
      <p className="text-xs text-gray-400">Saves are private. Keep the matching local teams installed. Loading creates a separate game.</p>
    </section>
  )
}
