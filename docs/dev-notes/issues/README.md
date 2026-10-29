# Issue Files

**Developer-only working record, not a player guide or a release promise.**

Use Paydirt's repository-local ticket workflow, with a required Bowl Bound milestone
assignment. Each issue lives in `<PREFIX>/<ID>.md`; the generated
[issue tracker](../issue-tracker.md) provides status and milestone views.
No external service or Paydirt runtime dependency is required.

## Prefixes

- **CLI:** terminal interaction, prompts, command shortcuts, help and terminal diagnostics.
- **UI:** web/browser interface only.
- **DEV:** tooling, packaging, security and development workflow.
- Keep rules, AI and data findings under their existing domain prefixes even when
  discovered through the CLI; use cross-references for shared causes.

### Terminal ticket reclassification (2026-10-27)

Owner requested separating CLI tickets from web UI tickets. Numeric suffixes are
retained for traceability; historical comments and commit history are not rewritten.
Each migrated ticket records its former ID in `previous-ids`. Current references
and future commit messages use the canonical CLI ID.

| Previous ID | Canonical ticket |
| --- | --- |
| UI-023 | [CLI-023](CLI/CLI-023.md) |
| UI-024 | [CLI-024](CLI/CLI-024.md) |
| UI-025 | [CLI-025](CLI/CLI-025.md) |
| UI-026 | [CLI-026](CLI/CLI-026.md) |
| UI-027 | [CLI-027](CLI/CLI-027.md) |
| UI-028 | [CLI-028](CLI/CLI-028.md) |
| UI-029 | [CLI-029](CLI/CLI-029.md) |
| UI-030 | [CLI-030](CLI/CLI-030.md) |
| UI-031 | [CLI-031](CLI/CLI-031.md) |
| UI-032 | [CLI-032](CLI/CLI-032.md) |
| UI-033 | [CLI-033](CLI/CLI-033.md) |
| UI-034 | [CLI-034](CLI/CLI-034.md) |
| UI-035 | [CLI-035](CLI/CLI-035.md) |

`retired-ids.yaml` maps old IDs to canonical ones. The creation script reserves
those old numbers so future web tickets cannot reuse them. Historical UI-023
through UI-035 references in append-only evidence refer to the CLI tickets above.
Do not add retired references to active `links`; use canonical IDs.

## File format

```yaml
---
id: UI-001
title: One-line description, at most 120 characters
status: open
priority: Medium
milestone: "19"
created-at: 2026-10-26
resolved-at:
closed-at:
tags: [reproduced]
links: []
commits: []
---
```

Follow front matter with `## Description`, `## Resolution / verification`, and
`## Comments`. Record reproducible evidence, expected behavior, acceptance checks,
and append-only timestamped comments (`--- YYYY-MM-DD HH:MM ---`).
Dates use ISO format. IDs must match the filename and prefix directory.
Links refer to other ticket IDs and must be mutual.

## Status and ownership

- **open:** work remains, including uncommitted implementations. Use tags such as
  `investigating`, `deferred`, or `reproduced` to distinguish evidence and readiness.
- **resolved:** a tested fix has been committed; record `resolved-at`, commit hash,
  tests and changed expectations. Await play-test confirmation.
- **closed:** a play-test audit confirms the issue no longer occurs; record
  `closed-at` and a timestamped `Play-test confirmation:` comment. Unit tests alone
  do not close gameplay or UI tickets. A duplicate, re-scoped, or wont-fix closure
  instead requires the matching tag and a documented reason.

Keep resolved/closed tickets. Reopening clears resolution/closure dates and adds an
explanation. Every ticket has exactly one target `milestone` from the
[canonical roadmap](../project-plan.md), including lettered milestones where needed.
Assignment is planned scope, not evidence that a milestone or fix has shipped.
A finding discovered after its original milestone ships belongs to the next relevant
follow-up milestone; do not silently reopen completed milestone acceptance.
Reassign with a timestamped reason if scope changes.

Priorities: **High** for incorrect gameplay or seriously misleading state/actions;
**Medium** for usability/accessibility barriers and missing verification; **Low**
for minor wording, formatting, or exploratory work.

## Maintenance

```bash
.venv/bin/python scripts/build_issue_index.py
.venv/bin/python -m pytest tests/test_issue_tracker.py -q
```

The test gate validates metadata, dates, milestone ownership, reciprocal links, and
index freshness. Check linked tickets during each milestone acceptance review and
record verification in the ticket as well as the milestone review.

Public tickets use synthetic examples only. Never copy historical chart values,
private play logs, session identifiers, saves, or detailed audit records into tickets.
The initial issues summarize the synthetic Chrome usability review; the user's kickoff
question is represented by a synthetic example, not their private trace.

## Create a ticket without OpenCode

Run `.venv/bin/python scripts/create_issue.py --help`. For example:

```sh
.venv/bin/python scripts/create_issue.py --prefix DEV --title "Synthetic example" \
  --milestone 19 --description "Describe a public-safe problem" \
  --acceptance "Verify with synthetic fixtures" --priority Medium --tag testing
```

Repeat --acceptance and --tag as needed. Absolute script/Python paths work from
other directories. The command validates against the index builder’s schema and
canonical roadmap, exclusively creates the next three-digit ID and regenerates
the index. It never overwrites a ticket; a competing creation advances the ID.
If indexing fails, it exits unsuccessfully and reports the preserved ticket path
so you can fix existing metadata and rerun build_issue_index.py. That builder
only regenerates the tracker; it does not create a ticket.
