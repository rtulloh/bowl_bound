// Thin client: it sends selections and returns what the engine said.
async function request(path, options, rawText = false) {
  const response = await fetch(path, options)
  if (response.ok && rawText) return response.text()
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Request failed')
  return body
}

const post = (path, payload) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const listTeams = () => request('/api/teams')
const controlled = (path, humanSide) => humanSide && humanSide !== 'manual' ? `${path}?human_side=${humanSide}` : path
export const newGame = (payload, humanSide) => post(controlled('/api/games', humanSide), payload)
export const getGame = (gameId, humanSide) => request(controlled(`/api/games/${gameId}`, humanSide))
export const coachStep = (gameId, humanSide, humanCall = null) => post(`/api/games/${gameId}/coach`, { human_side: humanSide, human_call: humanCall })
export const snap = (gameId, play, defense) => post(`/api/games/${gameId}/snap`, { play, defense })
export const decide = (gameId, choice, humanSide) => post(controlled(`/api/games/${gameId}/decision`, humanSide), { choice })

export const kick = (gameId, action, humanSide) => post(controlled(`/api/games/${gameId}/kick`, humanSide), { action })

export const gameAction = (gameId, action, humanSide) => post(controlled(`/api/games/${gameId}/action`, humanSide), { action })

export const saveGame = (gameId) => request(`/api/games/${gameId}/save`, undefined, true)
export const loadGame = (text) => request(
  '/api/games/load',
  { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: text },
)
