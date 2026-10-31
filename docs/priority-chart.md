# Ordinary play resolution and Priority Chart

Source: Bowl Bound 2007 rules, printed p.34 (PDF p.37). This is a textual
transcription, not an image of a historical team chart. Read the offensive row
against the defensive column. `#` means a nonnegative yardage, `-#` a negative
yardage, and `blank` a white no-change cell. `INC` represents a black cell.

## ASCII chart

<!-- priority-matrix:start -->
```text
OFFENSE \ DEFENSE | #   | -#  | blank | (#)   | (-#)    | [#]   | [-#]    | TD        | QR     | QT     | INT     | F       | INC
------------------+-----+-----+-------+-------+---------+-------+---------+-----------+--------+--------+---------+---------+--------
# / B             | ADD | ADD | ADD   | D     | D       | D     | D       | D         | D      | D      | D       | D       | INC
-#                | ADD | ADD | ADD   | D     | D       | D     | D       | D         | D      | D      | D       | D       | INC
(#)               | O   | O   | O     | O     | O       | D     | D       | D         | O      | O      | O       | O       | O
blank             | ADD | ADD | ADD   | D     | D       | D     | D       | D         | D      | D      | D       | D       | INC
TD                | O   | O   | O     | D     | D       | D     | D       | D         | D      | D      | D       | D       | INC
QR                | ADD | ADD | ADD   | D     | D       | D     | D       | D         | D      | D      | D       | D       | INC
QT                | O   | O   | O     | D     | D       | D     | D       | D         | D      | D      | D       | D       | INC
INC               | INC | INC | INC   | D     | D       | D     | D       | D         | D      | D      | D       | D       | INC
INT               | O   | O   | O     | INC   | INT_MIN | INC   | INT_MIN | INC       | QT     | O      | INT_MIN | O       | O
F                 | O   | O   | O     | F_DEF | F_MIN   | F_DEF | F_MIN   | F_ENDZONE | O      | O      | D       | F_MIN   | O
SOP / BLP         | OPT | OPT | OPT   | OPT   | OPT     | OPT   | OPT     | OPT       | OPT    | OPT    | OPT     | OPT     | OPT
PEN               | PEN | PEN | PEN   | PEN   | PEN     | PEN   | PEN     | PEN       | PEN    | PEN    | PEN     | PEN     | PEN
```
<!-- priority-matrix:end -->

The defensive TD column represents both printed `(TD)` and `[TD]`. The p.38
correction gives defensive `(TD)` the same priority as `[TD]`, without changing
its original source token. The chart-specific exceptions below still apply.

### Operation key

- **O / D:** select the offensive / defensive fact, including its out-of-bounds
  marker. The other fact does not contribute yardage or its marker.
- **ADD:** add signed yardage (blank is zero); retain either out-of-bounds marker.
  B and QR first roll their supplemental column; the defensive yards are then added
  to the supplemental result. They are never zero-yard results.
- **INC:** incomplete pass. No distance and no supplemental roll.
- **QT:** the chart explicitly changes offensive INT against defensive QR into
  Quarterback Trapped, not QR. The QT column is then rolled, with no defense retained.
- **INT_MIN:** interception at the lesser signed yardage from the two cells.
- **F_DEF:** offensive fumble at the defensive yardage.
- **F_MIN:** offensive fumble at the lesser signed yardage from the two cells.
- **F_ENDZONE:** offensive fumble one yard into the defenders' end zone.
- **OPT:** cancel the ordinary defense and follow SOP/BLP under Play 7/8. Advanced
  defenses are unavailable; their exceptions belong to Milestone 22.
- **PEN:** begin the penalty procedure, retaining the original defensive fact.

Minimum locations use signed comparison as an explicit project interpretation:
`min(12, -3) = -3`, not the smaller absolute distance. Basic VI-9/10 describes
signed spotting, but does not define the chart's `< #` notation independently.

## Rulebook discrepancies and precedence

