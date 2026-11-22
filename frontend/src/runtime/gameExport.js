const FORMAT = 'bowl-bound-browser-game'
const CONTROLS = new Set(['home', 'away', 'manual'])
const MAX_CHECKPOINT_BYTES = 2 * 1024 * 1024

export function encodeGameExport({ checkpoint, humanSide, name }) {
  return JSON.stringify({ format: FORMAT, version: 1, checkpoint, humanSide, name })
}

export function decodeGameExport(text, humanSide) {
  let parsed
  try { parsed = JSON.parse(text) } catch { /* The engine reports invalid checkpoint data. */ }
  if (parsed?.format !== FORMAT) {
    if (new Blob([text]).size > MAX_CHECKPOINT_BYTES) throw new Error('Save exceeds the 2 MiB limit.')
    return { checkpoint: text, humanSide }
  }
  if (parsed.version !== 1 || !CONTROLS.has(parsed.humanSide) || typeof parsed.name !== 'string'
    || !parsed.name.trim() || parsed.name.length > 160 || typeof parsed.checkpoint !== 'string') {
    throw new Error('Invalid Bowl Bound browser save format or version.')
  }
  if (new Blob([parsed.checkpoint]).size > MAX_CHECKPOINT_BYTES) throw new Error('Save exceeds the 2 MiB limit.')
  return { checkpoint: parsed.checkpoint, humanSide: parsed.humanSide, name: parsed.name }
}

export function downloadGame(text) {
  const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }))
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
}
