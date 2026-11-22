import { createWorkerClient } from './workerClient'

let workerRequest

export async function browserRequest(path, options, rawText) {
  workerRequest ??= createWorkerClient(
    new Worker(new URL('./engine.worker.js', import.meta.url), { type: 'module' }),
    new URL(`${import.meta.env.BASE_URL}browser/manifest.json`, document.baseURI).href,
  )
  const { status, body } = await workerRequest(options?.method ?? 'GET', path, options?.body)
  if (status >= 200 && status < 300) return rawText ? body : JSON.parse(body)
  const detail = JSON.parse(body).detail
  throw new Error(typeof detail === 'string' ? detail : 'Request failed')
}

