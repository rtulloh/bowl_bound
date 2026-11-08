# Fixed punt / fair-catch commitment contract

Status: bounded implementation reviewed following `a9007c32`; DATA-055 remains open.
The acceptance below covers fixed numeric punts and fair catches only.

## Authority and actual gap

[The approved rules profile](../rules-profile.md#basic-special-team-resolution-milestone-13)
permits fair catch or return of unmarked punts. Basic VI-5 (printed p.9 / PDF12),
VI-11 and VI-13 (printed pp.11–12 / PDF14–15) govern the punt's measured distance,
no-return markers and goal/end-line boundaries. The local rule PDF has SHA-256
`599b1366b77fb5c17e01e510f0e0e78b92aba505aa57880bb95de7f024a7e690`.
The observer uses typed facts and independently transcribed arithmetic, never the
engine's special-team resolver, descriptions, formatted chart strings or claimed
report outcome as its expectation oracle.

The retained 34-wrapper diagnostic inventory has 196 final punt-fair-catch reports
without a checked terminal handler. This is an event label census, not eligibility
or an accuracy percentage. Many other reports remain unknown because of prior
unqualified chains. A checked new endpoint must not erase an earlier unknown or
reanchor state/clock continuity. The 34 inputs are re-audited read-only after
synthetic REDs; no new historical games are part of this bounded slice.

## Population and causal graph

Start with normal drive or regulation scrimmage, `kick("punt")`, and one fixed
nonnegative numeric punt cell with no variable, penalty, marker, OOB or unsupported
modifier. The actual pinned row must belong to the original possessing/kicking
team's `special_teams/punt` column, use the one newly consumed offensive draw and
physical total, and precede the final decision. Require zero defensive/priority/
additional lookup exposure. All required typed capture, indexed history and raw-v2
row linkage/data agreement prerequisites remain enforced before this component.
Inventory identity establishes agreement only, not original chart/source truth.

For original yards-to-goal G and flight K, the landing is L=G−K in the original
kicker's orientation. Admit only 1≤L≤99. The receiving side is the opposite side;
its resulting yards to goal are 100−L, down one and distance min(10,100−L).
Synthetic controls explicitly cover L=1 and99, both possessions and different
original downs/distances. L=0/−1/−10/100, dead/marked punts, redirect FG/KO,
blocked/fumbled/variable/penalty results remain unknown in this first slice,
never a guessed zero, return or field-goal attempt.

The kick command creates a pending receiver chooser with exactly one strictly
enabled `kick:fair_catch` and `kick:return`, unique IDs and correct side/label.
It commits no log row, credit, boxes, scoring or field change. Its returned pending
report has the original field, excluded null-owner zero credit, Punt called and
resolved labels, no formation, no fixed report yardage and eleven false timing
facts. Bind this creating command, retained original field, draw/row and pending
snapshot to the same actual capture object. A restored pre-window pending object
lacks the causal anchor and stays unknown. No report number is treated as an index.

The later `decide("kick:fair_catch")` must match that pending endpoint and strict
menu, consume no draw/request/row/priority, append exactly one fresh indexed
report (not any prior observed or charged ID), and end the pending decision.
Independently derive the receiver's field and full excluded-zero credit. Check
Punt called/resolved, supported/nonpending/null reason, symbolic report yards None,
original/final fields, both complete statistical boxes and score/scoring ledger.
The final serialized timing facts are change_of_possession true and the other ten
false. These format facts do not themselves prove elapsed time.

Derive eligibility from the original typed command/cell and graph before reading
claimed final outcome/credit; a wrong claimed class cannot escape as unsupported.
Missing, disabled, duplicate, stale, foreign-object or wrong-side choices refuse.
The actual return choice remains explicitly unknown here, while global evidence
integrity and no-reanchor taint remain enforced. Report facts are checked before
unsupported later period continuation is left unknown.

## Local clock and continuity

The approved [shortest standard timing](../rules-profile.md#standard-timing-matrix)
uses ten seconds for change of possession. The first kick may commit a prior
deferred charge; that is not a charge for this pending punt and must not be
confused with it. For the final choice, use its supplied pending clock and prefix,
normal regulation with remaining>10, no prior pending timing/modifier/OT/untimed/
timeout context. Require strict quarter/remaining/budget and home/away mirrors at
both pending endpoints and after; immutable ledger prefix plus exactly one new
standard requested/elapsed ten-second charge referring to this fresh report ID.
Drive/near-period/unsupported clock contexts stay clock_unknown. This command-local
proof does not clear generic clock-chain taint or establish an initial clock.

Only an independently checked live scrimmage endpoint may feed same-object state/
box/score continuity, conditional on an untainted prior endpoint. Unknown period
continuation, return, failed or foreign command cannot reanchor. Existing earlier
capabilities and assertions remain unchanged. New source/helper bindings join
CLI before/after checks; late dependency changes invalidate current flags/details
while preserving explicitly labelled initial diagnostics.

## Meaningful synthetic controls and limits

Before implementation, retain missing-capability positives separately from actual
ignored corruptions: wrong owner/landing/down/distance, summed/flipped coordinates,
credit/type/owner, both box deltas, score/ledger, called/resolved/format/timing,
premature pending credit/append, wrong row owner/column, disabled/duplicate menus,
extra return/recovery/defensive draw, reused report ID, foreign/restored pending,
ledger prefix/seconds/reference/live clock and contradictory timeout mirrors.
Exercise all 216 physical offensive faces with literal patterned punt distances,
not uniform totals. A numeric return control remains unknown; it is not silently
accepted as a fair catch. Marked/end-zone/complex populations retain exposure.

Per-choice save/reload is separately collected by the implementation lead's
opt-in helper with explicit actual-object resume handoffs. These old wrappers'
aggregate replay flags cannot reconstruct addressed save evidence for the 1,042
observed nonclock mandatory decisions.
No complete event, source, fixture, historical fit or full DATA-055 claim follows.

## Paydirt consultation

Reviewed local `tests/test_punt_roll_metadata.py`, `tests/test_punt.py` and
`tests/test_punt_return_chains.py`. Adapt the separation of the original punt
roll from later return/recovery draws, mirrored-side controls and retained dice
on early-return paths. Do not reuse its mocked resolver/string expectations,
NFL/coffin-corner coordinates, penalty/recovery/clock rules, private charts or
runtime dependency. Bowl Bound's typed facts and approved rules govern.

## Bounded acceptance

Synthetic regression tests enumerate all 216 physical offensive faces and retain
23 original ignored-corruption REDs separately from eight missing-capability
cases. Strict source/module/helper identity and stale-current detail controls join
the CLI. Pending endpoints may feed conditional same-object continuity only when
independently checked; earlier unknown chains never reanchor.

The frozen cumulative passes 2,216 checks in 515.43 seconds before a narrow
period-boundary follow-up. That follow-up retains two meaningful REDs: a valid Q2
timeout reset was falsely refused, and a near-period report ID could collide with
a charged prefix. The fix checks charged identity before period UNKNOWN and checks
after-timeout mirrors only for a qualified nonperiod endpoint. All initial and
pending mirrors remain strict. Final related regressions pass 177 checks in 47.62
seconds, including the physical-face loop; independent review passes the five
follow-up controls. These overlapping results are not described as a new full
2,221-check run. Nineteen production files pass static checking without ignores.

Read-only re-audit of the 34 retained wrappers preserves 6,419 reports and checks
394 pending punt creators, 194 terminal report facts, 192 live fair catches and
192 local clock charges; two later period continuations remain clock-unknown.
Other retained unknown returns and tainted chains are not promoted. The diagnostic
linked terminal census becomes 5,320 checked subjects and 1,099 unknowns, not an
accuracy percentage. The 1,042 old mandatory decisions still lack addressed save
evidence; the separate opt-in capture helper must provide that evidence in future
qualified runs. No engine, chart, capture producer or historical game changed.
