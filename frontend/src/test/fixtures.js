const state = (over = {}) => ({
  possession: 'home', possession_name: 'Alpha Tech', down: 1, yards_to_go: 10, yards_to_goal: 65,
  spot: 'own 35', situation: '1st and 10', attacking: 'right', ball_from_left: 35,
  first_down_from_left: 45, ...over,
})
export const view = (over = {}) => ({
  home: 'Alpha Tech', away: 'Beta State', score: { home: 0, away: 0 }, finished: false, state: state(), log: [],
  actions: {
    offense: [
      { key: '1', label: 'Line Plunge' }, { key: '2', label: 'Counter' }, { key: '9', label: 'Drop Back' },
    ],
    defense: [{ key: 'A', label: 'Formation A' }, { key: 'B', label: 'Formation B' }],
  },
  ...over,
})
export const stateView = state
export const report = (over = {}) => ({
  number: 1, supported: true, pending: false, outcome: 'advance', yards: 6,
  called_play: 'Line Plunge', resolved_play: 'Line Plunge', defense: 'Formation A',
  description: 'Alpha Tech: Line Plunge vs Formation A - gain of 6 yards',
  unsupported_reason: null, state_before: state(), state_after: state({ down: 2, yards_to_go: 4 }),
  trace: [
    { section: 'offense', team: 'Alpha Tech', play: 'Line Plunge', formation: null, roll: { faces: [1, 2, 3], total: 15 }, cell: '4' },
    { section: 'defense', team: 'Beta State', play: 'Line Plunge', formation: 'Formation A', roll: { faces: [2, 1], total: 3 }, cell: '2' },
  ],
  ...over,
})
