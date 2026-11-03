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

## UI-055 validation

Four synthetic label cases failed against unchanged `78ffa23`, then passed after
removing only the duplicated suffix. Ran:

```text
PYTHONPATH=. .venv/bin/python -m pytest tests/test_timeout_button_labels.py tests/test_conditional_timeouts.py tests/test_armed_timeouts.py tests/test_timeout_continuations.py tests/test_issue_tracker.py -q
PATH=<Node 24 directory>:$PATH npm test -- src/test/clockFlow.test.jsx
PATH=<Node 24 directory>:$PATH npm test
PATH=<Node 24 directory>:$PATH npm run build
PYTHONPATH=. .venv/bin/python -m ruff check bowl_bound/regulation.py tests/test_timeout_button_labels.py
PYTHONPATH=. .venv/bin/python -m ruff format --check bowl_bound/regulation.py tests/test_timeout_button_labels.py
git diff --check
```

Results: 104 Python cases, five focused/frontend clock cases, all 131 frontend
cases and build/lint/format passed. These checks cover the presentation change;
they do not claim a fresh full Python gate or automated browser execution. No
push or change to a running frozen server is included in this checkpoint.

## Combined branch verification

Reviewed label implementation `81dc6e4` is integrated as `9d5071f`; runtime matches
the immutable parent play-test candidate at `855d4bb`. Tested merged head
`61d75fd` passes **3,503 Python tests in 879.31s, 93.17% branch coverage**, with
no skips or warnings. The integration's focused timeout/label/API/tracker run
passes 108 in 13.36s; frontend 131, build, Ruff, pip, link and diff checks pass.
This replaces the earlier full-gate-pending state for this merged source only;
automated browser execution remains unverified locally under the known sandbox
restriction.

UI-055 remains resolved awaiting owner confirmation. UI-054 remains open: API
and SSR/JSDOM retain the inspected PAT and complete kick/return entries, while
actual bounded-list scrolling/viewport visibility still needs verification.
UI-056/M37 only plans future support-log tools. No speculative event-loss fix,
publication or running-server change is part of this integration.
