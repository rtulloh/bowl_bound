# Milestone 24 — Initial alpha publication preparation

## Owner direction and boundaries

On 2026-10-28 the owner requested GitHub/release preparation after the M21a
implementation/audit commit d030974, with community feedback alongside remaining
roadmap work. This authorizes preparing tooling and documentation early; it does
not mark Milestones 22/23 complete or authorize a remote, push, tag or publication.
Keep local opencode.json changes outside project commits.

Decisions confirmed: MIT for original code; standalone apps for the initial alpha.
Owner supplied the public bug-report contact on 2026-10-28:
**bowlboundsupport@gmail.com**. Include it in the player reporting guide.
Proposed initial public version: 0.1.0-alpha.1 (Python normalized 0.1.0a1).
No tag is created during preparation; existing tags remain immutable.

## Paydirt consultation

Reviewed a local Paydirt checkout:

- paydirt.spec:5–18: selective data staging; adapt explicit resource inventory, not
  broad docs/images/directory globs or historical team inclusion.
- .github/workflows/release.yml:1–215: native platform builds and frontend build;
  adapt test/build/platform separation and checksum artifacts. Do not copy
  automatic public-release creation, broad dependency collection, unreviewed
  action versions or silent installer failures.
- paydirt-web/start.sh:1–48: path-independent startup and shutdown; do not ship
  uvicorn reload/Vite development servers or fixed readiness sleeps to testers.
- docs/installation.md:1–65 and docs/playing.md:1–75: separate install/run/play
  walkthroughs, platform-specific launch steps, clear troubleshooting. Do not
  inherit NFL play mappings, unavailable features or security-workaround commands.
- RELEASE_NOTES.md:1–63: versioned notes, but Bowl Bound public notes must contain
  player-facing features/limitations only, never private audit/seed/host details,
  local paths, internal ticket histories or agent configuration.

These are design references, not runtime dependencies. Retain copied-code
attribution when adaptation actually copies expression rather than an idea.

## Ticket sequence and commits

Each behavior change is test-first. Review tests before red, implementation
before green and final scoped diff before commit, as directed for M21a. Commit
each ticket before starting the next; run focused gates per ticket and the full
application gate before final milestone commit/publication recommendation.

1. [DEV-033](issues/DEV/DEV-033.md): license and version contract. Keep gameplay
   profile/save schema unchanged; test metadata mapping rather than bump rules.
2. [DEV-016](issues/DEV/DEV-016.md): separately scoped pre-alpha development-tool
   security remediation, retained in its existing milestone assignment. Review
   supported upgrades, clean install/audits, Node24.22.1 unit/build/browser gates.
   Never run blind force fixes or claim production exposure from dev advisories.
3. [DEV-012](issues/DEV/DEV-012.md): explicit release staging/manifest builder;
   no recursive inclusion of local seasons/, docs/, home directories or worktree
   contents. Fail on unexpected symlinks, missing inputs, unsafe destinations,
   stale assets and mismatched metadata; stage transactionally without destructive
   broad cleanup. Synthetic tests inject forbidden files and inspect archives.
4. [DEV-034](issues/DEV/DEV-034.md): standalone entry point and source launchers.
   Default production web mode uses one local FastAPI/Uvicorn process with built
   assets, no Node on player machines; preserve explicit CLI entry point. Loopback
   only unless explicit remote opt-in. Handle frozen/resource paths independently
   of cwd, missing resources, port conflict, readiness/browser opening and shutdown.
   Do not store player files in transient or read-only bundled resource directories.
5. [DEV-035](issues/DEV/DEV-035.md): README, player documentation index,
   installation/play/troubleshooting, public alpha notes and bug-report template.
   Reports request game version, short description/repro steps and optional
   inspected logs/save; never request chart PDFs, raw chart dumps, personal data
   or secrets. Email remains a publication blocker until owner supplies it.
6. [DEV-036](issues/DEV/DEV-036.md): PyInstaller and draft build workflow using
   only staged inputs. Target macOS arm64, Windows x64 and macOS Intel x86_64; no
   support claim until native runner smoke passes. Initial portable archives may
   avoid installers/signing complexity; document unsigned/platform caveats honestly.
   Pin reviewed tool/action versions; build from locked dependencies. Produce
   artifact manifest and SHA256 checksums. Prepare builds, not automatic publishing.
7. [DEV-037](issues/DEV/DEV-037.md): final source/history/privacy and fresh-machine
   audits, license inventory, full regression/security gates, player docs verification,
   platform evidence and owner go/no-go. Separate source-repository publication
   audit from distributable inspection: a clean ZIP does not make Git history safe.

## Artifact contract and excluded material

