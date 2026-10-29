# AGENTS.md — Bowl Bound Development Guide

This guide is adapted from Paydirt's development guidance for the standalone Bowl Bound project. It replaces Paydirt-specific NFL, Excel-import, release, and full-season requirements with Bowl Bound-specific rules, PDF-import, and privacy requirements.

## Project overview

Bowl Bound is a Python implementation of the Bowl Bound college-football board game. Its game engine is the authoritative source for all football decisions. The web application displays engine-provided state and outcomes; it must not interpret chart values or reimplement rules.

The project is intentionally separate from Paydirt. Reuse selected ideas or components only after verifying they fit Bowl Bound. Do not add a runtime dependency on the Paydirt repository.

The canonical roadmap is [docs/dev-notes/project-plan.md](docs/dev-notes/project-plan.md). Work in independently testable milestones, and stop for review and a commit at every completed milestone.

## Required workflow

### Consult Paydirt before every phase or milestone

At the start of every phase or milestone, consult the local Paydirt repository
for relevant implementation, architecture, tests, documentation and lessons learned
before planning or implementing the work. Record the references reviewed and the
applicable findings in the Bowl Bound phase/milestone notes, including what will
be adapted or deliberately not reused and why. If Paydirt is unavailable or has
no relevant material, document that limitation explicitly rather than skipping
this step silently.

Treat Paydirt as design input, not Bowl Bound authority: verify every reused idea
against Bowl Bound rules, architecture and privacy requirements. Do not inherit
NFL behavior, copy private team data or add a runtime dependency on Paydirt.

### Test-first behavior changes

For every bug fix and new behavior:

1. Write self-contained tests first, using synthetic charts and fixtures.
2. Run the tests against the unchanged implementation and demonstrate the expected failure where meaningful.
3. Implement the smallest correct change.
4. Run focused tests and relevant cumulative regressions.
5. Explain every changed expectation; never weaken assertions or add skips merely to pass.

For documentation, metadata, scaffolding, or initial file creation, run applicable existing checks without inventing artificial behavioral tests.

If a meaningful regression cannot be written, explain the limitation and obtain approval before changing production behavior.

### Milestone commits

Each project-plan milestone must end with:

- documented acceptance criteria satisfied,
- a focused test run,
- applicable cumulative checks,
- documentation updates, and
- a dedicated commit using `milestone X: <description>` as the subject, replacing X with the completed milestone number (for example, `milestone 2: define initial rules profile`).

Do not mix unrelated work into a milestone commit. Do not start the next milestone until the current milestone is reviewed and committed.

### Issue tracking

Create or update an issue for every reported problem when it is reported, even if
it is fixed immediately during the same work session. Do not leave quick fixes
untracked.

Track findings using [ticket conventions](docs/dev-notes/issues/README.md) and the
[generated issue tracker](docs/dev-notes/issue-tracker.md). Assign each ticket a
canonical project-plan milestone and keep evidence synthetic/public-safe. Review
assigned tickets during milestone acceptance; record tested commit references before
marking resolved, and play-test confirmation before closing. Regenerate the index
with `python3 scripts/build_issue_index.py` whenever tickets change.

## Privacy, team data, and source provenance

Historical team PDFs, converted team data, detailed import reports, game saves, and local play/audit logs are private by default.

- Keep private material in ignored paths such as private-data/. Converted historical team files live under seasons/<season>/<team>/team.yaml with CSV charts and remain ignored/unpackaged. Only the original fictional Cedar Valley and Harbor Tech bundles under seasons/2007/ and their synthetic provenance are narrowly allowlisted as public CC0 sample content. With explicit owner approval on 2026-10-29 (DEV-042), this includes exactly those two teams' original fictional roster.json and roster-sources.md files; all other rosters remain private and excluded.
- Never commit, publish, or export historical charts without separately established rights and explicit current approval. The owner directed on 2026-10-26 that Ohio State and Miami remain unpublished in game/release packaging; preserve local charts but exclude them from GitHub release artifacts and runtime bundles (see docs/ATTRIBUTION.md and DEV-012). Release packaging must use an exact sample allowlist, never copy the entire local seasons/ tree.
- Public unit tests use only synthetic charts and fixtures.
- Local import verification may use OSU/Miami data, but must live outside ordinary test collection and must not make CI depend on private files.
- Preserve PDF source provenance: source hash, filename, page, position, original text, and background color.
- Never silently convert an ambiguous or missing PDF cell into a zero-yard result.

