# Milestone 39 — Analysis of penalized two-point tries

Required release follow-up, authorized by root during Alpha 6 validation on
2026-11-05. Track AI-039. Keep the separate web chart viewer/M38 work intact.

The current AI audit finds a legal first-and-goal try at an enforced penalty spot,
but the analysis factory insists every try begins at the two. Its exception occurs
before the sampled-action settlement guard and aborts a computer turn. The initial
116-game audit retains three aborts and is failed evidence, not release acceptance.
Private matchup details and charts remain outside this note and public tests.

Before this phase, consulted local Paydirt `paydirt/computer_ai.py:91–120`:
its try offense reads the engine's current `yards_to_go`, and its defense reads
engine-provided legal formations independently of stale clock state. Adapt current
engine facts as analysis inputs. Do not copy NFL formations, scoring, chart values,
two-point eligibility or runtime dependencies.

Write synthetic controls first, expand only the sandbox's valid goal-to-go domain,
retain invalid-input rejection, and verify unchanged previously valid analysis and
strict replay. This domain correction does not alter scoring/penalty rules or
previously successful policy streams; do not introduce a policy revision solely
to analyze a newly supported legal field position.

The first private audit's zero-fallback assertion also needs classification:
all observed flags occur during two-point analysis. A bounded one-action model can
explicitly fall back when a hypothetical penalty needs a new snap. Retain actual
fallback counts and evidence; do not turn failed samples into zero or ignore illegal
calls/aborts. Final cohort checks and tested commit references follow in release
acceptance; the initial failed audit is retained separately.
The bounded repeated-try valuation limitation remains tracked separately as
[AI-034](issues/AI/AI-034.md); this fix does not claim to resolve it.

## Implementation review and focused acceptance

The new synthetic file demonstrates 14 expected failures against the original
factory guard, with two passing controls. Ten cases cover both possessions at
five displaced first-and-goal spots. Four more use actual offensive/defensive
penalty enforcement on both sides, then analyze offense and defense and finish
the try. The controls retain explicit incomplete-sample/legal-fallback behavior
and deterministic initial-two-yard analysis plus strict save/replay.

Change only the factory's try-domain check: first down and distance equal to
the current goal distance. The existing malformed-state regression now uses a
non-goal-to-go distance instead of rejecting a legal first-and-goal at three.
The existing versioned offensive basic-call preference for displaced tries remains;
its stale factory-limitation comment is corrected. No policy stream is revised.

Focused checks: `ruff check` and `ruff format --check` for the changed Python files;
`pytest -q tests/test_penalized_try_analysis.py tests/test_coaching_try_evaluation.py
tests/test_session_scoring.py tests/test_overtime.py tests/test_overtime_extra.py`:
85 passed. Cumulative `pytest -q tests/test_coaching* tests/test_difficulty*
tests/test_penalized_try_analysis.py tests/test_session_scoring.py tests/test_overtime*`:
456 passed in 70.53 seconds. Repository-wide Ruff lint/format and `pip check` pass.
Complete release and renewed cohort acceptance follow.


## Release acceptance follow-up

Tested implementation commit: `e4bfa8b`. Current-engine/coaching audit: all 116
cohort games plus 12 additional games pass mechanical reconciliation and strict
midpoint/final replay, including all three formerly aborted fixtures; two complete
canonical results repeat exactly. Independent review reconciles 21,345 primary
snaps and all legal calls. The 53 flagged two-point comparisons are the separately
tracked bounded repeated-try valuation limitation (AI-034), not aborts.

Full local gate: 3,983 Python tests pass with 93.35% branch-inclusive coverage,
147 frontend tests/build/audit, 54 real-engine Chromium checks, repository Ruff
lint/format and dependency consistency. The exact 118-team isolated runtime passes
UI/assets and every-team snap/save/load. Release build/publication remains tracked
in the Alpha 6 note and DEV-072; overall historical calibration is not claimed.
