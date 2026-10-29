# Turnovers and recovery chains

The engine resolves structured chart facts, never prose or substituted zeroes.
Fixed, DS, X and T1–T3 locations use the full-feature dice formula. Priority-selected
variable offensive and defensive distances roll independently, preserving source
facts and observed dice (`variable:offense` / `variable:defense`).

## Interceptions

The defense chooses return or incomplete pass. Declining consumes no return dice
and advances the down as an incomplete pass. Electing return consults the
interceptor's Interception Return column, except where the catch itself scores or
requires an end-zone choice. Choices block new snaps and apply exactly once.

## Fumbles

The location is applied before recovery. The fumbler rolls its recovery range.
Totals 17–19 for the fumbler or 37–39 for its opponent authorize an Interception
Return from the recovery spot. Return fumbles start another recovery chain,
bounded at 100 links; every actual recovery/return roll is traced.

An offensive recovery continues the original down/distance and statistical play
classification. A defensive recovery starts first-and-ten after any return.
If that returner fumbles and recovers its own fumble, it still starts a fresh
series at the final spot; recovery/advance does not consume a scrimmage down.
Its touchdown retains the defensive-return classification. An original-offense
own recovery short of the line to gain on fourth down is labeled
`turnover_on_downs`, not `offensive_recovery`.

## Goal lines, end lines and scoring (Basic VI-13)

Goal lines are 100 yards apart; each end line is ten yards beyond its goal line.

- In the original offense's end zone (including its goal line, before its end
  line), a defensive interception/recovery is a touchdown. An offensive fumble
  recovery is a safety. On or behind that end line the result is a safety, without
  an unnecessary recovery roll.
- In the defenders' end zone an offensive fumble recovery scores; a defensive
  interception/recovery offers touchback at own 20 or return.
- An interception on/beyond the defenders' end line is placed nine yards deep.
  A fumble there instead rolls the white-face sum for its live depth **before**
  the separate recovery roll (`end_zone_depth`, then `fumble_recovery`).
- End-zone returns subtract the actual depth. A return that never crosses its
  own goal line is a touchback; a return begun in the field and carried backward
  across its own goal line is a safety, as is an own-recovery return taken backward
  into the original offense's end zone.
- A return reaching the opposing goal line is a touchdown. Own-recovery advances
  retain the offensive touchdown classification. A return fumble uses its actual
  landing spot, even if still inside the end zone.

End-zone returns share ordinary return processing: penalties, no-change and
fumbles do not disable the entire Return choice. Scores use engine-owned home/away
order. Drive mode ends after scoring; regulation continues through conversions
and kicks as described in [the rules profile](rules-profile.md).

## Penalties and continuation

Declining a scrimmage penalty resumes its already-prepared turnover procedure
without rerolling lookups or committing a duplicate play.

An Interception Return penalty rerolls that column and offers the offended team
accept/decline. Defensive fouls are marked from the return end; an offensive foul
passing the midpoint uses that midpoint. End-zone origin is retained for numeric
enforcement. Accepted own-recovery return fouls replay the original down and keep
the original line to gain unless enforcement earns a first down. Only legal
advance, not stepped-off penalty yardage, contributes offensive statistics.
Unsupported end-zone penalty endpoints remain explicitly disabled with a reason;
decline still resumes the actual result. See [penalties](penalties.md).

## Verification

Synthetic suites: `test_turnovers.py`, `test_session_turnovers.py`,
`test_engine_hardening.py`, `test_variable_yardage.py`, `test_return_audit.py`,
`test_statistics.py`, `test_return_fumble_series.py` and `test_save_game.py`.
No historical charts are required.

The corrected return-series rules use replay profile `bowl-bound-m21-v1`. Saves
from the previous `bowl-bound-m19-v1` profile are rejected as incompatible before
team loading, rather than replayed under different down rules. No automatic
migration or deletion of private saves is performed.
