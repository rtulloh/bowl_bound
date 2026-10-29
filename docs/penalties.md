# Penalty procedure (Milestone 11)

Source: Bowl Bound 2007 Basic VI-4, printed pp. 6-9. Paydirt's penalty code was used as a
structural and test reference only; its yardage table and NFL enforcement are not copied.

## What happens on a PEN result

1. The offense rerolls its dice and looks up the **same play** again. The **original
   defensive result is retained**, so the defense is never rerolled. If the first result
   came from an Option, the reroll uses the resolved play (Play 7 or 8).
2. A reroll that is itself a penalty adds another foul and rerolls again, up to 100 times;
   past that the chart is rejected as invalid instead of looping.
3. A reroll that is B, QR, QT or an Option follows the normal supplemental rules.
4. **S and R** penalties first roll the offensive dice for their distance (the printed
   table). Fixed, 5Y, 5X and PI distances need no roll.

Every roll is recorded in the trace in the order it happened: `penalty_yardage`,
`penalty_distance`, `penalty_reroll`, `option` and `supplemental:*`.

## Who decides

The **offended** team chooses, and the choice is **derived from the foul's team, never from
the chart column** it was printed in. After a penalty the session shows the choice and
**nothing else can happen until it is made**: a new snap is refused (409) and consumes no dice.

| Situation | Result |
| --- | --- |
| One foul | Accept it (from the previous spot, or from the end of the gain where allowed) or decline |
| Several fouls by one team | Choose **one**. Distances are never added together |
| Fouls by both teams | **Offsetting**: the play is cancelled and the down is replayed, with no choice |
| OFF 5A (pre-snap, table 20-32) | No play and no refusal: enforced automatically, down replayed |
| PI | Stops all rerolls and cancels the defense; declining leaves an **incomplete pass** |

A decision applies **exactly once**. An unknown or disabled choice is refused (422) and
changes nothing. A decision with nothing pending is refused (409).

Declining an interception/fumble reroll continues the real turnover procedure,
including any end-zone choice, with the original prepared cells and dice source.
It does not reroll a lookup or record a second play. Variable yardage is resolved
by the full-feature method before the decision. Genuinely unsupported results
remain disabled with an engine-provided reason.

## Table (full-feature method)

| Penalty | OFF S | DEF S | OFF R | DEF R |
| --- | --- | --- | --- | --- |
| 5 yards | 10-19 | 10-24, 30-32 | 10-19 | - |
| 5A (pre-snap) | 20-32 | - | - | - |
| 5Y (marked from end of gain) | - | 25-29 | - | 20-29 |
| 10 yards | 33-36 | 33 | 30-39 | 10-19 |
| 15 yards | 37-39 | 34-39 (auto first down, from end of gain) | 20-29 | 30-39 (auto first down, from end of gain) |

Fixed chart tokens: `DEF 15` carries an automatic first down and may be marked from the end
of the gain; other fixed distances are ordinary. `DEF 5X` and `DEF 5Y` are both read as
**5Y**: five yards, no automatic first down, from the end of the gain. The source token is
kept in the penalty's `source`. PI distances are capped at 15, may be variable (DS, X, T1-T3),
and a variable distance is rolled and traced.

## Enforcement

- Penalties are marked from the **previous spot** unless the offended team chooses the end of
  a positive, in-field gain and the penalty allows it.
- No penalty except PI may exceed **half the distance to the offender's goal**. Distances are
  whole yards: half-distance rounds **down**, so the penalty is the smaller of the table
  distance and half the distance, toward midfield.
- PI is spotted at the foul; if the line of scrimmage is outside the 2, the spot cannot be
  inside the 2; on or inside the 2 it is half the distance.
- An accepted penalty **replays the down**. It earns a first down only if the new spot reaches
  the line to gain or the penalty carries one. It can never cause a turnover on downs.
- **PI after a QR or QT was already rolled** becomes a DEF 10 penalty with no automatic first
  down (see the rules profile).
- Accepting a penalty cancels the play, so a touchdown or safety gain no longer matters.
- A return-column penalty rerolls the return, then is accepted or declined by the offended team. It is marked from the return end, except an offensive foul after the return's midpoint is marked from that midpoint.

The project's worked example differs from the printed p. 9 example: a DEF 5 at the opponent 7
on third and five gives the opponent **4**, third and **2** (the half-distance rule), not the
opponent 5 and third and three.

## Not yet supported

Timing, kick and conversion penalties are handled by their engine procedures.
Return enforcement whose endpoint cannot yet be represented remains explicitly
disabled; declining continues the real result. See [turnovers](turnovers.md) for
end-zone return depth and offensive-recovery down/distance preservation.

## Tests

- `tests/test_penalty_yardage.py`: all 216 physical offensive rolls against all four table
  columns, boundaries, fixed, PI and variable distances, and enforcement.
- `tests/test_penalties.py`: reroll chains, offsetting, pre-snap, PI, Option and supplemental
  interaction, the reroll limit, and dice consumption.
- `tests/test_session_penalties.py`: pending safety, accept and decline, stale decisions, and
  cancelled scoring gains.
- A local-only smoke run of the private 2002 charts played 8,251 snaps with no errors.

## Decision labels

Penalty-decline buttons include the already prepared result (for example,
“Decline penalties: incomplete pass” or “Decline penalties: gain of 7 yards”).
Declining does not reroll that result. Interception/fumble labels identify the
known event/location and any remaining interception decision or recovery procedure;
they never predict a return or recovery that has not occurred. Kick/return
penalties likewise show the prepared distance or chart fact. These labels come
from the engine, not browser interpretation, and consume no dice or state changes.
Pending saves retain compatibility with the former generic decline wording.