- Printed p.3 gives `(4)` versus `(-1)` as 3, saying parentheses offset. The
  Priority Chart instead retains the offensive result: 4. This implementation
  follows the chart. `(4)` versus ordinary `-1` also gives 4.
- Printed p.38 says defensive TD always overrides except penalties. That broad
  statement does not erase the chart's INT/TD -> INC, F/TD -> F_ENDZONE, or
  SOP/BLP exceptions. Printed p.4 explicitly confirms INT/TD -> INC; printed p.3
  confirms F/TD is a fumble one yard deep.
- The published Priority Chart has no defensive Breakaway column. For this unusual
  imported result, the owner ruled on 2026-10-30 that a parenthesized defensive
  Breakaway overrides the offense except for an offensive parenthesized yardage result
  or a penalty. When it wins, the offense rolls its own B column, as for any Breakaway.
  This is limited to parenthesized Breakaway facts in defensive cells; it does not
  generalize priority decoration to other named results.
- Basic VI-12 names advanced defensive exceptions II.1-II.3, whereas the chart
  mentions Wild Card only. None is enabled in Milestone 7.

These interpretations are also recorded in [the rules profile](rules-profile.md).

## Engine API and scope

`bowl_bound.resolution.resolve_cells(offense, defense)` applies this table to
normalized facts without parsing source text, inspecting PDF colors, or rolling dice.
It returns an immutable `PriorityResult` with the operation, selected source, kind,
distance, pending flag, original input facts, and chart row/column categories.

`resolve_play(offense_team, defense_team, play, formation, dice)` consumes one
offensive roll then one defensive roll, looks up both cells, and returns
`PlayResolution`. Trace entries retain team/season, play, formation, physical dice
faces, consulted cell, and provenance. Invalid calls fail before dice are consumed.
Special-team facts and unsupported chart coordinates fail explicitly.

### Supplemental and Option resolution (Milestone 8)

- **B / QR / QT:** one offensive reroll consults the matching supplemental column
  (trace section `supplemental:B`, `supplemental:QR`, `supplemental:QT`). The reroll
  result is combined with the original defense only when the Priority Chart said
  ADD (B/QR); QT and defensive overrides retain no defense. A chain of B/QR/QT results
  keeps rolling; more than 10 consecutive rerolls is an invalid chart and raises.
- **Option (SOP / BLP):** the defensive result is nullified (a blank), and one
  offensive reroll consults Play 7 (SOP) or Play 8 (BLP) (trace section `option`).
  `called_play` stays Play 5; `resolved_play` becomes 7 or 8. No second defensive roll.
- **Overridden results** (for example, a defensive incomplete over B) consume no
  supplemental roll.

`resolve_cells` remains a pure symbolic priority lookup. `resolve_play` materializes
selected DS/X/T1–T3 distances (including supplemental and decorated defensive
turnover locations) using independent offensive face rolls, in offense/defense
order, traced as `variable:offense` / `variable:defense`. Overridden distances do
not consume dice. Original symbolic chart facts/provenance are retained.
Turnovers still await the engine recovery/return decision; no decision is fabricated.
Penalties are resolved by the [penalty procedure](penalties.md), which rerolls and then
waits for an explicit accept or decline. Original operands retain all symbolic distances.
F_ENDZONE carries a depth of one yard. This module does not update possession, field
position, clocks, score, or statistics.

## Exhaustive validation

`tests/priority_matrix.py` is an independently transcribed 12-by-13 expected matrix,
not imported or generated from the resolver table. `tests/test_priority_matrix.py`
checks all 156 printed intersections, expanded to **196 cases** (B, BLP, both
defensive TD decorations), for operation, outcome, source, and pending status. A
second pass runs every coordinate through `resolve_play`, asserting the two initial
rolls and exactly one extra roll only for B/QR/QT/Option. A separate test keeps this
ASCII table synchronized. `tests/test_supplemental_resolution.py` covers the reroll
columns, defense retention/cancellation, Option redirection, chains, and cycles.
