# Alpha 3 release record

## Release workflow review

Reviewed the local Paydirt checkout before preparing this release:

- `.github/workflows/release.yml:176-196` publishes a GitHub Release from a tag
  and attaches inspected workflow artifacts. Adapt tag-driven release identity and
  artifact attachment; Bowl Bound's manual build workflow currently uploads
  artifacts only, so attach them to the release after inspection.
- `docs/development.md:91-92` treats published version tags as immutable. Preserve
  alpha 1 and create the new `v0.1.0-alpha.3` tag only after the matching-version
  build succeeds.
- Do not reuse Paydirt release scripts, product rules, or team data.

## Acceptance evidence

- Python, frontend, display, documentation, and artifact versions agree on alpha 3.
- The full standalone workflow succeeds on the release commit.
- Inspect all three platform artifacts and checksums before publishing the GitHub
  release. Include only the explicit public sample allowlist.
