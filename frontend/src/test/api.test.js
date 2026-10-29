import { afterEach, describe, expect, it, vi } from 'vitest'
import { decide, kick, saveGame } from '../api'

afterEach(() => vi.restoreAllMocks())

describe('decide', () => {
  it('posts the engine choice to the game decision endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ view: {} }),
    })

    await decide('game-42', 'accept')

    expect(fetchMock).toHaveBeenCalledWith('/api/games/game-42/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ choice: 'accept' }),
    })
  })
  it('posts only the engine action key to the kick endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true, json: () => Promise.resolve({ view: {} }),
    })
    await kick('game-42', 'punt')
    expect(fetchMock).toHaveBeenCalledWith('/api/games/game-42/kick', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'punt' }),
    })
  })
})

it('downloads saves as opaque text, preserving integers outside JavaScript safe range', async () => {
  const exact = '{"config":{"coach_seed":9223372036854775807}}'
  const json = vi.fn(async () => JSON.parse(exact))
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, text: async () => exact, json })
  expect(await saveGame('game-42')).toBe(exact)
  expect(json).not.toHaveBeenCalled()
})
