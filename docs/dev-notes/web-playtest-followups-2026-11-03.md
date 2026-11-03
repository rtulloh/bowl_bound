# Web play-test follow-ups — 2026-11-03

Owner review of the M33 candidate identified missing special-team results in play
history ([UI-054](issues/UI/UI-054.md)) and duplicated timeout counts on buttons
([UI-055](issues/UI/UI-055.md)). These are independently testable follow-ups;
neither is evidence of completed milestone acceptance.

## Paydirt consultation

Reviewed local Paydirt's
`paydirt-web/frontend/src/components/Game/PlayLogDisplay.tsx` and its tests,
`components/Game/PlayingPhaseTimeout.test.jsx`, and
`components/PlayLog/PlayLog.jsx` before implementation. Adapt coverage that every
recorded event remains visible and that display changes preserve request wiring.
Keep Bowl Bound engine-generated descriptions, labels and legal actions. Do not
reuse Paydirt's UI field-position calculations, prose-based yardage interpretation,
NFL state assumptions or client-created football event records.

## Timeout button labels

Remove parenthesized remaining-timeout counts from Use/Cancel buttons; the
scoreboard remains the authoritative visible budget. Keep both conditional and
legacy action identifiers, request behavior and clock rules unchanged. Engine
tests must establish the label change before updating synthetic display fixtures.

## Special-team history

Trace a synthetic touchdown/PAT/kickoff/return sequence through committed reports,
API serialization and the rendered history. Distinguish durable history from the
latest-result panel and retain the engine's combined kick/return report model.
Record the reproduced failure and focused checks before a behavioral correction.
