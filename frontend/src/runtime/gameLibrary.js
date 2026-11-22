const STORE = 'games'

function openLibrary() {
  return new Promise((resolve, reject) => {
    const request = globalThis.indexedDB.open('bowl-bound-game-library', 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: 'id' })
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function transaction(mode, operation) {
  const db = await openLibrary()
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode)
      let result
      let failure
      tx.oncomplete = () => resolve(result)
      tx.onabort = () => reject(failure ?? tx.error ?? new Error('The browser save transaction was interrupted.'))
      operation(tx.objectStore(STORE), (value) => { result = value }, (error) => {
        failure = error
        tx.abort()
      })
    })
  } finally {
    db.close()
  }
}

export function listSavedGames() {
  return transaction('readonly', (store, done) => {
    const request = store.getAll()
    request.onsuccess = () => done(request.result.sort((a, b) => b.updated - a.updated))
  })
}

function updateSavedGame(id, expectedVersion, update) {
  return transaction('readwrite', (store, done, fail) => {
    const request = store.get(id)
    request.onsuccess = () => {
      if (request.result?.version !== expectedVersion) {
        fail(new Error('This save changed in another tab. Export your live game or reopen the latest local save.'))
        return
      }
      done(update(store))
    }
  })
}

export function writeSavedGame(record, expectedVersion) {
  return updateSavedGame(record.id, expectedVersion, (store) => {
    const saved = { ...record, version: crypto.randomUUID(), updated: Date.now() }
    store.put(saved)
    return saved
  })
}

export function deleteSavedGame(record) {
  return updateSavedGame(record.id, record.version, (store) => { store.delete(record.id) })
}