Include only engine/runtime modules needed to run the game, built frontend assets,
selected player docs, license/attribution/version metadata and exact original
Cedar Valley/Harbor Tech chart files plus their public synthetic provenance/license.
No optional local rosters, even fictional ones, are bundled without a separately
reviewed exact allowlist change. Historical team charts, source PDFs/rulebook,
saves, play/audit logs, developer notes/config, test fixtures, importer tooling,
node_modules, development servers, environment files and unrelated local files
are excluded from player artifacts. .gitignore is not a release manifest.

## Final acceptance / publication hold

- Test malformed/hostile staging inputs, filename/path traversal and symlinks;
  verify extracted contents, not just source-selection code.
- Fresh source checkout and built artifact load public samples, serve UI, play,
  save/reload, print version and shut down without private files or Node/Python
  installations for standalone users.
- Full Python coverage/lint/format, frontend unit/build, browser/full games and
  dependency/security checks pass; report all failures/retries/warnings honestly.
- No copied chart rights or official game affiliation implied by MIT/code license.
- Verify player-facing release notes have no developer-private content.
- Confirm email, license notices, platform/signing caveats and known limitations.
- Review public Git contents and reachable history before remote/tag/push approval.
  Never sanitize history destructively or change existing tags without approval.
- Stop after the dedicated milestone24 preparation commit for owner review. GitHub
  setup and first release-tag build are the next explicit owner-authorized step.

## Planning validation

Pending read-only plan review and existing issue-tracker checks. No runtime edits
or packaging/publication actions are part of this planning checkpoint.

### Grilling Notes

**Assumptions verified:** 4/5: existing backend serves built UI and binds locally
(backend/__main__.py); Python/API/npm currently duplicate version 0.0.1
(pyproject.toml, backend/app.py, frontend/package.json); source license was
undecided (docs/ATTRIBUTION.md); original sample reproduction/provenance already
exists (bowl_bound/sample_teams.py). Native cross-platform build support remains
unverified until actual runners execute smoke tests.

**Open Questions:** 2 -> 0: owner selected MIT and supplied the public support
email. Version 0.1.0-alpha.1 is a preparation default, not a tag.
**Status changed:** No; READY for preparation, NOT READY for publication.
**Key revision:** Stage before PyInstaller analysis, not just filter its data
files: dependency analysis from a dirty worktree can otherwise include unwanted
modules. Source launchers must also use built assets, not Vite/reload. Rollback
is a new immutable release/tag later; retain prior artifacts and do not mutate
existing saves/profiles, delete private material or rewrite history. Portable
archives are simpler than installers; native execution and signing caveats
remain explicit release gates rather than assumed capabilities.

## DEV-033 implementation evidence

Paydirt metadata/workflow consultation above applies to this ticket. Independent
version contract avoids copying runtime code. Reviewed tests before red:2 expected
failures (old version, absent license). After implementation review:51 focused
metadata/API/regulation/replay tests passed; focused Ruff passed. API health
payload, engine profile and save schema remain unchanged. License/version/API
documentation updated together; no tag or release exists.

## DEV-016 cumulative result

Separate prerequisite completed: selected Vite8.3.5, Vitest5.0.5 and React plugin
6.1.2 after engines/peer/advisory review. Clean install with --ignore-scripts,
full/production audits0,122 frontend tests/build and32 Chrome cases passed
(3.7m, no retries). Retained whatwg-encoding deprecation and informational jsdom
performance advice; no warning suppression or test-isolation weakening. See
[dependency security](dependency-security.md). Support email is now confirmed.

## DEV-012 release selection evidence

Implemented exact source/resource manifest and transactional stage/build/runtime/
archive script. Selected sample SHA256 pins match original public fictional
charts/provenance/license; no historical team or optional roster selected.
Synthetic injected private files, paths/symlinks/stale inputs/assets, immutable
outputs and archive content inspections covered. Reviewed tests before initial
missing-module/API reds and4 meaningful malformed-lock failures; implementation
review found no gameplay coupling. Focused29 tests passed with80.06% script
branch-aware coverage. Actual isolated staged clean frontend build and isolated
Python UI/team/game/save smoke passed; clean runtime ZIP assembled.
[Build guidance](release-builds.md) explains exact commands and remaining gates.
This ZIP is native-builder input, not the standalone alpha. Final lint/test
rerun after review precedes the ticket commit.

## DEV-034 starter evidence

Implemented production local launcher and source/standalone start.sh/start.bat
selection, preserving existing terminal entry point. Consulted Paydirt starter
above; deliberately avoided reload/Vite/child-process cleanup complexity. Tests
reviewed before missing-module red and failed-startup false-success regression.
After implementation review82 focused launcher/packaging/API tests passed; Ruff
lint/format passed. Live synthetic-resources startup from unrelated directory
confirmed API/UI readiness and graceful Ctrl+C exit. Browser never opens for an
occupied port and waits for actual startup. Source paths with spaces and frozen
resource resolution are synthetic-tested; actual Windows/frozen platform smoke
still required. Exact manifest now includes launcher and starter scripts.

## DEV-035 player documentation evidence

