---
id: IMPORT-002
title: Refresh importer documentation drift and small robustness gaps
status: open
priority: Low
milestone: '25'
created-at: 2026-10-26
resolved-at: null
closed-at: null
tags:
- importer
- documentation
links:
- IMPORT-007
- IMPORT-009
commits: []
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

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.
