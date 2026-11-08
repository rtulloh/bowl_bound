# Bowl Bound 1.0.0 release preparation

Status: integrated for final release gates; not built or published. Owner selected **1.0.0** on
2026-11-07, superseding the planned Alpha 10. Target immutable tag: `v1.0.0`.
[Milestone 42](milestone-42.md) owns the required correction and validation.

## Required work

- [DATA-064](issues/DATA/DATA-064.md): correct play-specific interception-depth
  generation and enforce independent plausibility checks. After the final fix,
  complete the [whole-cohort passing-cell audit](milestone-42.md#whole-cohort-passing-cell-audit)
  on actual release charts; disclose all flagged values and unresolved exceptions.
- [DATA-055](issues/DATA/DATA-055.md): complete independent event accounting and
  close the known kickoff-return recovery observer coverage gap.
- [DATA-046](issues/DATA/DATA-046.md): compare frozen corrected candidates with the
  available compatible private 2007/2008 developer references under matched
  conditions, with explicit source support and explained differences.

Keep LSU/Ohio State owner review before broad regeneration. Record per-ticket
acceptance evidence and the overall release decision. The 1.0.0 naming decision
does not mark unfinished work complete or change statistical acceptance criteria.

## Packaging and publication

At release preparation, coordinate package, application, frontend, launcher and
native installer/version metadata on 1.0.0, update applicable development-status
and player/release wording, and run the final full regression on those exact
bytes. Preserve existing source/accuracy limitations accurately; a software
version does not turn modeled or unknown chart inputs into historical evidence.

Use the current source/native/package verification workflow, exact approved
generated-team/sample manifests and excluded private-reference inventory.
Verify all platforms, installed/portable behavior, checksums, catalog and
save/load acceptance before upload. Confirm v1.0.0 is unused; never delete or
reuse an earlier tag. Publish a regular Latest release with verified assets and
clear correction notes. Existing alpha tags, assets and live games remain intact.

No version metadata, chart, runtime, tag or release asset is changed merely by
recording this target. Detailed implementation and release evidence belongs in
the milestone notes and a final acceptance section when actually available.

## Simultaneous Bowl Bound and Paydirt play

Owner explicitly requested [DEV-078](issues/DEV/DEV-078.md) for 1.0.0: Bowl Bound
uses local port **8001** by default in standalone/source production launchers and
`python -m backend`; Paydirt retains **8000**. Include this in release notes and
native startup acceptance. Frontend development proxy/player URLs use the Bowl
Bound port, and explicit `--port` overrides remain available.

## Root integration and bounded release scope

Root integrated the final reviewed `c89b83a` lane into release commit `57974ab`,
preserving its exact runtime/chart files alongside the separate future planning,
maintenance and AGENTS documentation. Reconciled conflicts were append-only
notes and the regenerated issue index. The original owner checkout, running
previews and immutable Alpha 9 release remain unchanged by that integration.

Consulted local Paydirt docs/dev-notes/release-1.10.2-scope.md before this release
phase. Adapt its separation of concrete correction evidence, immutable tested
source and platform artifact verification. Do not reuse NFL models, privately
sourced charts, broader historical-fit conclusions or its release-test waiver.

The 116-team conditional-depth correction and schema-three source/stage gates
are implemented and independently reviewed. The prior exact implementation gate
at `ca04750` passed 5,525 Python tests with 92.25% combined/87.73% branch coverage,
without skips/warnings. Representative 34 and matched 32 checks pass core,
strict replay and addressed-save acceptance. Their causal/clock results remain
partial; full DATA-055 and broader DATA-046 historical qualification stay open.
Those limits are disclosed and do not become a historical-accuracy claim in
1.0.0. No new behavior work from Milestones 43, 44 or 45 is included.

Release metadata now uses 1.0.0 across Python, API, frontend and launcher. Existing
version assertions are updated to that identity; engine/save profiles are not
changed. Player guidance describes the actual conditional-depth model and new
8001 default. The public source chart audit freshly passes all 116 teams after
version integration. Exact-version full regression, packaged/native port checks,
fresh OSU screenshots and all-platform artifact inspection remain before
publication; no final build or release success is claimed at this checkpoint.

## Stable-version packaging correction

The actual 1.0.0 staging attempt exposed alpha-only guards; tracked as
[DEV-081](issues/DEV/DEV-081.md). Synthetic regressions first reproduced the
failure (8 failed/10 passed after correcting a missing test-fixture notice
directory). One shared stable/alpha version pattern now governs source staging,
runtime archives and Windows installers. Exact component agreement, path safety
and archive inventories remain enforced. The focused packaging/native/launcher/
metadata/issue/player-doc suite passes 186 tests and fresh actual source staging
succeeds. Native Windows compilation remains a runner gate.

The initial exact-version full regression was deliberately interrupted after one
test when this blocker was discovered; it is not counted as passing. A new frozen
full run follows the packaging correction. Earlier frontend tests/build and the
116-team chart audit remain separate evidence; none substitutes for final native
port 8001 coexistence acceptance.
