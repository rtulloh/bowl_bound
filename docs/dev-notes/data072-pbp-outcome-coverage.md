# DATA-072: PBP outcome coverage and scramble classification

Milestone 34b; linked to DATA-069. This is an isolated, untested candidate, not a
replacement cohort. The reviewed research candidate was transplanted onto
`origin/main` at `ca11f76` on source-only branch
`fix/data072-scramble-precedence`. The tests-only upstream checkpoint is
`88da3ae`. Published charts and immutable releases remain unchanged.

## Findings

An independent read-only census verified all 580 manifest pins for the 116
published generated 2007 teams. It counted normalized chart facts and the
authoritative initial priority result in all 6,264 self offense/defense
formation/call contexts. This census calls `resolve_cells`, which consumes no
dice; it ran no games, supplemental replay, generation or test suite. Detailed
rows and source pins remain ignored under
`private-data/data072-2007-outcomes-v1/` in the isolated worktree.

| Category | Encoded primary OFF: teams present / 116 | Encoded DEF: teams present / 116 |
| --- | ---: | ---: |
| Numeric gain | 116 | 116 |
| Numeric loss | 116 | 116 |
| No gain | 116 | 116 |
| F | 116 | 0 |
| INT | 116 | 6 |
| Incomplete | 116 | 54 |
| QR | 2 | 0 |
| QT | 116 | 24 |
| B | 0 | 0 |
| SOP / BLP | 0 / 0 | Not legal DEF instructions |
| Offensive penalty | 116 | 0 |
| Defensive penalty | 70 | 0 |

Penalty side is independent of the chart containing its instruction. Both sides
are currently emitted on OFF from observed side/distance evidence; absence from
DEF is not absence of a defensive penalty procedure. QR occupies seven primary
call columns with summed printed physical mass 11/216 across those columns;
this sum is not a per-play cohort probability. Initial priority selects QR in
42 contexts. It selects F in 5,694 contexts, INT/incomplete/QT in 2,784 each,
offensive penalties in all 6,264 and defensive penalties in 3,660. These are
presence counts, not historical rates. No B/SOP/BLP in primary or defensive
sources means those branches are unreachable here; available supplements do
not establish triggers.

The initial priority census does not complete supplemental, recovery, return,
penalty acceptance/decline/repeat, state clipping or statistical procedures.
Selected F/INT/P instructions remain pending, not zero-yard snaps or completed
turnovers. The census therefore does not certify the full requested coverage.

There are distinct causes, requiring distinct remedies:

- `generate.py:937–940,1023–1035` can emit SOP/BLP when classified Option records
  explicitly resolve to calls 7/8. The classifier requires explicit narrative
  evidence; lack of a label is unknown, not proof of zero historical branches.
- `generate.py:1015–1020` emits B only for a tail compatible with shared B support.
  Direct numeric long gains do not make that instruction reachable. A new B
  representation needs joint body/tail accounting, not an extra independent
  gain event.
- `generate.py:1279–1300` has no defensive-F category. Adding raw defensive F to
  existing offensive F rates would double count pressure without a joint model.
- Small positive requested probabilities can round to zero under available
  physical weights. Requested, encoded and priority-selected mass must remain
  separate; a silent presence flag is insufficient.
- A concrete source classifier bug can also erase genuine scramble support.

## Narrow corrective candidate

For a synthetic row with `rush=True`, `qb_scramble=True`, `pass=True` and seven
observed rushing yards, the old `classify_espn` pass branch precedes rush and
produces `incomplete` with null yards. This changes both NCAA attempt/yard
accounting and the source pool that can produce QR. The candidate gives an
explicitly annotated rushing scramble precedence over generic pass flags,
after kicks, sacks and interceptions. Explicit completions preserve their old
classification. Unknown scramble flags and generic overlap preserve legacy
behavior; the patch does not guess scrambles from play length or direction.

Rows taking the corrected branch carry
`bb-pbp-scramble-precedence-v1`; legacy family-v2 and legacy-v1 event files remain
loadable. Cached normalized events are not silently rewritten. There is no
claim that every absent QR in the released cohort comes from this defect;
source incidence must be measured prospectively.

