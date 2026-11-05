# Alpha 7 visual-chart candidate

Status: local integration and validation in progress; no push, tag, build
dispatch or publication authorized for this preparation checkpoint. Owner rapid
web play-test confirmation remains pending.

## Exact source and scope

Start from public origin/main `9a2897f7d45d9b2b6c48fc21fd311b02562d788b`,
verified with git ls-remote before worktree creation. This includes the complete
approved Alpha 6 catalog, M39 displaced-try analysis fix and public M40/DEV-073
native discovery deadline fix. Do not substitute the owner's private local main.

Merge only reviewed M38 and canonical M41 viewer work from
`eb2ebcd41449ff09a7ae85fbd6a489c051cc3a55`. Original tested implementation
commits `39a0e84e319094cd44fb5811447f0299edfed06c` and
`92fc811dafd6c56cabcb554451f43d2aa45bd42a` remain ancestors.
The numbering-correction commit preserves their hashes and historical labels.

Only the generated issue index conflicted; rebuild it from the merged ticket
files, retaining public DEV-073/M40 and separate UI-061/M38 and UI-062–065/M41.
No production source conflict or imported football-rule change occurred.
The public M40 notes remain the native-catalog fix; viewer notes use M41.

The candidate bumps coordinated Python/public/frontend versions to 0.1.0a7 /
0.1.0-alpha.7, leaving the existing engine profile/save schema unchanged.
Version tests first fail twice on the unchanged a6 implementation, with 15
passing controls; the required change is release identity only. Synthetic native
smoke fixtures may retain a6 as an arbitrary fake API version.

## Guidance and provenance

Reviewed the candidate's AGENTS.md, exact release manifest, Alpha 6 acceptance
record, player packaging/documentation tests and native discovery fix.
Reconsulted Paydirt `.github/workflows/release.yml`,
`tests/test_release_metadata.py` and
`docs/dev-notes/release-readiness-2026-11-02.md`. Adapt coordinated version
validation, separate build/publication stages and reconciled complete-game
evidence. Keep Bowl Bound's own exact manifest, generated-catalog rights scope
and native-smoke guards. Reuse no NFL behavior, private chart data or runtime
Paydirt dependency.

The generated catalog is byte-for-byte the reviewed public Alpha 6 set; no new
team, roster, provenance permission or source-data scope is added. Preserve
all three local previews on ports 8139, 8140 and 8141. Port 8141 is the owner's
rapid full-catalog play-test server and is not restarted by this work.

## Validation

Pending focused integration checks followed by one established full gate on the
complete candidate. Verify frozen CSV cells, full 10–39 desktop fit, closed help,
shared Priority, safe detached views, save/game purity and retained exact
118-team packaging. Native multi-platform artifacts/publication are later steps
after owner play testing and root coordination.

## Owner board-style follow-up

Before the integration gate completed, owner layout references added prominent
formation groups, boxed dice totals, strong chart colors, Running1–4 / Option5 /
Passing6–9 headers, separate supplemental offense columns, and Special Teams.
UI-066–068/M41 track these new presentation objectives. The first integration
gate was interrupted deliberately after 35 browser checks passed; remaining
checks and partial Python coverage are not acceptance. Renew the final gate
after all follow-ups are integrated. Preserve the baseline logs.
