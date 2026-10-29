# Milestone 21 — public sample coaching comparison

All data below uses the original fictional Cedar Valley and Harbor Tech charts.
The runner reads no historical charts, private saves or local play logs.

## Method

Run from the repository root using Python 3.12.8:

~~~sh
.venv/bin/python -m bowl_bound.coaching_audit --seeds 101 307
~~~

The command writes JSON to stdout; redirect it to an ignored local file if needed.
It accepts optional `--policies baseline easy-v1 medium-v1 hard-v1` (and legacy
`chart-v1`). Only the two public samples are loaded; no private-team path option
is offered. Errors emit a generic JSON error and exception type to stderr, never
engine exception text, chart cells or local paths. Exit status is nonzero on failure.

The default matrix includes baseline, Easy, Medium and Hard: gameplay seeds
101/307, both home/away sample arrangements and both CPU sides, 32 games total.
CPU and stand-in coaching seeds are independent SHA-256-derived 63-bit values
keyed by gameplay seed, arrangement, side, policy and stream purpose. There are
32 distinct CPU seeds and 32 distinct stand-in seeds in this matrix.

The public-observation baseline stand-in can now choose legal punts, field goals
and game actions. This fixes AI-009’s earlier forced-fourth-down-snap limitation.
These are reproducible games, not a calibrated strength tournament: different
policies consume dice along different game paths. Scores are descriptive, not
paired causal win-probability measurements.

Each game reconciles the scoring ledger and independently observed period score
deltas against final scores, statistics against report facts, every clock debit,
all four 900-second quarters, settled supported reports and structured chart traces.
Period deltas are attributed to the engine period before each command, including
overtime rounds; they are audit observations, not a second scoring rules engine.
The saved continuation is checked after the named default checkpoint (step 40),
including calls, reports, decisions and full state. Evidence includes the actual
number of replayed commands; a mismatch fails rather than setting a success flag.
The runner never submits another command once the engine reports a finished game.

Per-call evidence contains the actual normalized policy preference vector observed
without extra draws or global RNG changes. Deterministic decisions are one-hot.
Discarded fallback draws and subsequent concealed-turn previews are excluded from
the committed call’s vector. An illegal CPU selection is counted then rejected;
a successfully returned game therefore has zero observed illegal selections.

Comparable-call buckets preserve role, side, down, quarter, phase, overtime, hurry
and legal menus. Distance: <=3/6/10/long. Field: <=20/50/80/deep yards to goal.
Clock: <=60/120/180/ordinary seconds. Score: tied/one-score/multiple-score lead or
deficit. Repetition is the same call on successive appearances in the same bucket.
Each bucket reports samples, distinct calls, largest share, longest comparable
streak and a small-sample flag (<30). Ordinary first/second/third-down offensive
or defensive buckets with at least 30 samples, multiple legal alternatives and
>=50% largest share receive an **advisory** concentration flag—not a failure,
usage cap or proof of bad coaching.

## Results — AI-009 remediation rerun

This replaces earlier tables. All paths, including baseline, change because
stand-in legality and per-game coaching seeds changed; do not interpret changes
from the previous forced-snap comparison as isolated policy-strength effects.

| Policy | Games | Reports | Comparable | Repeated | Fallbacks | Home score range | Away score range |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| baseline | 8 | 1379 | 169 | 32 | 0 | 3–36 | 10–40 |
| easy-v1 | 8 | 1351 | 185 | 33 | 0 | 6–30 | 0–27 |
| medium-v1 | 8 | 1385 | 196 | 44 | 0 | 0–38 | 3–29 |
| hard-v1 | 8 | 1373 | 187 | 25 | 0 | 0–27 | 3–39 |

All 32 finished and reconciled clocks, statistics and scores. All saved futures
matched: **5,123 compared continuation commands**, **5,520 committed preference
vectors**, zero observed illegal CPU selections, zero analysis fallbacks.

### CPU called offensive plays

Columns 1–9 are called plays, not resolved run/pass statistics (Option may branch).

| Policy | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Punt | FG | Kickoff | Kneel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 57 | 42 | 58 | 67 | 52 | 72 | 72 | 68 | 54 | 47 | 11 | 34 | 1 |
| easy-v1 | 77 | 85 | 85 | 67 | 67 | 58 | 59 | 56 | 50 | 42 | 14 | 37 | 2 |
| medium-v1 | 62 | 44 | 42 | 70 | 59 | 88 | 65 | 94 | 81 | 42 | 13 | 40 | 2 |
| hard-v1 | 74 | 69 | 70 | 70 | 70 | 64 | 79 | 69 | 78 | 27 | 11 | 34 | 4 |

### CPU called defensive formations

| Policy | A | B | C | D | E | F |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 115 | 88 | 92 | 112 | 101 | 111 |
| easy-v1 | 93 | 81 | 73 | 86 | 88 | 115 |
| medium-v1 | 94 | 85 | 85 | 87 | 100 | 110 |
| hard-v1 | 68 | 106 | 74 | 87 | 90 | 108 |

### Stand-in fourth-down special actions

| CPU policy | Stand-in punts | Stand-in field goals |
| --- | ---: | ---: |
| baseline | 33 | 11 |
| easy-v1 | 50 | 9 |
| medium-v1 | 40 | 16 |
| hard-v1 | 38 | 13 |

## Review and limitations

- Every tier used all nine calls and all six formations; no single-call lockup.
- Hard punted 27 times. Separate synthetic regressions enforce made-FG,
  goal-line-touchdown and obvious-punt valuation; counts alone are not acceptance.
- No concentration advisories occurred in this small, finely bucketed matrix.
  Small-sample buckets are retained explicitly rather than declared balanced.
- Zero fallbacks here do not replace synthetic whole-comparison failure tests.
- The samples, baseline stand-in and heuristic utility cannot establish that Hard
  wins more often. No dice, charts or football rules were tuned to improve results.
- Tests deliberately corrupt replay state and period totals, reject invalid
  preference vectors and verify no kickoff is submitted after completion.

## Named behavior profiles (AI-007)

The comparison above uses `baseline-v1`, `easy-v1`, `medium-v1` and `hard-v1`
behavior profiles (persisted baseline policy remains `baseline`) and
`coaching-audit-v1` evidence thresholds. Legacy `chart-v1` is available explicitly
but is not part of the default matrix. Profile extraction preserves the existing
values and policy streams; current JSON includes per-game `behavior_profile`
and `audit_profile` names. No new strength claim or retuning accompanies this
metadata/refactor.

## Final-source repeat — 2026-10-28

On source `41da5fd`, reran `.venv/bin/python -m bowl_bound.coaching_audit
--seeds 101 307` using only the public fictional samples. All 32 games finished
and reconciled: 5,123 compared replay commands, 5,520 committed preference
vectors, zero observed illegal CPU selections or fallbacks. Removing the two
new profile-name fields yields exact JSON equality with the AI-009 evidence.
Each of baseline/Easy/Medium/Hard contributes eight games and names its behavior
profile plus `coaching-audit-v1`. Thus the extraction/deduplication did not change
this matrix; this is not proof of coaching optimality or stronger Hard play.
Full JSON remains in the approved local OpenCode temporary directory, not in
release artifacts or historical chart storage.
