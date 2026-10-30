---
id: IMPORT-002
title: Refresh importer documentation drift and small robustness gaps
status: resolved
priority: Low
milestone: '25'
created-at: 2026-10-26
resolved-at: 2026-10-30
closed-at: null
tags:
- importer
- documentation
links:
- IMPORT-007
- IMPORT-009
commits: [d8c9d9c, 03ab1d8]
---

## Description

- docs/normalization.md:36-42 says errors include filename, bounds and original text, but
  `normalization.py:30-35,91-93` deliberately reports only the page and reason to keep private
  text out of logs.
- `tools/pdf_import/cli.py:33-34` tells users batch processing "arrives in Milestone 5d";
  the plan moved it to Milestone 25.
- `cli.py:177-179` restores previous files via `previous.decode("utf-8")` inside the rollback
  handler; a non-UTF-8 pre-existing file would abort the remaining restores and mask the
  original error.
- `metadata.py:84` defaults the metadata background to white without grid evidence, and
  `metadata._color` accepts only RGB triples while `cells._rgb` also accepts gray values.
- `scripts/build_issue_index.py:30-33` raises date errors without the ticket path.

## Resolution / verification

- Correct the two documents and the CLI message; add a test that the CLI help/messages do not
  reference retired milestones.
- Restore rollback bytes directly; add a synthetic rollback test with non-UTF-8 content.
- Unify color parsing helpers and record an explicit "no evidence" marker instead of white
  where appropriate; include the ticket path in index date errors.

Implemented in `d8c9d9c`, with help-output assertion follow-up `03ab1d8`.

- Baseline synthetic tests reproduced the non-UTF-8 decode failure, stopped rollback after a
  restore error, rejected grayscale metadata colors, defaulted no-fill metadata to white,
  echoed retired Milestone 5d, and omitted the ticket path from invalid-date errors.
- Rollback now passes prior bytes directly and attempts each restore/removal while preserving
  the original write exception. Tests cover non-UTF-8 existing data and an injected restore
  failure. Shared PDF RGB parsing now handles DeviceRGB and DeviceGray shapes in cells and
  metadata.
- Metadata with no measured fill uses three empty provenance RGB fields. Writers now emit
  team-file version 2; readers preserve compatibility with version 1 and reject the version-2
  marker in version 1 bundles. Normalized chart cells and PAT outcomes still require RGB.
- Corrected the normalization/privacy and bundle/schema documentation, removed the stale
  milestone wording from CLI errors, and made invalid ticket-date errors include the ticket
  path. Regenerated the two fictional sample team YAML files and their release hashes.
- Verification: the focused PDF/import/model/codec/issue/release test slice passed 404 tests;
  the updated 73-test bundle suite and 28 CLI tests passed. Ruff check, Ruff format check and
  `git diff --check` passed.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-30 00:00 ---
Resolved after test-first fixes, version-2 bundle coverage and focused regression checks. No
play-test is needed for this importer/data-format and development-tooling ticket; it remains
resolved pending the Milestone 25 acceptance review.
