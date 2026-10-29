# Source and License Attribution

Bowl Bound is a standalone project. It has **no runtime dependency** on the Paydirt
repository. Paydirt ideas or components may be reused selectively, but only by copying a
small, attributed component after verifying it fits Bowl Bound (see
[project plan](dev-notes/project-plan.md), "Decision gates").

## Paydirt

| Field | Value |
| --- | --- |
| Project | Paydirt (Python simulation of the Paydirt football board game) |
| Author / copyright holder | rtulloh |
| Repository | `git@github.com:rtulloh/paydirt.git` |
| License | MIT, Copyright (c) 2026 rtulloh |
| Reference commit at Bowl Bound initialization | `bfaf841` (Paydirt v1.9.2) |

Guidance in `AGENTS.md` and the project plan was adapted from Paydirt's development
guidance, with Paydirt-specific NFL, Excel-import, release, and full-season requirements
replaced by Bowl Bound rules, PDF-import, and privacy requirements.

### Copied-component register

Paydirt web components were adapted into Bowl Bound in Milestone 10. Record every copied
or adapted component here in the same commit that introduces it. The commit column is the
Paydirt checkout the files were read from (`bfaf841`); the last commit that touched the
adapted files there was `c3712a6`.

| Bowl Bound path | Paydirt source path | Paydirt commit | Modifications |
| --- | --- | --- | --- |
| `frontend/src/components/FootballField.jsx` | `paydirt-web/frontend/src/components/Field/FootballField.jsx` | `bfaf841` | Rewritten to draw engine-supplied coordinates only; removed quarter/possession/first-down math and Paydirt team colors |
| `frontend/src/components/Scoreboard.jsx` | `paydirt-web/frontend/src/components/Scoreboard/Scoreboard.tsx` | `bfaf841` | Converted to JSX; shows only engine strings; no clock, score or timeouts yet |
| `frontend/src/components/PlaySelector.jsx` | `.../Plays/OffensePlays.jsx`, `.../Plays/DefensePlays.jsx` | `bfaf841` | Merged into one component; keys and labels come from the backend; Paydirt play names and keyboard shortcuts removed |
| `frontend/vite.config.js`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/src/styles/index.css`, `frontend/src/main.jsx` | same names under `paydirt-web/frontend/` | `bfaf841` | Trimmed to the Milestone 10 demo; Paydirt fonts, colors, websocket proxy and animations removed |
| `frontend/playwright.config.js` | `paydirt-web/frontend/playwright.config.js` | `bfaf841` | Serves the production build from the Bowl Bound API over synthetic teams |
| `frontend/src/components/CoinToss.jsx` | `paydirt-web/frontend/src/components/Game/CoinToss.jsx` | local reference checkout | Coin appearance only; removed browser randomness, heads/tails outcome rules, CPU choices and possession calculation; engine winner/choices remain authoritative |
| `bowl_bound/coaching.py` | `paydirt/computer_ai.py` | `bfaf8410cb586149f06f98bf98ecca572cae360d` | Adapted balanced/situational mixture, independent coaching randomness and legal fallback ideas; independent public-observation implementation, no coupled engine class, NFL restrictions or chart analysis |

The Milestone 20 concealed simultaneous-call flow also follows Paydirt’s
`paydirt-web/frontend/src/components/Game/PlayingPhase.jsx` design at that checkout:
only the human role is selectable. Bowl Bound plans privately on the server rather
than sharing both selections with the browser. Colored dice are an independent
engine-metadata renderer; Paydirt dice distributions/display code were not copied.

Not copied: Paydirt's store, hooks, routes, play log, dice display and penalty handling.
The FastAPI adapter (`backend/`) and the engine session are new Bowl Bound code.

The repository-local issue workflow (`docs/dev-notes/issues/README.md` and
`scripts/build_issue_index.py`) follows Paydirt’s per-ticket front matter, generated
index, and open/resolved/closed verification model. The Bowl Bound generator is a
standalone implementation with required canonical-milestone ownership and metadata
validation. No Paydirt tickets, gameplay rules, or runtime code are imported.

Milestone 18 save/resume follows the versioned JSON, local-team reference and browser
download/load workflow reviewed in `paydirt/save_game.py` and
`paydirt-web/backend/routes.py` at `bfaf841`. `bowl_bound/save_game.py` and the browser
SaveControls are independent implementations: a strict Bowl Bound command/dice
journal reconstructs pending procedures instead of copying NFL snapshot fields or
inferring pending scores from prose. No Paydirt code/package is loaded at runtime.

Paydirt is MIT-licensed, so its copyright and permission notice apply to the adapted
portions:

> MIT License
>
> Copyright (c) 2026 rtulloh
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this
> software and associated documentation files (the "Software"), to deal in the Software
> without restriction, including without limitation the rights to use, copy, modify,
> merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
> permit persons to whom the Software is furnished to do so, subject to the following
> conditions:
>
> The above copyright notice and this permission notice shall be included in all copies
> or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
> INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
> PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
> HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
> CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
> THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Bowl Bound license

Original Bowl Bound code and documentation are licensed under the
[MIT License](../LICENSE), Copyright (c) 2026 rtulloh, selected by the owner
on 2026-10-28. Adapted Paydirt portions retain the notice above. The original
fictional sample charts have their separate CC0 dedication below. This code
license does not grant rights to third-party game text, names, charts or rosters,
and does not imply affiliation with or endorsement by any game publisher.

## Game and chart material

Rulebook text, historical team PDFs, converted team data, and rosters are private by
default. They are not covered by the Paydirt MIT license and are never committed unless
redistribution rights have been explicitly established. See [AGENTS.md](../AGENTS.md)
for the privacy policy.

### Historical charts and rosters

Only the original fictional samples below are approved for public tracking and
distribution. A historical PDF filename containing "free" is not a license.
Historical PDFs, converted charts, provenance, verification expectations and
rosters remain private unless distribution rights and explicit current approval
are separately established. The code license grants no rights to that material.
Do not include private comparisons or chart-derived examples in public docs.

## Original public fictional teams

Cedar Valley and Harbor Tech (2007) are independently authored synthetic teams.
Their chart bundles and provenance are narrowly tracked under
[`seasons/2007/`](../seasons/README.md),
not derived from PDFs, historical charts, or Paydirt chart values. The generation
recipe in `bowl_bound/sample_teams.py` reproduces them byte-for-byte. Original sample
content is dedicated under [CC0-1.0](../seasons/SAMPLE-LICENSE.md); all historical material
remains subject to its separate privacy and redistribution restrictions.

### Current release-packaging direction (2026-10-26)

The owner has directed that the 2002 Ohio State and Miami (Florida) teams remain
unpublished in game packaging when GitHub release builds are introduced. This
supersedes treating the earlier “marked free” statement as permission to bundle
them. Keep local charts intact but exclude both teams, historical provenance and
rosters from public release archives/runtime bundles. Only the original fictional
Cedar Valley and Harbor Tech samples are currently allowlisted for tracking and
public game distribution. Do not package the whole local `seasons/` directory.
Milestone 24 must inspect built artifacts, not rely on `.gitignore` alone.
