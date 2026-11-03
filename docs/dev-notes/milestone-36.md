# Milestone 36 — Easy player coaching helper in the web UI

## Owner direction and scope

On 2026-11-03 the owner requested a ticket in a subsequent milestone to bring
Easy player help to the web UI. Browser Easy CPU difficulty already works. The
missing feature is the general player coaching helper: the CLI currently enables
it by default on Easy and offers a `Z` toggle. The browser already displays the
separate engine-owned shared fourth-down guidance across normal difficulties.
This note schedules future investigation and implementation; no helper behavior,
API or UI is implemented here. Do not expand M33, the chart-generator workstream
or M35 coffin-corner scope. Track this work in [UI-053](issues/UI/UI-053.md).

## Consultation before planning

Reviewed the actual local Paydirt sources:

- `paydirt/interactive_game.py:1069-1116` displays role-specific helper output and
  numeric-chart limitations; `docs/playing.md` documents the `Z` toggle.
- `paydirt/ai_analysis.py:943-1055` defines `EasyModeHelper`, conditional numeric
  offense suggestions/coverage, a defensive tendency recommendation and tips.
- `tests/test_ai_analysis.py:264-327` checks helper construction, bounded offensive
  suggestions and defensive output. Adapt the contract-test shape using fictional
  Bowl Bound fixtures; do not reuse its team fixtures or run private-data tests.

Adapt separation of analysis from presentation, role-specific content and honest
coverage limits. Do not reuse NFL timing/two-minute-warning tips, formation maps,
opponent tendency claims, global helper state, chart data or runtime dependencies.
Paydirt is design input, not Bowl Bound rules authority. Reconsult relevant code
and tests when implementation begins.

Reviewed Bowl Bound `bowl_bound/player_coaching.py`, `SavedGame.player_advice`
and `player_advice_available` in `save_game.py`, the helper display/toggle in
`cli.py`, `tests/test_player_coaching.py`, and `docs/playing.md`. The existing
engine computes up to three numeric-only offensive estimates with explicit
coverage and exclusions over the exact 216 offensive dice outcomes. Current
defensive help is situational text, not a concrete learned recommendation.
Availability is Easy-only and requires an eligible legal offense/defense context;
mandatory pending decisions do not currently receive this general helper. These
observations are an initial inventory, not proof of every lifecycle or special
branch. Inspect the API/frontend and all pending contexts before claiming parity.

[CLI-047](issues/CLI/CLI-047.md) remains open for role-specific presentation and a
concrete public-situation defensive recommendation. Reconcile/reuse that pipeline
rather than creating competing helper policies or treating its planned behavior
as already implemented. [UI-041](issues/UI/UI-041.md) supplies the existing shared
public fourth-down advice; retain its approved policy and visibility.

## Planned implementation and acceptance

1. Inventory offense, defense, kicks, conversions, penalties and other pending
   decisions in engine/CLI/browser flows. Record what exists, what is absent and
   what is intentionally out of scope; do not promise unexplored Paydirt parity.
2. Define an engine-owned read-only assistance contract with availability, legal
   action identities/labels, role, advisory content and honest unavailable/limited
   coverage. Reuse verified Bowl Bound analysis. The API adapts engine facts and
   the browser displays them; neither interprets charts nor calculates football.
3. Define Easy-only helper visibility and an accessible on/off control. Decide
   and document browser defaults and preference lifetime across new games,
   Save/Load, reload, human-side changes and control-mode changes. Do not silently
   change replay data to persist a presentation preference. Test Medium/Hard and
   unavailable/finished contexts explicitly.
4. Preserve every legal choice and user selection. Help never submits a play,
   resolves a pending decision, consumes gameplay/coaching randomness, adds journal
   commands or changes state, statistics, clock or saved continuation. Repeated
   reads/toggles are pure. Respect current human/CPU information policy: no
   concealed CPU call, future dice, raw private chart/provenance or opponent data
   leaks. Expose only deliberately approved derived helper facts; conditional
   numeric rates are not full-engine conversion odds.
5. Keep existing fourth-down guidance consistent and avoid conflicting or
   duplicated recommendations. Do not reintroduce hidden chart inspection for
   CPU field-goal/punt/go selection or invent new football policy through UI work.
6. Write meaningful synthetic engine/API/frontend regressions first, show expected
   failures, then implement the smallest correct behavior. Cover all normal
   difficulties, both sides/roles, legal/unavailable/pending contexts, numeric
   coverage/exclusions, concealed-call independence, repeat-read purity, toggle
   accessibility, save/control-mode lifecycle and stale response handling. Add
   real-engine browser cases using only fictional public-safe charts.
7. Update player, coaching, API and save/control documentation as applicable,
   explicitly describing CLI/browser differences. Run focused and complete gates,
   review the public-safe changes, record tested commits and obtain actual owner
   play-test confirmation before closure and the dedicated M36 acceptance commit.

## Planning validation

This commit changes documentation/ticket planning only. Regenerate the issue
index, run the existing tracker checks and verify links/diff. No artificial
behavior test, production implementation, full gameplay rerun, push or live-server
restart is part of this planning task. Execution evidence follows below.

Planning checks: `.venv/bin/python scripts/build_issue_index.py` succeeds;
`.venv/bin/python -m pytest tests/test_issue_tracker.py -q` passes all **18** cases
in **0.49s**. All **849** local links in the changed planning documents resolve;
`git diff --check` passes. UI-053 remains open/planned; no feature implementation
or owner play-test acceptance is claimed.
