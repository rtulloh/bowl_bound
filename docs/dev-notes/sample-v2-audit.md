# Fictional sample v2 all-cell audit

Public/synthetic evidence only; no historical charts or private game logs.

## Scope and result

Both generated teams and all ten public bundle/provenance files were checked.
`tests/test_sample_teams.py` verifies byte-for-byte reproduction and ordinary
catalog loading; `tests/test_sample_playability.py` verifies the cell semantics.

- **1,680 entries:** per team, 270 offense, 270 defense, 90 supplemental,
  180 special-team and 30 PAT entries. Every required coordinate exists exactly
  once; source fingerprints and synthetic v2 provenance are consistent.
- All running columns reject PI, interceptions, incompletions and QR/QT.
  SOP/BLP redirects appear only in Option. Passing columns retain the legitimate
  passing outcomes. No variable-distance stress tokens remain in playable cells.
- Every numeric primary pairing has a net result within the fictional design
  bounds of −12..60 yards. Actual ordinary ranges are −7..18 for Cedar Valley
  attacking Harbor Tech and −8..18 in the reverse matchup. No −T3-style remote
  loss or turnover location is present.
- Every supplemental/special-team value is numeric and inside its declared
  column-specific demonstration bounds. PAT entries are booleans with both make
  and miss outcomes. Recovery ranges are nonempty, contiguous and proper subsets
  of the supported 10..39 offensive totals.

## Exact primary dice-weighted coverage

Enumerate all **216 offensive** and **36 defensive** physical combinations,
retaining face multiplicities, then aggregate identical totals. For each of
9 called plays × 6 defenses × both team directions, check every lookup pair:
**839,808 weighted primary combinations** (419,904 per attacking team).
Every result belongs to a supported family; no ordinary run resolves directly
to a pass-only event. Option passing redirects are intentional.

The family weights below are the same in each direction by recipe design;
numeric values differ. Plays and formations are weighted equally here, so this
is not an AI call-distribution report or a game-level probability forecast.

| Primary family | Weight per attacking team |
| --- | ---: |
| Ordinary numeric yards | 325,668 |
| Fumble | 23,724 |
| Penalty | 24,624 |
| Interception | 11,232 |
| Incomplete | 16,824 |
| Breakaway | 3,060 |
| SOP | 1,944 |
| BLP | 1,296 |
| QT | 9,504 |
| QR | 2,028 |
| **Total** | **419,904** |

This exhausts primary chart coordinates and weights, not every recursive branch
sequence or possible game state. Supplemental/return cells are audited individually;
branch resolution remains covered by the unchanged engine suites. Two complete
manual and four complete coached browser games with v2 charts passed the existing
clock/scoring/statistics/privacy/save-continuation checks. Numeric limits and broad
family-frequency checks are fictional sample design constraints, not changes to
Bowl Bound rules and not a claim of historically calibrated football statistics.

## Validation

- `.venv/bin/python -m pytest tests/test_sample_playability.py tests/test_sample_teams.py -q --tb=short`: **15 passed**, including the two additional all-cell/weighted audits.
- Production implementation full gate before those two test-only additions:
  `.venv/bin/python -m pytest --cov -q --tb=short`: **1,677 passed**, **92.63%**
  branch-aware coverage. No production/chart changes followed that run.
- `npm test` in `frontend/`: **101 passed**; `npm run build`: passed.
- `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS=<isolated-v2-synthetic-root> npx playwright test`
  in `frontend/`: **26 passed**, no retries.
- Ruff lint and formatting checks passed. No test skips added.

## Compatibility and deployment

The owner approved replacing the fictional charts and restarting the game.
Only the exact public sample allowlist was regenerated, after checking that those
files had no owner edits. IDs remain stable; recipe/source fingerprints increment
to v2. V1 saves need the unchanged v1 charts, retained in an ignored local backup;
they are not silently migrated by bypassing fingerprint checks. Historical data
is untouched. The local server was restarted and health/current build/new-game
creation were verified. No push or publication was performed.

Tested implementation: **f571840**. Final combined sample/decision/index checks:
**47 passed**. Ruff lint and all 192 Python-file format checks pass.
