import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import SaveControls from '../components/SaveControls'
import { loadGame, saveGame } from '../api'

vi.mock('../api', () => ({ loadGame: vi.fn(), saveGame: vi.fn() }))
beforeEach(() => vi.clearAllMocks())

it('uploads an opaque save and hands the engine response to the application', async () => {
  const loaded = { game_id: 'new', view: { pending: { kind: 'engine' } } }
  loadGame.mockResolvedValue(loaded)
  const onLoaded = vi.fn()
  const onBusyChange = vi.fn()
  render(<SaveControls onLoaded={onLoaded} onBusyChange={onBusyChange} onError={vi.fn()} />)
  fireEvent.change(screen.getByLabelText('Load saved game'), { target: { files: [{ size: 20, text: async () => '{"opaque":true}' }] } })
  await waitFor(() => expect(onLoaded).toHaveBeenCalledWith(loaded))
  expect(loadGame).toHaveBeenCalledWith('{"opaque":true}')
  expect(onBusyChange.mock.calls).toEqual([[true], [false]])
})

it('does not replace the current game after a failed load', async () => {
  loadGame.mockRejectedValue(new Error('Incompatible save'))
  const onLoaded = vi.fn()
  const onError = vi.fn()
  render(<SaveControls gameId="old" onLoaded={onLoaded} onBusyChange={vi.fn()} onError={onError} />)
  fireEvent.change(screen.getByLabelText('Load saved game'), { target: { files: [{ size: 1, text: async () => '?' }] } })
  await waitFor(() => expect(onError).toHaveBeenCalledWith('Incompatible save'))
  expect(onLoaded).not.toHaveBeenCalled()
})

it('blocks oversized files without reading or uploading them and disables busy controls', async () => {
  const onError = vi.fn()
  const text = vi.fn()
  const { rerender } = render(<SaveControls gameId="old" onLoaded={vi.fn()} onBusyChange={vi.fn()} onError={onError} />)
  fireEvent.change(screen.getByLabelText('Load saved game'), { target: { files: [{ size: 3 * 1024 * 1024, text }] } })
  await waitFor(() => expect(onError).toHaveBeenCalled())
  expect(text).not.toHaveBeenCalled()
  expect(loadGame).not.toHaveBeenCalled()
  rerender(<SaveControls gameId="old" busy onLoaded={vi.fn()} onBusyChange={vi.fn()} onError={onError} />)
  expect(screen.getByLabelText('Load saved game')).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Save game' })).toBeDisabled()
})

it('downloads versioned JSON and releases its temporary browser URL', async () => {
  const exact = '{"schema_version":1,"config":{"coach_seed":9223372036854775807}}'
  saveGame.mockResolvedValue(exact)
  const RealBlob = globalThis.Blob
  const makeBlob = vi.spyOn(globalThis, 'Blob').mockImplementation(function(parts, options) { return new RealBlob(parts, options) })
  URL.createObjectURL = vi.fn(() => 'blob:save')
  URL.revokeObjectURL = vi.fn()
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  render(<SaveControls gameId="old" onLoaded={vi.fn()} onBusyChange={vi.fn()} onError={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Save game' }))
  await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:save'))
  expect(saveGame).toHaveBeenCalledWith('old')
  expect(click).toHaveBeenCalledOnce()
  expect(makeBlob.mock.calls[0][0]).toEqual([exact])
  makeBlob.mockRestore()
  click.mockRestore()
})
