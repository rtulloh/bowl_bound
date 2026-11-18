# Frontend dependency remediation — DEV-016

## Paydirt reference / applicability

Reviewed Paydirt release workflow and selective runtime spec for milestone24
(see milestone-24.md). Adapt clean build separation, not its unpinned install
commands or broad dependency collection. Bowl Bound serves static assets with
Python; Vite/Vitest are development/build/test tools and are not player servers.

## Red evidence and selection

On 2026-10-28, full npm audit reproduced5 affected package entries:2 moderate,
1 high,2 critical (esbuild, vite, vite-node, tinypool, vitest). This is the
meaningful failing security check; no artificial gameplay regression was added.
There is no evidence of host compromise or production runtime exposure.

Registry engines/peers/dependencies were reviewed before selecting exact versions:

- Vite8.3.5: Node20.19+/22.12+, Rolldown-based toolchain.
- @vitejs/plugin-react6.1.2: Vite8 peer, same Node minimum; optional React
  compiler/Babel peers are not required for the current plain React app.
- Vitest5.0.5: Node22.12+/24/26+, supports Vite6.4/7/8 and existing jsdom.

Node **24.22.1** / npm **11.19.1** constraints remain unchanged. Existing React,
jsdom and Playwright versions remain unchanged; no gameplay/UI assertions or
Vite configuration needed weakening or skips. No npm audit fix --force used.

## Lifecycle scripts / validation

Both selected install and clean install used **--ignore-scripts**. This is the
release-build policy unless a particular necessary script is reviewed separately.
No blanket allowScripts entry was added. Platform-native packages installed as
optional locked dependencies; unit/build validation succeeded without scripts.
Other platforms still require their own clean native build/smoke evidence.

- npm ci --ignore-scripts:260 installed,261 audited,0 vulnerabilities.
- Retained warning: whatwg-encoding3.1.1 deprecated under the existing jsdom
  dependency. No warning suppression; it is not an audit vulnerability finding.
- Full unit suite:122 passed /16 files using Vitest5.0.5. Performance advice
  about jsdom pool reuse was informational; isolation was not weakened.
- Production Vite8.3.5 build passed (29 modules).
- Full npm audit after install and npm audit --omit=dev:0 vulnerabilities.
- Python release-metadata tests:2 passed after lockfile changes.
- Full real-engine Chrome browser suite: **32 passed in3.7m**, no retries, skips
  or warnings reported. All original gameplay/save/commentary assertions retained.

The older node24-upgrade.md describes the pre-remediation graph and warnings.
Keep that historical evidence; use this note for the subsequent dependency change.
A zero audit count is not a comprehensive code or bundled-artifact security audit.

## November 17 policy — advisory audit, required application regression

The owner directs that npm audit should not block the native build. Keep the
full audit in the separate **Dependency audit (advisory)** workflow and retain
its failing status and logs when vulnerabilities are found. The **Tests**
workflow and local full-regression runner exclude this command. The exact-commit
native verifier continues to require successful Tests, including Python coverage,
frontend unit/build, generated-chart audit and real-engine browser regression.
Run `npm audit --prefix frontend` independently for a fresh report.

DEV-087 remains open for unpatched picomatch GHSA-fc5q-39xc-vjpf. The current
13/14 high package findings propagate that advisory; they have not been fixed.
`npm explain picomatch` identifies development paths through Vite, Vitest and
Tailwind/Chokidar/globbing dependencies. The application imports React and its
own components; the exact native runtime selection serves compiled static
assets and excludes node_modules and the Node development server/toolchain.
This narrows the observed exposure to build/test tooling; it is not a claim
that development dependencies are harmless or that every future advisory is
acceptable. Retain clean locked installs with scripts disabled, review new
findings, and apply a compatible maintained fix when available. No dependency
version, lockfile, audit severity filter or audit return code is changed.

Consulted Paydirt .github/workflows/test.yml for this phase: its frontend
unit/build/browser checks do not include an npm-audit release gate. Adapt the
separation of application regression from advisory reporting, not its NFL
behavior, runtime dependencies or data packaging. Official references:
[npm audit](https://docs.npmjs.com/cli/v11/commands/npm-audit/) and
[Vite static production output](https://vite.dev/guide/build.html).
