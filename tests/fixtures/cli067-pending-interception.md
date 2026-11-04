# CLI-067 pending-save regression

`cli067-pending-interception.json` was captured at commit `064e03d`, before
adding pending interception context. It uses `tests.test_cli.new_game()`:
the fictional `default_teams()` charts with season 2002, gameplay seed 7 and
coach seed 31. The only command is `snap 9 A`, leaving the game at its
return/incomplete choice. No historical chart, roster or owner game is included.

The strict replay test loads this unchanged pre-context save with the original
synthetic charts, displays the newly derived spot, and compares continuation
against a fresh game. Do not regenerate it using the implementation under test.
