// Real engine/API responses in React's DOM harness; this is not Chromium coverage.
import { execFileSync, spawn } from 'node:child_process'
import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { saveGame } from '../api'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const nativeFetch = globalThis.fetch
let server, folder, base, fixtures
let requests = [], loaded = []

function pythonCommand() {
  if (process.env.BB_PYTHON) return process.env.BB_PYTHON
  const executable = process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'
  const local = join(root, '.venv', executable)
  if (existsSync(local)) return local
  const common = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd: root, encoding: 'utf8' }).trim()
  const shared = resolve(root, common, '../.venv', executable)
  return existsSync(shared) ? shared : 'python3'
}

beforeAll(async () => {
  folder = mkdtempSync(join(tmpdir(), 'bowl-bound-review-integration-'))
  const python = pythonCommand()
  const env = { ...process.env, PYTHONPATH: root }
  fixtures = JSON.parse(execFileSync(python, ['-m', 'tests.review_integration_fixtures', folder], { cwd: root, env, encoding: 'utf8' }))
  const port = await new Promise((done) => {
    const probe = createServer()
    probe.listen(0, '127.0.0.1', () => {
      const value = probe.address().port
      probe.close(() => done(value))
    })
  })
  base = 'http://127.0.0.1:' + port
  let errors = ''
  server = spawn(python, ['-c', 'import sys; from pathlib import Path; import uvicorn; from backend.app import create_app; uvicorn.run(create_app(Path(sys.argv[1])), host="127.0.0.1", port=int(sys.argv[2]), log_level="warning")', folder, String(port)], { cwd: root, env, stdio: ['ignore', 'ignore', 'pipe'] })
  server.stderr.on('data', (chunk) => { errors += chunk })
  for (let attempt = 0; attempt < 100; attempt++) {
    try { if ((await nativeFetch(base + '/api/health')).ok) return } catch {}
    if (server.exitCode !== null) throw new Error('Real-engine test server exited: ' + errors)
    await new Promise((done) => setTimeout(done, 40))
  }
  throw new Error('Real-engine test server did not become healthy: ' + errors)
}, 20_000)

afterAll(async () => {
  if (server && server.exitCode === null) {
    await new Promise((done, reject) => {
      const timer = setTimeout(() => reject(new Error('Owned test API server did not stop')), 5000)
      server.once('exit', () => { clearTimeout(timer); done() })
      server.kill('SIGTERM')
    })
  }
  if (folder) rmSync(folder, { recursive: true, force: true })
})
beforeEach(() => {
  requests = []; loaded = []
  vi.stubGlobal('fetch', async (path, options) => {
    requests.push({ path, method: options?.method || 'GET' })
    const response = await nativeFetch(base + path, options)
    if (path.startsWith('/api/games/load') && response.ok) loaded.push(await response.clone().json())
    return response
  })
})
afterEach(() => vi.unstubAllGlobals())

async function upload(text) {
  const before = loaded.length
  const input = screen.getByLabelText('Load saved game')
  const menu = input.closest('details')
  if (menu && !menu.open) fireEvent.click(screen.getByText('Game', { selector: 'summary' }))
  fireEvent.change(input, { target: { files: [{ size: text.length, text: async () => text }] } })
  await waitFor(() => expect(loaded).toHaveLength(before + 1))
  await waitFor(() => expect(screen.getByLabelText('Load saved game')).not.toBeDisabled())
  return loaded.at(-1)
}
const coaches = () => requests.filter((request) => request.path.endsWith('/coach')).length
const scheduledPause = async () => act(async () => { await new Promise((done) => setTimeout(done, 350)) })

it.each(['home', 'away'])('retains two-point review before the real required kick reception, human=%s', async (human) => {
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: human } })
  await upload(fixtures['two_' + human])
  expect(await screen.findByTestId('session-status')).toHaveTextContent('is going for two. Choose your defense')
  expect(screen.getByTestId('log-entry')).toHaveTextContent('is going for two.')
  fireEvent.click(screen.getByTestId('defense-play-a'))
  const review = await screen.findByRole('region', { name: 'Two-point result' })
  expect(review).toHaveTextContent('two-point conversion no good')
  const before = coaches()
  await scheduledPause()
  expect(coaches()).toBe(before)
  fireEvent.click(within(review).getByRole('button', { name: 'Continue' }))
  fireEvent.click(await screen.findByTestId('penalty-choice-kick:touchback'))
  await waitFor(() => expect(screen.getAllByTestId('log-entry')).toHaveLength(3))
  const entries = screen.getAllByTestId('log-entry')
  expect(entries[0]).toHaveTextContent('is going for two.')
  expect(entries[1]).toHaveTextContent('two-point conversion no good')
  expect(entries[2]).toHaveTextContent(/kickoff.*touchback/i)
  expect(screen.queryByRole('region', { name: 'Two-point result' })).toBeNull()
}, 10_000)

it('loads and resumes the real halftime review once, before the computer kickoff', async () => {
  render(<App />)
  await screen.findByTestId('start-game')
  await upload(fixtures.halftime)
  const review = await screen.findByRole('region', { name: 'HALFTIME' })
  expect(review).toHaveTextContent('Home — Q1 0, Q2 0, Half 0.')
  expect(review).toHaveTextContent('Away kicks to Home to start the second half.')
  await scheduledPause()
  expect(coaches()).toBe(0)
  await upload(fixtures.halftime)
  expect(screen.getAllByRole('region', { name: 'HALFTIME' })).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Start second half' }))
  await screen.findByTestId('offense-play-1')
  await waitFor(() => expect(screen.queryByRole('region', { name: 'HALFTIME' })).toBeNull())
  const current = loaded.at(-1)
  const saved = await saveGame(current.game_id)
  const calls = coaches()
  await upload(saved)
  await scheduledPause()
  expect(screen.queryByRole('region', { name: 'HALFTIME' })).toBeNull()
  expect(coaches()).toBe(calls)
}, 10_000)

it('keeps actual PAT and complete kick-return records in full history across reload', async () => {
  render(<App />)
  await screen.findByTestId('start-game')
  fireEvent.change(screen.getByLabelText('Control mode'), { target: { value: 'manual' } })
  const current = await upload(fixtures.history)
  fireEvent.click(screen.getByRole('button', { name: 'Show complete history' }))
  let entries = screen.getAllByTestId('log-entry')
  expect(entries).toHaveLength(43)
  for (const [index, entry] of current.view.log.entries()) expect(entries[index]).toHaveTextContent(entry.commentary)
  expect(current.view.log.filter((entry) => entry.outcome === 'pat_good')).toHaveLength(14)
  expect(current.view.log.filter((entry) => entry.outcome === 'kickoff_return')).toHaveLength(15)
  await upload(await saveGame(current.game_id))
  entries = screen.getAllByTestId('log-entry')
  expect(entries).toHaveLength(43)
  for (const [index, entry] of current.view.log.entries()) expect(entries[index]).toHaveTextContent(entry.commentary)
}, 10_000)
