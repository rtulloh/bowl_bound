# College offensive statistics (Milestone 17)

The engine attaches immutable `PlayStatistics` credit to each committed play report
and folds those credits into `view.statistics`. No clock request, view request,
choice setup or pending result is another statistical play. The API serializes the
engine's numbers; the browser displays the supplied table labels and values.

## Supported team totals

- Rushing attempts, net yards and touchdowns.
- Passing attempts, completions, net yards, touchdowns and interceptions thrown.
- Sacks taken and sack yards lost (shown as positive loss yardage).
- Total offensive plays = rushing attempts + passing attempts.
- Total offense yards = net rushing yards + net passing yards.

Sacks are already included in rushing attempts/yards. They must not be subtracted
again from total offense or passing yards. These are **offensive team summaries**,
not a complete NCAA box score. Player allocation, first downs, drive/red-zone and
third/fourth-down summaries, time of possession, fumbles-lost totals, kicking/return
statistics and individual defensive credit are not represented by these fields.
The existing scoring ledger remains authoritative for all points, including
returns, safeties and conversions; offensive touchdowns alone do not sum to score.

## Chart classification policy

The user approved explicit-marker classification on 2026-10-26. This is a named
Bowl Bound accounting interpretation, not an assertion that a numeric chart cell
identifies every real-world player's action:

| Committed result | Offensive credit |
| --- | --- |
| Ordinary plays 1–5 | Rush |
| Option resolved to SOP/BLP (7/8) | Use the resolved passing play, not the called Option |
| Ordinary numeric/no-change/TD on plays 6–9 | Completed pass, even for zero or negative yards |
| QR branch | Rush, never an inferred sack merely because yardage is negative |
| QT branch with a loss | Sack: one rushing attempt and net rushing loss; no pass attempt |
| QT at zero or positive yards | Rush, no sack |
| Final incomplete result | Incomplete pass attempt |
| Interception returned | Pass attempt plus interception; no completion or offensive yards |
| Interception declared incomplete | Incomplete pass attempt; no interception |
| Bad snap during a scrimmage pass call | Team rushing attempt/loss, no completion or sack |
| Automatic kneel | Team rushing attempt/loss, no sack |
| Automatic spike | Incomplete team pass attempt |

B/QR/QT supplemental evidence comes from typed lookup traces, never parsed UI
wording or raw PDF tokens. Breakaway yardage retains its originating category;
the last consulted QR/QT branch controls a chain, but a penalty reroll discards
prior branch classification while retaining its audit trace. A fumble retains the resolved
play's category unless explicit QR/QT or bad-snap evidence says otherwise; there
is no invented passer/receiver identity. A pass fumble without those markers is
accounted as a completed pass followed by a fumble.

## Yardage and exclusions

- Measure actual net gains/losses, clipped at either goal line. A 50-yard chart
  result from the opponent 8 credits eight yards, not 50. A printed TD credits the
  distance to goal. A safety loss is limited to the distance to the own goal line.
- Use resolved variable fumble locations, without another roll. The normalized
  resolution/report carries that observed location while its trace keeps the
  original source cell and variable-location rolls.
- Include original-team fumble-recovery advances in the originating rush/pass
  category. Stop offensive yardage at the first opposing recovery, even if a
  later fumble gives the original offense the ball again. Defensive/interception
  return yards and touchdowns are not offense, including after reacquisition.
  Attribution audits the already observed recovery/return trace and never changes
  possession or rolls dice.
- Accepted return penalties retain legal advance to the engine-provided enforcement
  base, including the Bowl Bound offensive-return midpoint restriction. Stepped-off
  foul yardage is never offense. Declined penalties retain the actual advance.
  Pending returns/penalties count only when the procedure finishes.
- Accepted previous-spot penalties, pre-snap fouls and offsetting/replayed downs
  contribute no rush/pass attempt or yardage. An end-of-gain accepted penalty
  retains the underlying attempt/gain but excludes penalty yardage. Declined
  penalties retain the actual result. This follows the engine's available
  previous/end enforcement facts, not an invented foul spot.
- Exclude all PAT/two-point plays and their penalties/returns. In particular,
  overtime paired tries are conversions, not offensive snaps. Full-series overtime
  scrimmage plays count with regulation totals. Exclude kicks/returns and
  unsupported/unapplied results from offensive totals.

## Contract

`report.statistics` contains `kind` (`excluded`, `rush`, `completion`,
`incomplete`, `interception` or `sack`), `team` (`home`/`away`, null when
excluded), `yards` and `touchdown`. It is a credit, not a second gameplay outcome.
Both called and resolved play labels remain intact, including on a bad snap.

`view.statistics.home` and `.away` contain numeric totals with the field names used
by `TeamStatistics` in `bowl_bound/statistics.py`. `view.statistics.rows` supplies
engine-formatted `label`, `home` and `away` strings for display-only clients. The
browser exposes these in the collapsible **Team statistics** table. Existing
clients may ignore the additive fields; no request format changes.

The summary is a fold of committed credits, not a mutable counter updated by
polling. Every view and final-state guard therefore shares the same audited
ledger. Statistics consume no random values and cannot affect gameplay or clock.

## Sources and historical boundary

Reviewed 2026-10-26: [2022 NCAA Football Statisticians' Manual](http://fs.ncaa.org/Docs/stats/Stats_Manuals/Football/2022.pdf),
Basic Interpretations 11–12 (overtime, team kneels/spikes), Sections 2–3 (net rushing,
negative completions, losses attempting to pass), Section 13 (fumble advances),
Section 14 (penalty exclusions/retained gains), and Section 16 (sacks).
The public PDF was examined in memory and is not copied into this repository.

Use these college team-accounting conventions for the supported game profiles;
this does not recreate historical changes to NCAA statistical reporting. Home
season still selects gameplay rules, not NFL sack accounting. Bowl Bound's
approved chart/penalty/try policies override cases for which its engine has no
real-world player/contact/foul-location evidence.
