import { createWorkerClient } from './workerClient'

function setup() {
  const worker = new EventTarget()
  worker.postMessage = vi.fn()
  worker.terminate = vi.fn()
  return { worker, request: createWorkerClient(worker, 'https://example.test/game/browser/manifest.json') }
}

test('correlates replies and transfers save text without reserializing it', async () => {
  const { worker, request } = setup()
  const save = '{"seed":9007199254740993}'
  const load = request('POST', '/api/games/load', save)
  const list = request('GET', '/api/teams')
  expect(worker.postMessage.mock.calls[0][0].body).toBe(save)
  worker.dispatchEvent(new MessageEvent('message', { data: { id: 2, result: { status: 200, body: '{}' } } }))
  worker.dispatchEvent(new MessageEvent('message', { data: { id: 1, result: { status: 200, body: save } } }))
  expect((await list).body).toBe('{}')
  expect((await load).body).toBe(save)
})

test('rejects outstanding and future commands after a worker failure', async () => {
  const { worker, request } = setup()
  const first = request('GET', '/api/teams')
  worker.dispatchEvent(new Event('error'))
  await expect(first).rejects.toThrow(/reload/i)
  await expect(request('POST', '/api/games')).rejects.toThrow(/reload/i)
  expect(worker.postMessage).toHaveBeenCalledTimes(1)
  expect(worker.terminate).toHaveBeenCalledOnce()
})
