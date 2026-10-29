# Vector cell extraction — supported profile (Milestone 5b)

This is a geometric extraction stage, not a team
export or independent historical-data reconciliation (Milestones 5c and 6).

## Boundaries

- `tools/pdf_import/layout.py` maps a documented letter-page coordinate profile to
  chart addresses. Vertical boundaries come from actual thin vector rectangles,
  allowing different column widths on the two offense pages; printed roll anchors
  must match the supported row profile instead of guessing missing rows.
- `tools/pdf_import/cells.py` extracts text, rotation, background color, and provenance
  from supplied bounds. It does not interpret chart tokens or football rules.
- `bowl_bound.normalization` later converts text plus classified color into facts.

The initial profile uses portrait 612×792-point offense pages with 30 rows (10–39),
9 play columns and QT/QR/B columns, followed by landscape 792×612-point
defense/special pages. Defense has 6 groups × 5 rolls × 9 plays; special teams has
30 rows × 6 columns. The special-chart dice-number column supplies 30 PAT backgrounds.
Coordinates describe layout geometry only; committed fixtures contain synthetic tokens.

## Evidence and ambiguity

Thin black rectangles may be grid borders rather than black result backgrounds.
Background fills can span multiple cells; the extractor must sample the whole interior,
not assume a rectangle belongs to just one cell. Missing geometry, partial coverage,
ambiguous overlaps, and text straddling a cell boundary must fail explicitly. A white
blank requires positive grid/background evidence; no missing cell becomes zero yards.

Extraction preserves the PDF filename and SHA-256, one-based page number, cell
position, original text, rotation, and RGB background. This evidence is private for
historical teams. Do not commit cell dumps or local extraction reports.

Unsupported curve/image objects intersecting a cell interior fail explicitly. Non-finite
object geometry is rejected before filtering. RGB and grayscale channels must be in
the PDF unit range; declared color spaces other than DeviceRGB/DeviceGray fail.
When pdfplumber supplies no color-space metadata, unit-channel shape is the available
evidence; indexed/spot colors, clipping paths, and transparency are not supported
by this initial profile. The source must use opaque vector rectangles.
Rotated text is ordered along its reading axis, retaining geometric gaps and line breaks.

## Validation

Public synthetic PDFs cover colors, rotation, grid borders, merged fills, blanks,
missing geometry, and ambiguity. Local verification against the first two-team PDF
stays outside test collection and reports aggregate counts without exporting charts.
A successful aggregate count alone is not full chart verification; Milestone 6
independently reconciles every position and dedicated PAT entry.

## Profile tolerances and group boundaries

Vertical grid candidates must be narrow (at most 3 points), at least 14 points long,
and overlap the chart row region. Centers within 0.5 points are clustered; the
resulting 16 offense or 20 defense boundaries must match the documented profile
within 2.6 points (variable-width offense) or 0.75 points (defense). Extra/missing
columns and foreign decorative lines fail rather than shifting chart addresses.

On offense, the left dice column precedes nine plays, then a gap separates the
three supplemental columns; the right dice column is not another chart result.
On defense, the formation label and dice columns precede nine plays, then a gap
separates six special-team columns. The right edge of special teams is also the
left edge of the PAT dice-number column. PAT text remains the printed roll number;
only later import validation converts that column’s white/red background to PAT facts.

Printed row centers must remain within 1.5 points of the profile; defense and
special-team roll anchors must align within 0.5 points. Extraction additionally
requires positive grid/fill evidence for each cell; anchors alone do not prove a
background. Full content reconciliation remains Milestone 6.

## Independent local cross-checks

Authorized local Paydirt PDF printouts can be compared with their already-extracted
CSV references to check generic text/color extraction. They have a separate layout
adapter, are not accepted as Bowl Bound teams, and do not introduce an NFL rules
dependency. Keep printouts, reference data, adapters, and detailed comparison reports
in ignored `private-data/verification/`; synthetic PDF regressions remain the public
acceptance gate. Report matches, mismatches, and extraction errors separately rather
than treating unexamined cells as matches.
