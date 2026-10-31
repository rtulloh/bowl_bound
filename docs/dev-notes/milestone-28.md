# Milestone 28: Preserve save replay across automatic timing changes

## Paydirt consultation

Reviewed the local Paydirt save implementation and tests before implementation:

- `../paydirt/paydirt/save_game.py`: Paydirt stores a versioned JSON snapshot of
  the game state and restores fields into a new engine.
- `../paydirt/tests/test_save_game.py`: tests cover writing and restoring saved
  state, including scoring data.

Adapt the explicit save-compatibility testing. Do not copy Paydirt's snapshot
format or team-path loading: Bowl Bound saves must continue to validate their
integrity, match local chart fingerprints, and reconstruct state by replaying
recorded commands and rolls. No NFL behavior, Paydirt data, or runtime dependency
is reused.

## Finding

The owner reported that a local game saved before Milestone 27 no longer loads.
The unchanged pre-Milestone 27 checkout loads it, but current code rejects the
replayed state digest. A structural comparison found that game state and all
other digest fields match; the timing log's normal-method label changed from
`clock:runoff` to `standard`. The private save itself remains local and is not a
test fixture.

Older saves made while a normal clock choice is pending also include the removed
runoff action in the pending controls. The compatibility check must recognize
that old digest while keeping the current live controls unchanged.

## Acceptance

- Synthetic pre-Milestone 27 saves at a live scrimmage and pending clock choice
  replay under current code with the same state and current legal actions.
- Invalid integrity/state digests and mismatched local charts remain rejected.
- The owner-provided save loads without being edited or overwritten.

## Validation

- The new synthetic compatibility test failed before the fix with
  `SaveFormatError`; both legacy fixtures now load and preserve the current legal
  actions and next-play continuation.
- Focused save, CLI, and issue-index checks: 119 passed.
- Full Python gate: 2,606 passed in 515.17 seconds, 93.33% coverage, no skips.
- Ruff, formatting, `pip check`, and `git diff --check` passed.
- The owner-provided save loaded through `--play --load` to the interactive
  prompt. Exiting did not save; a before/after hash confirmed the private file
  was unchanged.
- Frontend files were not changed, so frontend and browser suites were not
  rerun.

Milestone commit: `9d0678d` (`milestone 28: preserve pre-timing save replay`).
CLI-048 was resolved against this tested commit and closed after the owner
confirmed resuming and playing through a quarter transition.
