# Milestone 40 — Bounded full native catalog discovery

Track DEV-073, discovered during Alpha 6 native acceptance. The first pinned
Windows build succeeds, becomes healthy and returns the expected version, but
its first `/api/teams` request exceeds the smoke helper's legacy five-second
budget. Intel also builds successfully and fails at the identical request boundary.
Windows installer checks consequently do not run; this attempt is failed release
evidence. Apple Silicon's native job passes.

Reviewed local Paydirt `.github/workflows/release.yml` before this follow-up.
It supplies native build/installer orchestration but has no equivalent complete-
catalog HTTP smoke/deadline mechanism. Retain Bowl Bound's pinned strict native
acceptance rather than copying unpinned dependencies or optional installer failure.
The earlier reviewed Paydirt complete-season runner reinforces preserving complete
validation and surfacing failures; no NFL scheduling/rules/data are reused.

`TeamCatalog.teams()` loads and validates every chart/provenance bundle on each
listing. Health readiness does not perform that work, and warming the catalog
would not establish a cached fast path. This is a request-budget mismatch in the
release harness, not evidence of an engine or chart correctness failure. Do not
claim actual Windows discovery duration until the corrected native run measures it.

A self-contained synthetic HTTP fixture answers health/version immediately and
delays its two-team catalog for six seconds. Against the unchanged helper it
fails with the same `TimeoutError` at five seconds. The correction gives only
complete catalog discovery a 30-second bound and prints elapsed discovery time;
ordinary health/version/action/save/load and static-asset requests retain five
seconds. Exact set/count/problem checks and every-team snap/save/load remain.
No chart, application module, coaching policy or engine behavior changes.

The six-second fixture passes after the correction. Focused smoke/release/native/
installer regressions: 116 passed in 10.26 seconds. Repository Ruff lint/format and
dependency consistency pass; 22 issue/player-doc checks pass. The complete local
gate passes: 3,984 Python tests in 876.03 seconds, 93.35% branch-inclusive
coverage; 147 frontend tests, production build and dependency audit; 54 real-engine
Chromium checks in 4.1 minutes. No tests were skipped or assertions weakened.
The application, coaching, frontend, chart resources and release manifest are
byte-identical to the accepted `fc9998c` candidate, so its 128-game current-engine
audit remains applicable. A downloaded first-candidate Apple Silicon app also
passes the corrected complete 118-team snap/save/load smoke, with catalog
discovery measured at 3.01 seconds. This is supporting evidence, not final
artifact acceptance. The failed Windows/Intel run is retained. Publication still
requires a fresh pinned build of all three final native jobs plus Windows
install/registry/game/save/uninstall acceptance and final asset review.

## Final acceptance

Committed correction `9a2897f` is retained byte-for-byte in corrected chart source
`a95ded6`. All three final native jobs in [run 42099569172](https://github.com/rtulloh/bowl_bound/actions/runs/42099569172)
pass without weakening assertions. Catalog discovery is 3.53s arm64, 14.26s Intel,
6.69s portable Windows and 6.74s installed Windows. Windows actual install/registry/
game/save/uninstall preserves an unrelated file. Final downloaded arm64 passes
independently locally (2.81s discovery). The complete 118-team checks remain;
ordinary requests retain their five-second deadlines. DEV-073 is resolved pending
owner download/play-test confirmation. Alpha 6 is public Latest, with all eleven
asset digests and the real repository Releases panel verified. See the
[publication receipt](release-alpha6.md#published-alpha-6--2026-11-05).
