# Addressed mandatory-choice save capture

Status: implementation in progress for DATA-055; replay evidence is separate
from independent football accounting. Old aggregate midpoint/final replay flags
do not establish addressed save coverage and are not upgraded retrospectively.

## Scope and placement

`tools.pending_choice_capture.capture_pending_choices` is an opt-in development
collector for an isolated audit process. Nest it inside typed receipt capture,
then close both contexts before calling `verify_pending_choices`. It wraps the
actual `SavedGame._execute` boundary outside the typed profiler wrapper. This
covers public, atomic API and coached command paths, including coached paths
that bypass `_run`. It delegates every command once, skips native save replays,
and records diagnostic failures without replacing the authoritative result or
exception. Foreign threads, nested commands and abnormal collector exits make
the evidence unusable. It is not installed in the API server or game engine.

The collector holds strong references to the actual observed objects. Each
pending boundary retains its object number, creating command or initial anchor,
full view and log, enabled choices, complete native save and SHA-256, journal
frontier, tape count/position, team identities and game configuration. Commands
retain typed addresses and their exact same-object linkage. Unselected, failed,
foreign, missing and unusable evidence remains visible rather than becoming a
successful decision count.

## Save and continuation identity

`fixed_save` changes only native `saved_at` serialization metadata and its native
canonical integrity hash, with an explicit timezone. A synthetic frozen-clock
control compares it byte for byte with native `dumps_game`. It does not alter
football clock, journal, dice, RNG state, configuration or team fingerprints.
Native `loads_game` validates each detached save. Offline verification performs
the original enabled choice on a detached clone and compares the returned
object, complete view/log, exact canonical save, journal and dice continuation.
It never draws from the live game's RNG.

For an audit runner's real midpoint reload, pass `capture.resume` as the optional
`resume_checkpoint` callback. This performs the actual native reload and records
an explicit original-object to restored-object edge. Equal-looking unrelated
objects cannot supply an origin. Preserve both pending addresses across this
edge; the retired original boundary is accounted for by an explicit handoff,
and the restored boundary still requires its actual choice continuation. A
forked original continuing after the handoff is refused. The callback's default
is absent, preserving the runner's ordinary save/reload behavior.

## Design input and test-first evidence

Reviewed local Paydirt `tests/test_save_game.py` (initial save/reload and scoring
preservation controls). Adapted exact state and scoring preservation as design
input. That material does not supply addressed mandatory-choice receipts. No
NFL rules, file format, team data or runtime dependency is reused. Bowl Bound's
native save integrity, typed command lifecycle and mandatory menus remain the
authorities.

The unchanged typed collector lacks addressed mandatory saves: one meaningful
failure with two numeric/exception controls retained. Initial missing-module
failures are capability scaffolding. Four later corruptions exposed ignored
creating-command, duplicate-attempt, enabled-menu and abnormal-exit evidence;
a separate nondeterministic coach-seed fixture error was corrected explicitly.
The composed full-game test exposed a retired midpoint pending boundary, leading
to the explicit resume edge instead of dropping that address. A diagnostic
metadata failure also reproduced replacement of an authoritative command before
its guard was moved inside diagnostic error handling. All original failures are
retained privately; no engine defect is inferred from observer failures.

## Acceptance boundaries

A result labeled `GO-addressed-replay-only` requires complete linked typed
command/boundary exposure and matching detached continuations. Independent
causal ownership, statistics, field state, priority, clock and rules require the
separate bounded observer. Full-game or historical qualification additionally
requires frozen candidate inputs, complete exposure counts, required forced
branches, matched coaching conditions and the milestone's final gates. RZDZ is
an engine action, never a chart family. Detailed saves, game results and capture
receipts remain private.

## Additional exposure and metadata guards

Optional `clock_choice` menus remain separate from nonclock mandatory decisions.
A saved native view with `clock_optional=true` can legitimately continue by an
ordinary snap, kick or action. The original successful command is replayed and
counted as a normal clock continuation, without inventing a menu ID or changing
football behavior. Explicit clock decisions and nonclock mandatory decisions
have separate counts. An unselected final menu still remains unknown.

Complete exposure checks require a one-to-one typed-command mapping and both
before-pending and after-pending boundary addresses, including the last command.
Typed live tape frontiers are compared to the same actual object's snapshots;
a restored replay cursor is not the original live cursor. Every command retains
its full after-save, so even a nonpending resume must match the last observed
source command. A rejected resume makes the capture unusable even when caught.

Three meaningful corruption failures reproduced omission of a final menu,
fabrication of a tape frontier and duplicate use of one typed command. Independent
reviews then reproduced a forged phase label, a creator hidden as an initial
anchor, and Python's loose `True == 1` view comparison. The verifier now binds
phase to the native saved view, checks the earliest producing command address,
and compares structured JSON canonically with finite values and preserved types.
The original assertions and native engine behavior remain unchanged.

## Final synthetic conformance checkpoint

The exact frozen implementation passes 33 self-contained checks in 108.86
seconds. The full Hard game retains native midpoint and final strict replay,
and collection on/off compares the complete canonical save, view/log, entire
journal, actual dice and tape position. Its 214 commands use two actual
authoritative objects and retain 154 raw pending boundaries: 153 exact detached
continuations plus one explicit midpoint handoff. Continuations comprise 33
nonclock mandatory decisions and 120 normal-clock continuations, with no explicit
clock decisions, capture errors or unresolved boundaries in this synthetic game.
These are observed conformance counts, not complete forced-branch coverage.

The related typed-capture, envelope, pending-accounting and runner regression
passes 184 checks in 103.16 seconds; documentation/tracker checks pass 36.
Ruff, formatting and Pyright pass without ignores. Both source pins and the
original assertions remain unchanged during the final full run. Earlier runs,
including pre-peer and pre-annotation results, are retained with their actual
scope. No historical candidate games are run by this checkpoint, and the old
34-game panel's missing addressed saves remain missing. DATA-055 stays open.
