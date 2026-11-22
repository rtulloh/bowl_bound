// Thin client: it sends selections and returns what the engine said.
async function request(path, options, rawText = false) {
  if (import.meta.env.MODE === 'browser') {
    const { browserRequest } = await import('./runtime/browserRequest')
    return browserRequest(path, options, rawText)
  }
  const response = await fetch(path, options)
  if (response.ok && rawText) return response.text()
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Request failed')
  return body
}

const post = (path, payload) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const listTeams = () => request('/api/teams')
export const getRules = (season, gameType) => request(`/api/rules?season=${season}&game_type=${gameType}`)
const controlled = (path, humanSide) => humanSide && humanSide !== 'manual' ? `${path}?human_side=${humanSide}` : path
export const newGame = (payload, humanSide) => post(controlled('/api/games', humanSide), payload)
export const getGame = (gameId, humanSide) => request(controlled(`/api/games/${gameId}`, humanSide))
export const coachStep = (gameId, humanSide, expectedRevision, humanCall = null) => post(`/api/games/${gameId}/coach`, { human_side: humanSide, human_call: humanCall, expected_revision: expectedRevision })
export const snap = (gameId, play, defense) => post(`/api/games/${gameId}/snap`, { play, defense })
export const decide = (gameId, choice, humanSide) => post(controlled(`/api/games/${gameId}/decision`, humanSide), { choice })

export const kick = (gameId, action, humanSide) => post(controlled(`/api/games/${gameId}/kick`, humanSide), { action })

export const gameAction = (gameId, action, humanSide) => post(controlled(`/api/games/${gameId}/action`, humanSide), { action })

export const saveGame = (gameId) => request(`/api/games/${gameId}/save`, undefined, true)
export const loadGame = (text, humanSide) => request(
  controlled('/api/games/load', humanSide),
  { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: text },
)

export const getCharts = (gameId, side) => request(`/api/games/${gameId}/charts?side=${side}`)

export const listSeasonTemplates = () => request('/api/seasons/templates')
export const createSeason = (payload) => post('/api/seasons', payload)
export const summarizeSeason = (snapshot) => post('/api/seasons/summary', { snapshot })
export const recordSeasonResult = (gameId, payload) => post(`/api/games/${gameId}/season-result`, payload)
export const removeSeasonResult = (payload) => post('/api/seasons/remove-result', payload)
