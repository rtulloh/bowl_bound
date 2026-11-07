# Alpha 9 defensive-chart release preparation

Status: preparation only; no Alpha 9 charts or release accepted yet.

## Owner scope and bounded acceptance

The owner requests an experimental chart release without delaying publication for uncertain historical formation choices, exact designer formulas, or optional defensive breakaway allocation. Retain the approved 116 generated 2007 teams and two original fictional samples. Defer additional seasons and new defensive B placement. Preserve old previews, chart artifacts and immutable release tags. Alpha 8 is already public; use a new version.

The generator, independent audit and game validation workstreams will first freeze one coherent candidate. Required acceptance covers legal complete chart loading, explicit known/unknown provenance, physical probability mass and event budgets, current-engine state/statistics/clock/trace/save behavior, legal coaching actions, the established full regression gate and exact release packaging. Historical accuracy is provisional; reference chart replication and exact historical season outcomes are not acceptance conditions. Zero event budgets remain zero. Small budgets use a declared representable policy instead of impossible strict contrasts or manufactured events. Disclose remaining model and source limitations.

## Paydirt consultation

Reviewed local Paydirt `tests/test_release_chart_packaging.py` before release integration. Adapt consistent chart inventory and attribution across native entry points, and verify dynamically loaded backend dependencies. Do not copy Paydirt chart data, NFL policies, source licensing assumptions or packaging paths; Bowl Bound retains its exact approved manifest and no runtime dependency on Paydirt.

## Integration preparation

Public main baseline: `9f3041a0af7b9d5bb60018d7df0d611347ff023e`. Work occurs in a separate durable release worktree; the owner's original checkout and local previews remain untouched.

Existing version assertions were changed to Alpha 9 first: two expected failures against unchanged Alpha 8 package/launcher metadata, one unrelated license check passed. The coordinated package, frontend and lockfile versions then change together. Gameplay/save profile remains unchanged. The first attempted test interpreter lacked FastAPI and failed collection; the established complete Python 3.13 environment was then used. No collection failure is counted as behavioral evidence.

Final candidate identities, tested commits, commands, warnings, source/native acceptance and publication receipts will be recorded here before acceptance.

Preparation verification: isolated Python 3.13 development/web/PDF dependencies installed and `pip check` passes. `pytest -q tests/test_release_metadata.py tests/test_launcher.py`: 17 passed. Frontend uses Node 24.22.1: 158 unit tests and production build pass; clean installation audit reports zero vulnerabilities. Retain the upstream whatwg-encoding deprecation and jsdom environment performance advisory. An attempted nonexistent `tests/test_docs.py` command ran no tests; the actual documentation test files were then selected. Final integrated full regression is still required.