Replaced stale README and added player index, installation, play, startup,
troubleshooting, versioning, public draft release notes and email bug reporting.
Owner follow-ups included BowlBound.exe Windows naming, verified-download
security guidance, chart-extractor/platform-library instructions and official
Python/Homebrew/pip/venv links. Support address is bowlboundsupport@gmail.com.

Adapted Paydirt guidance structure, not private developer release-note content
or broad security bypasses. Exact package inventory includes only player guides
and a public attribution summary; no detailed source attribution register or
developer notes. Native dependency license texts are still a later gate.
44 focused checks (including local documentation targets/selection/privacy and
report contact) and64 synthetic importer CLI/export/e2e tests passed after
review. All8 official setup links returned HTTP200; importer help flags match
examples. No gameplay changes or historical-chart imports/tests were needed.

## Cumulative checkpoint — runtime/docs through 5bb3b3c

`.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **2,275 passed
in470.17s**, **93.38% branch-aware coverage**; no skips/warnings reported.
The unchanged75% floor passed. Launcher84% rounded module coverage. The earlier
DEV-012 script-specific80.06% check is separate: scripts are outside the normal
application coverage source list, not silently counted by this gate.
Frontend122/build and full32 Chrome cases passed with the remediated toolchain.
Repository Ruff lint/format and77 focused metadata/package/launcher/docs/tracker
checks passed at the player-doc commit. These results do not establish native
Windows/Intel/Linux standalone support or publication readiness.

## Owner-approved source publication snapshot

The owner separately authorized a public source push, then approved creating a
clean public snapshot after the pre-public history audit found private
verification expectations in documentation. This does not complete Milestone 24
or authorize tags, native artifacts or a GitHub release.

Reconsulted Paydirt `.gitignore`: retain separation of private charts, saves,
logs, environments and generated builds, but keep Bowl Bound's stricter exact
fictional-team allowlist. No Paydirt code or data is copied by this step.

The new public repository is independent of the retained pre-public checkout.
Old commit IDs in milestone/ticket notes describe that retained archive; they
are not ancestors that can be resolved in public Git history. Develop and push
from the new public checkout going forward; do not merge/push the old private
history. The original checkout and local agent configuration are unchanged.

Sanitization changes documentation/configuration only: remove historical-team
verification expectations, use an explicitly fictional schema example, clarify
current distribution permission, and generalize host-specific paths in prior
command examples. Omit opencode.json entirely. Engine, frontend, importer, tests,
fixtures, version/save profile, release manifest and public sample bytes remain
unchanged from the reviewed source. No behavioral red test is warranted.

### Source gate results

Fresh Python 3.12 environment installed with
`.venv/bin/python -m pip install -e ".[dev,web,pdf]"`. This source regression
uses local Python 3.12.8; it is not endorsement of that patch for native shipping.

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **2,275 passed
  in 450.68s**, **93.38% branch-aware coverage**; no skips/warnings reported.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m ruff format --check .`: **360 files** already formatted.
- `.venv/bin/python -m pip check`: no broken requirements.
- Frontend, Node **24.22.1**: `npm ci --ignore-scripts`, `npm test` (**122 passed**),
  `npm run build`, `npm audit` and `npm audit --omit=dev`: passed; audits **0**.
- Full real-engine Chrome gate: **32 passed in 3.7m**, zero retries/skips.
  Command in frontend: `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS="$TMPDIR/bowl-bound-public-source-e2e" npm run test:e2e`.
- Launcher `--version` prints 0.1.0-alpha.1; `python -m bowl_bound --seasons seasons
  --list-teams` lists exactly Cedar Valley and Harbor Tech (2007).
- **641** local Markdown file/directory targets exist; **11** pinned sample hashes
  match. Staged source contains **428** text files; no private libraries, PDFs,
  rosters, saves/logs, build/dependency trees, local config or prior Git history.
- Pattern-based credential/host-path scans found no matches. These checks are
  defense in depth, not a guarantee against every possible secret or a full
  dependency/native-artifact security audit.

Retained notices: npm reports deprecated whatwg-encoding@3.1.1; Vitest prints
informational jsdom pool-performance advice; pip reports an available update.
No warnings were suppressed and no assertions/skips/coverage thresholds changed.
Native builds, exact bundled dependency notices and platform acceptance remain
open under DEV-036/DEV-037. Source publication is not a standalone alpha release.

### Owner clarification: three native build targets

During source publication the owner requested macOS Apple Silicon arm64,
Windows x64 (BowlBound.exe) and macOS Intel x86_64 ("ix86"). No 32-bit macOS
or Linux standalone target is planned for the initial alpha. Reconsulted
Paydirt release.yml: adapt its separate ARM/Intel native builds, not its extra
Linux artifact, broad staging or automatic public release. DEV-036 and player
installation guidance updated; 77 focused release/launcher/metadata/tracker
checks passed after the documentation-only change. Native implementation and
smoke evidence are still outstanding; this source push creates no builds/tag.