The PDF importer is a development tool, not a runtime engine dependency. Initially support only documented digitally generated layouts; fail clearly on unsupported scans or layouts.

## Architecture principles

### Engine is source of truth

1. All Bowl Bound rules, state transitions, timing, scoring, statistics, penalties, and overtime behavior live in the engine.
2. The API adapts engine state; it does not decide game behavior.
3. The frontend displays labels, legal actions, results, and traces provided by the backend.
4. Commentary and result descriptions originate in the engine.
5. AI selects from legal engine actions but never duplicates rule enforcement.

Avoid these anti-patterns:

- Parsing prose in the UI to determine football results.
- Recalculating field position, possession, down, distance, or score in the UI.
- Interpreting raw chart colors or strings outside importer/chart-normalization code.
- Giving the AI hidden state or chart behavior different from human-controlled play.
- Subclassing a large Paydirt engine and scattering Bowl Bound exceptions through inherited NFL behavior.

### Separation of chart processing from rules

- **Importer:** PDF geometry, text, colors, source evidence.
- **Chart model:** normalized semantic cell facts and validation.
- **Engine:** dice, priority resolution, supplemental outcomes, rules, state, and statistics.
- **Presentation:** display only.

A cell's PDF color is converted to an explicit fact at import time. The engine consumes the fact, not PDF rendering information.

## Bowl Bound implementation rules

- Use Bowl Bound exact dice distributions: enumerate all 216 offensive and 36 defensive combinations in tests.
- Preserve both the called play and resolved play classification, especially for Option to SOP/BLP, B, QR, and QT branches.
- Keep chart traces structured and complete: show consulted rolls/cells without inventing rolls that did not occur.
- Implement penalties, timing, optional rules, and overtime from an explicitly approved Bowl Bound rules profile. Do not inherit NFL behavior by default.
- Retain imported source tokens such as DEF5X in provenance; apply Bowl Bound interpretations through named rules policies.
- Treat advanced options as separate, documented, testable milestones. Unsupported options must remain unavailable rather than partially simulated.

## Style and organization

- Python 3.10+ and full type hints for function parameters and returns.
- Use dataclasses for simple data models; use enums for bounded rule concepts.
- Classes use PascalCase; functions and variables use snake_case; constants use SCREAMING_SNAKE_CASE.
- Use relative package imports.
- Prefer specific exceptions and actionable error messages; never use bare except.
- Use Google-style docstrings for public classes/functions where behavior is not obvious.
- Keep tests under tests/, mirroring production modules where practical.
- Keep maintained guidance under docs/; development notes and investigations belong only in docs/dev-notes/.
- Keep README.md concise and link to detailed canonical documents.

## Validation expectations

Until project tooling is created, document the exact commands run in each commit summary. The future full regression gate will include, as applicable:

- Python unit and integration tests with coverage of at least 75% (`pytest --cov`; branch coverage, enforced by `fail_under` in pyproject.toml),
- linting and formatting checks,
- importer synthetic-fixture tests,
- backend/API tests,
- frontend unit tests and production build,
- browser tests using the real engine,
- deterministic complete-game simulations, and
- AI play-selection audits.

A completed game is not sufficient evidence by itself. Reconcile scoring, state transitions, clock behavior, statistics, and structured traces. AI validation must review call distributions, repetition in comparable situations, and legal-decision fallbacks, not merely final scores.

Before any push, run the established full regression gate for the project. Do not hide skips or warnings; report them clearly.

## Documentation maintenance

Update documentation in the same change as any modification to gameplay, chart semantics, importer format, API contract, AI/coaching, controls, dependencies, packaging, or installation. If no documentation update is needed, state why in the change summary.

When changing documentation links or structure, update references and verify examples against synthetic data or authorized public materials.

## Releases and publication

- Do not add a GitHub remote or publish project material without explicit approval.
- Review tracked files and history for private charts, PDFs, reports, and saves before publication.
- Preserve release tags as immutable history; increment rather than delete/reuse a tag.
- Use synthetic demonstration teams if historical team-chart distribution rights remain unresolved.
