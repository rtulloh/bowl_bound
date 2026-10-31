# Milestone 29: Clarify blank chart cells in terminal traces

## Paydirt consultation

Reviewed `../paydirt/paydirt/game_engine.py`, `ReturnChartRoll.trace` (around
line 77). Paydirt wraps raw return-chart values in quotes, so an empty value is
visible as `""`. Its return-chart trace is not the same as Bowl Bound's ordinary
offense/defense lookup trace. Adapt only the explicit-empty presentation idea;
do not reuse Paydirt game or chart semantics, private data, or runtime code.

## Finding

Bowl Bound has a valid normalized `NO_CHANGE` cell whose canonical CSV token is
empty. The CLI interpolates that token directly, displaying `cell ` and making a
present blank cell look like a missing defensive response. An explicit trace
marker can remove the ambiguity without changing the chart schema or engine.

## Acceptance

- The CLI renders `NO_CHANGE` chart cells with a visible blank marker.
- Other chart cells retain their current trace values.
- Synthetic tests cover both cases; no historical chart fixtures are added.
