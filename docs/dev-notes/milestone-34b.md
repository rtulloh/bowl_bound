# Milestone 34b — Recent-season chart expansion

Status: planned. Owner requested a separate ticket on 2026-11-05 to generate
more recent college seasons, probably working backward from 2025. Track
[DATA-037](issues/DATA/DATA-037.md); this does not expand the current Alpha 6
chart-release cohort or complete M34a calibration.

## Sequence and acceptance

Start with 2025, then 2024, 2023 and earlier years. Report source coverage gaps
and per-team exclusions instead of silently changing the order or quality gates.
Reuse the reviewed individual-play generation methodology, preserving source
hashes, terms/attribution review, generator configuration and accepted output
provenance. Keep raw caches, private reference charts and detailed audit evidence
outside publication and ordinary public tests.

Benchmark charts may be unavailable. Establish confidence from supported
real-season evidence, explicit source-fitted versus held-out comparisons, finite
chart diagnostics and deterministic multi-seed full-game/season audits. Reconcile
scoring, clock, statistics, traces and strict save/replay; report outliers and
limitations without claiming historical calibration from completed games alone.
Use year-appropriate team identities, conference/schedule/postseason metadata and
supported engine rules; expose approximations instead of inheriting 2007 BCS
behavior silently. Review each season before separately approving its release.

## Paydirt consultation

Reviewed local `tests/run_full_season.py` before this planning pass. Adapt its
seeded real-engine/CLI exercise, reconciled period/final/scoring totals and clear
statement that a generated schedule or postseason is a regression simulation.
Do not reuse 1983 NFL membership, schedule, tiebreakers, bracket, team data or
runtime imports. Bowl Bound's own generation contracts, college season metadata
and approved engine policies remain authoritative. No production behavior or
new-year charts are implemented by this planning ticket.
