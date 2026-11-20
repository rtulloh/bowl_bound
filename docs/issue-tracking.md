# GitHub issue tracking

[GitHub Issues](https://github.com/rtulloh/bowl_bound/issues) is the source of truth
for bugs, improvements and planned work. Create or update an issue when a problem
is reported, including quick fixes. Search existing issues before creating duplicates.
Do not create repository-local ticket files or regenerate a local issue index.

Each issue needs a clear problem, expected behavior, public-safe reproduction or
evidence, acceptance criteria, canonical roadmap milestone, and exactly one
priority label: `priority:high`, `priority:medium` or `priority:low`. High means
incorrect gameplay, data loss, unusable installation or another serious blocker;
Medium covers ordinary functionality and usability; Low covers minor polish and
exploratory improvements. Reassess priority when evidence or impact changes.

Record implementation commits, checks and remaining limitations in the issue.
A tested implementation awaiting owner play-test stays open and explicitly says
so; close only when applicable acceptance and play-test confirmation are complete.
Preserve prior evidence when scope or status changes. Repository labels carry
priority independently of optional GitHub Project fields.

Historical charts, PDFs, saves and detailed audits remain private: link only
public-safe summaries and synthetic examples. Do not upload private evidence to
GitHub issues or comments.

## Migration

On 2026-11-20 the owner migrated 340 local tickets: 123 open, 179 resolved and
38 closed. Locally resolved tickets remain open pending their confirmation
requirements. Legacy IDs such as DATA-069 remain in migrated titles for search.
Local files were removed only after all 340 ticket hashes matched the migration
report, with complete imported history and no pending closures. Git history and
GitHub records retain the previous tickets. Historical notes may quote retired
commands as evidence; those commands are no longer the current workflow.

Paydirt consultation: reviewed its `AGENTS.md:390–409` (GitHub canonical tracking with an offline
fallback) and the owner-run
`scripts/migrate_github_issues.py` report schema. Adapt the explicit repository,
source identity and preserved-history mapping; do not copy game behavior or add
a runtime dependency. Cleanup is tracked in [GitHub #343](https://github.com/rtulloh/bowl_bound/issues/343), milestone 48.

Unlike Paydirt’s fallback, Bowl Bound retires local ticket creation entirely at
the owner’s request. Targeted cleanup verification found no remaining active
CI/tool/test dependencies on the retired scripts. No full local regression was
run for this documentation/tool retirement.

Migration checks: all 340 report entries have complete imported history and no
pending closures. All 290 remaining Markdown issue-detail links resolve to a
report-mapped GitHub issue or the migration follow-up (#343). No relative
Markdown links remain into the deleted ticket directory. `git diff --check`
passes. Existing historical command transcripts remain evidence, not instructions.
