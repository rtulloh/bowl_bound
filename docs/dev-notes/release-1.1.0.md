# Bowl Bound 1.1.0 release preparation

Status: planning only, 2026-11-15. Not built or published. Owner selected
**1.1.0** as the next release target. Planned immutable tag: `v1.1.0`.

This release is expected to deliver explicit cross-season web matchups
([Milestone 44](milestone-44.md)). Recording the target does not change version
metadata, charts, rules, save schema, tags or release assets, and does not claim
that any Milestone 44 acceptance criterion is complete.

## Scope

- [UI-070](issues/UI/UI-070.md): independent home/away year and team selection,
  season-qualified identities, backend-provided home-season rules visibility,
  actionable unsupported-profile errors and save/load preservation.
- [UI-071](issues/UI/UI-071.md): the setup UI design in
  [cross-season team selection design](cross-season-team-selection-design.md),
  with the owner-reviewed static preview at
  [mockups/cross-season-setup.html](mockups/cross-season-setup.html).
- [UI-009](issues/UI/UI-009.md): season-qualified in-game team labels, which
  cross-season matchups make necessary for same-school/different-year games.
- [DATA-066](issues/DATA/DATA-066.md): add the 52 generated 2002 teams so
  cross-season play has a second full cohort. **Blocked:** the existing 2002
  bundles came from the older `college-chartgen-v1` pipeline and fail the
  release audit (0/52 pass tactical contrast; two teams have fully blank
  defensive charts). They must be regenerated with the approved
  `bb-chartgen-budget-alpha-v1` exporter before they can be pinned. Only
  generated charts are in scope; the PDF-imported 2002 teams stay private.

The engine already accepts independent season-qualified team IDs and derives
rules from the designated home team's season; see UI-070's verification comment.
No engine change is planned for this scope within the supported 1940–2023 home
season range. Supporting 2024+ home seasons remains a separate rules-profile
extension and is not part of 1.1.0 unless separately approved.

## Explicitly out of scope

- Milestone 43 persistent played-season statistics ([DATA-065](issues/DATA/DATA-065.md)).
- Milestone 45 simulation-improvement measurement ([DEV-080](issues/DEV/DEV-080.md)).
- New seasons beyond the 2002 generated cohort tracked by DATA-066, other new
  chart generation, chart-rights changes or private-data distribution.
- Version metadata changes, native builds, tags or publication. Those happen in
  a later release-preparation phase after Milestone 44 acceptance.

## Acceptance gates

Follow the established release gate when this target is actually prepared:

- Test-first synthetic cross-year/same-year regressions, including swapped
  home/away, same school in different years, human/manual modes, unsupported
  home profiles and save/load identity preservation.
- Assert actual engine kickoff/touchback and overtime behavior across a supported
  rules boundary, not only rendered labels.
- Frontend unit/build, API/session/persistence regressions and a real-engine
  browser play-test of the setup flow.
- Full Python coverage, lint/format, dependency check, generated-chart audit and
  the complete browser suite on the exact release bytes.
- Publication review for private charts, PDFs, logs and saves; preserve the exact
  generated/sample allowlist and source attribution.
- Verify published install artifacts on every supported native target after
  publication, per [release validation guidance](release-builds.md).

## Verification

Documentation-only change. Ran
`python3 -m pytest tests/test_issue_tracker.py tests/test_create_issue.py tests/test_priority_docs.py tests/test_release_player_docs.py -q`
and `git diff --check`. These validate the backlog record, not release readiness.


## DATA-066 candidate update, 2026-11-16

The generator recovery now has a separately identified 55-team 2002 candidate,
including reviewed season-specific commentary rosters for all 55 teams. This
supersedes the old 52-team attempt as the candidate under review, rather than
claiming reproduction of its missing snapshot. Existing 2007 chart pins remain
unchanged. The [concise candidate review](data066-release-review.md) records exact
package identity, successful mechanical/browser evidence, the failed rushing-fit
assessment and the remaining regression/integration/distribution decisions.
The season is not yet pinned in the public manifest; the source gate is still
running. No native v1.1.0 artifact or release has been built or published.
