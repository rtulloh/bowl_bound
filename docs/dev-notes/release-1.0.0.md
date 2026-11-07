# Bowl Bound 1.0.0 release preparation

Status: planned, not built or published. Owner selected version **1.0.0** on
2026-11-07, superseding the planned Alpha 10. Target immutable tag: `v1.0.0`.
[Milestone 42](milestone-42.md) owns the required correction and validation.

## Required work

- [DATA-064](issues/DATA/DATA-064.md): correct play-specific interception-depth
  generation and enforce independent plausibility checks.
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
