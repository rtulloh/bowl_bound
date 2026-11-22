const GAMES = 'games'
const SEASONS = 'seasons'
const DATABASE = import.meta.env.VITE_BOWL_BOUND_LIBRARY || 'bowl-bound-game-library'

function openLibrary() {
  return new Promise((resolve, reject) => {
    const request = globalThis.indexedDB.open(DATABASE, 2)
    request.onupgradeneeded = ({ oldVersion }) => {
      if (oldVersion === 0) request.result.createObjectStore(GAMES, { keyPath: 'id' })
      request.result.createObjectStore(SEASONS, { keyPath: 'id' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function transaction(storeName, mode, operation) {
  const db = await openLibrary()
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, mode)
      let result
      let failure
      tx.oncomplete = () => resolve(result)
      tx.onabort = () => reject(failure ?? tx.error ?? new Error('The browser save transaction was interrupted.'))
      operation(tx.objectStore(storeName), (value) => { result = value }, (error) => {
        failure = error
        tx.abort()
      })
    })
  } finally {
    db.close()
  }
}

function listRecords(storeName) {
  return transaction(storeName, 'readonly', (store, done) => {
    const request = store.getAll()
    request.onsuccess = () => done(request.result.sort((a, b) => b.updated - a.updated))
  })
}

function updateRecord(storeName, id, expectedVersion, update) {
  return transaction(storeName, 'readwrite', (store, done, fail) => {
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

function writeRecord(storeName, record, expectedVersion) {
  return updateRecord(storeName, record.id, expectedVersion, (store) => {
    const saved = { ...record, version: crypto.randomUUID(), updated: Date.now() }
    store.put(saved)
    return saved
  })
}

export function deleteSavedGame(record) {
  return updateRecord(GAMES, record.id, record.version, (store) => { store.delete(record.id) })
}

export const listSavedGames = () => listRecords(GAMES)
export const listSavedSeasons = () => listRecords(SEASONS)
export const writeSavedGame = (record, version) => writeRecord(GAMES, record, version)
export const writeSavedSeason = (record, version) => writeRecord(SEASONS, record, version)
