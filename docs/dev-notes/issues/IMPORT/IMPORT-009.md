---
id: IMPORT-009
title: Finish Milestone 25 acceptance and merge the parked batch importer
status: resolved
priority: High
milestone: '25'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- importer
- milestone
- validation
links:
- IMPORT-002
- IMPORT-003
- IMPORT-004
- IMPORT-005
- IMPORT-006
- IMPORT-007
- IMPORT-008
commits:
- 8f6f759
- f9a31b9
- d8c9d9c
- 03ab1d8
- 8767ec2
- d1a43cb
- 89c4308
- 95cbe68
- e583902
- 0f050eb
- 24eae29
- a052138
- 4c81fa6
- 824b0c6
- 28169cd
- b0ad58d
- b1e4b44
- 7da0b51
- a865eb5
- 3db98a5
- e573c74
---

## Description

Integrate the repaired batch importer onto the public main lineage and close Milestone 25 with reproducible acceptance evidence. The parked draft is not complete until all milestone tickets are reviewed, documentation is current and the dedicated milestone commit exists.

## Resolution / verification

- Review every open Milestone 25 ticket, require tested commit references before marking resolved, and keep unresolved scope explicit.
- Run focused batch/importer tests, the enforced release/importer coverage checks, the full Python/frontend/browser gate and any private local verification separately reported.
- Record Paydirt references, changed expectations, synthetic evidence, privacy review and exact commands in a Milestone 25 note under docs/dev-notes/.
- Merge the completed work without private PDFs, reports or historical teams; regenerate the issue index and verify all links.
- Create the dedicated commit with subject milestone 25: support batch team PDF imports only after acceptance criteria pass.

### Acceptance evidence — 2026-10-30

- Selectively integrated the reviewed batch-import draft and its fixes on the current public
  lineage. The parked branch predates Milestones 6–24, so it was not merged wholesale.
- All linked Milestone 25 tickets are resolved with tested commit references. Their status
  remains resolved because owner play-test confirmation is still pending.
- Full Python regression and branch coverage:
  `.venv/bin/python -m pytest --cov --cov-report=term-missing -q` — 2,548 passed,
  93.48% coverage (75% minimum).
- Quality checks passed: `ruff check .`, `ruff format --check .`,
  `.venv/bin/python -m pip check`, and `git diff --check`.
- Frontend checks passed: `npm ci --ignore-scripts`, `npm test` (122 passed, 16 files),
  `npm run build`, and `npm audit` (zero vulnerabilities).
- Real-engine browser tests passed: 33 tests using synthetic fictional teams via
  `BB_E2E_SEASONS=/private/tmp/bb-m25-integration-e2e-seasons npm run test:e2e`.
- Test fixtures were corrected where integration surfaced inconsistent PAT provenance,
  and where an engine-only negative variable multiplier was incorrectly represented as
  CSV input. Assertions were not weakened. The details and commands are recorded in
  [the milestone work log](../../milestone-25.md).
- No MaysFootball or other historical chart files, converted teams or reports were used.
- Dedicated milestone commit is created after this acceptance record.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 00:00 ---
Acceptance gates passed and the work log, project plan, ticket evidence and generated issue
index are updated. Milestone 25 is ready for owner review; retain resolved status until
play-test confirmation and do not close yet.
