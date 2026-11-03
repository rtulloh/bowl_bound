# Milestone 37 — downloadable support reports

Status: planned; owner requested a ticket, not immediate implementation.
Tracked work: [UI-056](issues/UI/UI-056.md) and
[UI-057](issues/UI/UI-057.md).

Provide a Download support log action and an email-compose link to the existing
public contact, `bowlboundsupport@gmail.com`. A user should be able to review the
report, download it and attach it to an email. A mailto link cannot attach files;
its body should contain a useful summary and clear attachment instructions.
No automatic email sending or external upload is authorized by this feature.

## Paydirt consultation

Reviewed Paydirt's `paydirt-web/frontend/src/components/Game/PlayLogDisplay.tsx`,
its tests, and `components/PlayLog/PlayLog.jsx` during this planning phase. Reuse
the idea of a complete readable event history, not client-created football facts
or prose-derived positions. No ready-to-reuse support exporter was established
by this review. Bowl Bound's `docs/reporting-bugs.md`, engine reports and privacy
rules define the applicable report boundary.

## Acceptance

- Replace player-facing spreadsheet terminology such as `cell` with contextual
  result labels in the game and reports. Distinguish a chart result or rule result
  from a fully resolved play; retain technical schema and provenance identifiers.

- Include every recorded event through the current point: scrimmage, PAT/tries,
  kickoffs, returns, penalties and mandatory continuations; distinguish a pending
  result from a completed play. Preserve exact engine chronology and timing,
  scoring, field/down context, timeout use and dice/chart audit evidence.
- Include version/build, rules profile, control mode/difficulty, relevant runtime
  details and source/chart fingerprints needed to identify a reproduction.
  Decide the minimal replay data that can be safely included; provide explanatory
  gaps instead of claiming missing raw charts are embedded or replayable.
- Offer a readable complete copy/export plus a deterministic UTF-8 download,
  including long and unfinished games. Use server bytes for any structured
  integer-rich data rather than lossy browser JSON reserialization.
- Let users review what they share. Keep private content local until the user
  explicitly shares it; exclude full chart matrices, source PDFs, credentials,
  unrelated files and unnecessary local paths. Review the existing reporting guide
  for the appropriate handling of detailed chart traces.
- Open a prefilled compose window for the documented support address, with a
  concise problem template and attachment instructions. Preserve a copy/download
  fallback when a mail client is unavailable. Do not transmit on opening the link.
- Synthetic tests verify completeness, source fidelity, save/load, partial and
  complete games, boundary cases, export purity and the actual compose link.

This work must not create another source of football rules in the browser.
