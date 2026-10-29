# Node 24.22.1 frontend toolchain acceptance

## Scope

Owner requested moving the web frontend from end-of-life Node 18.20.8 to
Node 24.22.1 before alpha. This is a milestone 20a tooling follow-up, not
CLI completion, a rules change or a dependency-major upgrade. See DEV-015
and the separate pre-alpha dependency finding DEV-016.

- Root `.nvmrc` pins **24.22.1**. Existing nvm installation downloaded the
  official Apple Silicon distribution and verified its SHA-256 checksum.
- `frontend/package.json` requires `>=24.22.1 <25` and npm `>=11.19.1 <12`,
  records `npm@11.19.1`, and `frontend/.npmrc` enables engine-strict installs.
- The lockfile changed only its root engines metadata. All **380 dependency
  entries**, versions, integrity hashes and resolutions remain identical.
- No app source, chart, gameplay, fixture or assertion changes were needed.
  There is no frontend ESLint configuration to migrate; Python Ruff is unchanged.
- nvm selection via `nvm use` works at the root; global default remains Node 18.
  No shell profile/global default changed. Developers must select this project
  runtime before invoking npm; installing another version does not switch all
  existing terminal sessions automatically.

## Security evidence and limits

The [Node security advisory](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases)
explicitly lists the **eMudhra intermediate CA compromise**;
[24.22.1](https://nodejs.org/en/blog/release/v24.22.1) contains the mitigation.
This is not an npm malware incident or evidence of a compromised host. Node
is build/development/test tooling here; Python serves the static web assets.
This change does not update system/Python certificate stores or other projects.

Full `npm audit` still exits 1: **5 vulnerable development-tool package entries**
(2 moderate, 1 high, 2 critical) in esbuild/Vite/vite-node/tinypool/Vitest.
`npm audit --omit=dev` reports **0 vulnerabilities**. This is not a comprehensive
compiled-bundle security review. DEV-016 tracks deliberate major-version
remediation before alpha; no `npm audit fix --force` was run.

Clean install warnings are retained: deprecated whatwg-encoding@3.1.1 and npm 11
allowScripts review warnings for esbuild@0.21.5 and optional fsevents@2.3.2/2.3.3.
A later `npm install-scripts ls` on this platform lists esbuild; no broad
lifecycle-script approval/denial or warning suppression was added.

## Validation

All npm commands below ran from `frontend/`, with
`$HOME/.nvm/versions/node/v24.22.1/bin` prepended to PATH.

- `npm install --package-lock-only --ignore-scripts`: passed; exact dependency
  graph unchanged (canonical JSON SHA-256 excluding root:
  `fe267a5163179dcae1fa5b1cac498c3a24c731a8e3ac549810c0ddc3a069a490`).
- `npm ci`: clean install passed, warnings/audit findings listed above.
- `npm test`: **104 passed**.
- `npm run build`: passed; built asset names unchanged.
- `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS=<isolated-v2-synthetic-root> npx playwright test`:
  **26 passed**, no retries or skips, including six complete sample games,
  reconciled clock/scoring/statistics, save continuation, defense names and
  compact recorded dice. Isolated server on 8123; live server not restarted.
- Node 18 `npm ci --dry-run --ignore-scripts`: expected **EBADENGINE**, confirming
  unsupported tooling fails before installation. This is metadata validation,
  not a new gameplay behavior or an artificial test suite.
- `nvm use`, `node --version`, `npm --version`, `nvm version default`: confirmed
  **24.22.1**, **11.19.1**, and unchanged global default **18.20.8**.

Use existing tests for this metadata/documentation change; no synthetic gameplay
regression invented. Node upgrade acceptance is separate from the still-open
DEV-016 dependency remediation. No release, push or publication performed.

Final cumulative metadata gates (repository root):

- `.venv/bin/python scripts/build_issue_index.py`: passed.
- `.venv/bin/python -m pytest tests/test_issue_tracker.py tests/test_packaging.py -q --tb=short`: **23 passed**.
- `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`: passed.
- The documented root `npm --prefix frontend ci --dry-run --ignore-scripts`
  also rejects Node 18 with EBADENGINE.

Tested toolchain implementation: **5a1f63f**. DEV-015 resolved against that
commit; DEV-016 remains open for the separate pre-alpha dependency upgrade.

## Subsequent DEV-016 remediation

The evidence above describes the original runtime-only upgrade. See
[dependency-security.md](dependency-security.md) for the separately scoped
2026-10-28 Vite/Vitest/plugin upgrade, clean-install/script policy and reruns;
its current results supersede the original outstanding audit count, not the
historical record.
