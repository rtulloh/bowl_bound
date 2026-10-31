# Chart-cell normalization

Milestone 4 implements `normalize_cell(provenance, ChartColor)` in
`bowl_bound.normalization`, using the legends on printed pp. 32–33 and 35 of
the local rulebook identified in [the rules profile](rules-profile.md).

The caller supplies an explicitly classified red, green, white, black, or yellow
background. PDF color extraction, supported color signatures, and unsupported-layout
detection belong to the PDF importer. It accepts exact canonical RGB colors and a small,
verified DeviceCMYK palette after deterministic conversion; it does not choose a nearest
color or guess from arbitrary RGB values. Original text, source hash, filename, page,
bounds, and normalized RGB evidence remain unchanged in provenance.

## Supported facts

- Ordinary numeric/variable results: red gives negative yardage, green positive.
  A printed minus on red is not negated twice. An explicit conflicting sign fails.
- White blanks mean no change; black blanks mean incomplete. Red, green, or yellow
  blanks fail rather than becoming zero. A white `*`/`†` means no change with marker.
- Parentheses and brackets become priority facts. A trailing `*` or `†` becomes
  the out-of-bounds/no-punt-return marker. These facts do not resolve priority/timing.
- DS, X (including alias T0), T1, T2, T3 become variable references, not constants
  or extra rolls. No dice are rolled during normalization.
- F, INT, BK locations use their printed signs, never background-based negation.
  Bare F explicitly means F+0, as confirmed by the project owner; this is a known
  shorthand, not a missing-data fallback. Preserve the bare source token in provenance.
  INT/BK without locations still fail, and empty cells never become fumbles or zero yards.
- B/QR/QT/SOP/BLP/TD, punt FG/KO redirects, NG, and INC are explicit kinds with
  legend colors. FG*/KO* retain the no-return marker.
- Yellow OFF/DEF fixed/S/R/5Y/5X and PI fixed/variable entries become penalty data.
  DEF5X remains 5X: its rules-policy interpretation belongs to the engine.

Case, surrounding whitespace, whitespace after OFF/DEF/PI/INT/BK/F prefixes or
a sign, and Unicode minus/en-dash are canonicalized only for parsing. Internal
whitespace in digits or alphabetic tokens is rejected, not joined. Compact forms
like F+6, FX, and DEF5 are accepted deliberately; whitespace is not required where
the prefix and location are unambiguous. Other dash glyphs are unsupported.
Malformed wrappers, repeated markers, unknown forms, and unsupported color/token
combinations raise `NormalizationError` with a safe page-and-reason message; its
attributes retain the page and bounding box. The caller's `Provenance` retains the
filename and original text for private local review. Legacy graphical circled priority
is not decoded from a text glyph; an importer for that layout must supply explicit
evidence or reject the layout.

Keep provenance and local import reports private; do not log or display source filenames
or source text. API/UI adapters should expose only the safe error message. Priority
wrappers are supported on numeric and variable entries, TD entries (including [TD],
explicitly listed in the legend), and parenthesized `B` only in defensive chart cells.
The owner-approved Milestone 26 interpretation treats that defensive result as an
override that gives the offense a Breakaway reroll; other decorated named results remain
unsupported. PI means defensive pass interference per the legend; no inference from NFL
behavior is used.
Leading zeros and signed zero are accepted as integer forms; explicit signs must
still agree with the color. No artificial yardage magnitude limit is imposed here.
PUNT_REFERENCE is reserved in the schema and is not produced by this grammar.

The result is a [schema-v1 cell](chart-schema.md). Column placement is validated when
constructing the offense/defense/supplemental/special-team record. This function
does not normalize PAT dice-number-column colors, metadata, or privileges, nor
apply published team errata. Those belong to import validation and rules policies.

## Synthetic example

```python
from bowl_bound.models import BoundingBox, Provenance
from bowl_bound.normalization import ChartColor, normalize_cell

evidence = Provenance("a" * 64, "synthetic.pdf", 1, BoundingBox(0, 0, 1, 1), "F +6", (255, 0, 0))
assert normalize_cell(evidence, ChartColor.RED).yards == 6
```

All committed tests use synthetic evidence. No historical charts or PDF tooling
are needed to run them.
