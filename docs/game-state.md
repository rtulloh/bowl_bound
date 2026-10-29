# Basic game-state transitions (Milestone 9)

`bowl_bound.game_state` applies a final ordinary outcome to possession, spot, down
and distance. It is pure: no clock, score, statistics, or random numbers.

## Field state

- `yards_to_goal` is measured from the goal the possessing team attacks, `1..99`.
  Midfield is 50. A team at its own 30 has `yards_to_goal == 70`.
- `down` is `1..4`; `yards_to_go` is `1..yards_to_goal`. When distance equals the
  distance to the goal, the situation is goal-to-go and is described as "Goal".

## Transitions

| Event | Result |
|---|---|
| Gain `>=` yards to go | First down: down 1, distance `min(10, new goal)` |
| Gain `>=` yards to goal | Touchdown; no state (scoring is Milestone 14) |
| Short gain or loss | Next down; distance shrinks or grows; goal-to-go kept |
| Incomplete pass | Next down at the same spot |
| Failed fourth down | Turnover on downs at the same spot; other team takes over |

On a turnover on downs the other team takes over at the same field spot, measured
from its own goal. Example: HOME fails on fourth down at the opponent's 30
(`yards_to_goal == 30`); AWAY takes over at its own 30 (`yards_to_goal == 70`).

## Refusals

- A result that would move the ball past the own end zone raises `EndZonePending`.
  End-zone fumbles and safety rules are resolved by `turnovers.py` in Milestone 12; ordinary
  gain safety handling remains separate so it is never guessed.
- Any pending priority result raises `PendingOutcomeError`. Pending results are never
  treated as zero yards.

## Engine-owned description

`describe(state)` returns wording such as `home: 1st and 10 at midfield`,
`away: 2nd and Goal at opponent 4`, or `home: 1st and 10 at own 30`.

## Scope

Kickoffs, punts, turnover returns, penalties, and scoring are not in this milestone.
Milestone 12 adds a separate turnover resolver for fumbles and interceptions; this module
continues to own only ordinary gains, incompletions, downs and distance.

## Validation

`tests/test_game_state.py` has 29 synthetic tests. It covers midfield, goal-to-go,
fourth-down, and end-zone boundaries. It also exhaustively checks every legal
combination of spot (1-99), down (1-4), distance and gains from -9 to 40, asserting
the state invariants.
