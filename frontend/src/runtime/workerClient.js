export function createWorkerClient(worker, manifestUrl) {
  const pending = new Map()
  let nextId = 0
  let failure

  function stop() {
    failure = new Error('The browser engine stopped responding. Reload to recover your last saved checkpoint.')
    worker.terminate()
    for (const { reject, timer } of pending.values()) {
      clearTimeout(timer)
      reject(failure)
    }
    pending.clear()
  }

  worker.addEventListener('error', stop)
  worker.addEventListener('messageerror', stop)
  worker.addEventListener('message', ({ data }) => {
    const entry = pending.get(data.id)
    if (!entry) return
    clearTimeout(entry.timer)
    pending.delete(data.id)
    if (data.error) entry.reject(new Error(data.error))
    else entry.resolve(data.result)
  })

  return (method, path, body = null) => new Promise((resolve, reject) => {
    if (failure) {
      reject(failure)
      return
    }
    const id = ++nextId
    pending.set(id, { resolve, reject, timer: setTimeout(stop, 90_000) })
    try {
      worker.postMessage({ id, manifestUrl, method, path, body })
    } catch {
      stop()
    }
  })
}
