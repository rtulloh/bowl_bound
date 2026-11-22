let runtime
let queue = Promise.resolve()

async function initialize(location) {
  const manifestUrl = new URL(location)
  const runtimeUrl = new URL('pyodide/', manifestUrl)
  const { loadPyodide } = await import(/* @vite-ignore */ new URL('pyodide.mjs', runtimeUrl).href)
  const pyodide = await loadPyodide({ indexURL: runtimeUrl.href })

  const manifestResponse = await fetch(manifestUrl)
  if (!manifestResponse.ok) throw new Error('Could not download the browser game manifest.')
  const manifest = await manifestResponse.json()
  const archive = manifest.files?.[0]
  if (manifest.version !== 1 || manifest.files?.length !== 1 ||
      archive?.url !== 'python.zip' || archive.mount !== '/app' ||
      !/^[a-f0-9]{64}$/.test(archive.sha256)) {
    throw new Error('Invalid browser game manifest.')
  }
  const response = await fetch(new URL(archive.url, manifestUrl))
  if (!response.ok) throw new Error('Could not download the browser game engine.')
  const bytes = await response.arrayBuffer()
  const hash = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))
  const digest = Array.from(hash, byte => byte.toString(16).padStart(2, '0')).join('')
  if (digest !== archive.sha256 || bytes.byteLength !== archive.bytes) {
    throw new Error('The browser engine archive failed verification.')
  }

  await pyodide.loadPackage(['pydantic', 'pyyaml'])
  pyodide.unpackArchive(bytes, 'zip', { extractDir: '/app' })
  await pyodide.runPythonAsync(`
import sys
from pathlib import Path
sys.path.insert(0, '/app')
from backend.browser_bridge import BrowserBridge
_browser_bridge = BrowserBridge(Path('/app/seasons'))
`)
  return pyodide
}

self.addEventListener('message', ({ data }) => {
  queue = queue.then(async () => {
    try {
      runtime ??= initialize(data.manifestUrl)
      const pyodide = await runtime
      pyodide.globals.set('_browser_method', data.method)
      pyodide.globals.set('_browser_path', data.path)
      pyodide.globals.set('_browser_body', data.body)
      const raw = pyodide.runPython('_browser_bridge.request(_browser_method, _browser_path, _browser_body)')
      self.postMessage({ id: data.id, result: JSON.parse(raw) })
    } catch (error) {
      self.postMessage({ id: data.id, error: `Could not run the browser game: ${error.message}` })
    }
  })
})