Synthetic tests were written before the associated implementation changes for
overlapping `pass` and `pass_attempt`, preserved rushing totals, sack/INT and
completion precedence, unknown-support behavior and policy roundtrip. A
classification-to-generator case asserts actual primary QR emission and its
requested source probability. The existing no-fabrication test is unchanged.
No tests, lint, formatting, type checks or local regression were executed,
following the owner's explicit upstream-only direction. The subsequent upstream
tests-only run [44786384688](https://github.com/rtulloh/bowl_bound/actions/runs/44786384688)
at `88da3ae` demonstrated the expected red: 3 failed, 4 passed, 124 deselected
in 0.33 seconds. Both overlapping pass flags produced `incomplete`/null yards;
the classification-to-QR case failed on the same lost rush evidence. Protection
cases passed. Corrected checkpoint `33b7c00` stopped before the focused step in
[44786642123](https://github.com/rtulloh/bowl_bound/actions/runs/44786642123):
the mandatory research runtime guard rejected changed attested source bytes.
The focused step was moved before that unchanged mandatory guard to obtain
diagnostic test evidence. Full-gate acceptance requires a separately reviewed
prospective source-attestation decision; prior normalization/calibration receipts
are not renewed by this fix.

## Required upstream verification

Root authorized the source-only upstream path after independent static review
found no confirmed blocker. The Tests workflow now runs seven focused synthetic
cases before its unchanged full gate. Preserve the tests-only red checkpoint
and subsequent candidate green logs. Candidate commands include:

```sh
python -m pytest tests/chartgen/test_evidence.py tests/chartgen/test_generation.py -q
python -m pytest tests/test_issue_tracker.py -q
ruff check tools/chartgen/evidence.py tests/chartgen/test_evidence.py tests/chartgen/test_generation.py
ruff format --check tools/chartgen/evidence.py tests/chartgen/test_evidence.py tests/chartgen/test_generation.py
pyright tools/chartgen/evidence.py tests/chartgen/test_evidence.py tests/chartgen/test_generation.py
```

The focused/cumulative selection and established full upstream gate must be
reviewed before execution; `test_generation.py` contains existing synthetic
game/refinement cases. No historical research games are authorized by this note.
Issue-index generation is metadata maintenance, not a test result.

## Full vocabulary and cohort replacement remain open

The owner requires gains/losses/no gain, F, INT, incomplete, QR, QT, BLP, SOP,
offensive and defensive penalties and B to be meaningfully supported by both
generators. This patch addresses one real classification loss; it does not
satisfy that broader contract or close DATA-072. Require legal placements
(SOP/BLP only offensive Option), disjoint locks, explicit requested/encoded/
selected/procedure receipts and a synthetic complete-vocabulary fixture. An
observed zero must stay factual zero. Any mandatory small support floor must be
separately labeled AUTHORED, jointly budgeted with OFF/DEF/redirect contributions
and checked against unchanged source targets. Incompatibility must fail with a
named coverage/fit conflict. No arbitrary all-column filling or modern rate
transfer is justified.

Before regenerating or replacing the 2007 cohort, review a prospective bounded
contract: source/cache and classifier hashes, all 116 team identities and source
scopes, source-incidence/unknown counts, profile/support-prior version, exact
finite mechanism/procedure coverage, fixed rules and coaching context, metrics,
per-team and pooled tolerances, fixture scope, screening/confirmation sample and
unused seeds, resource cap and stop conditions. Measure the published baseline
and candidate on matched fixtures; reconcile source/event accounting, statistics,
scoring, clock, traces and replay. Preserve failed settings. Require independent
regeneration/hash reproduction and the applicable upstream full gate. No new
support prior, historical rate, changed tolerance, chart replacement or release
publication is selected or authorized here.

## Paydirt design input

Reviewed local Paydirt `docs/chart-validation.md:478–488`: separate weighted
initial resolution, conditional/pending measures and stateful qualification;
preserve source/freeze identities. Reuse those boundaries, not its NFL rules,
token legality, private cells or runtime code. Bowl Bound's own classifier,
priority resolver, NCAA statistical credit and 216/36 physical dice remain
authoritative.
