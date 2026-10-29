"""Independent transcription of the 2007 Bowl Bound Priority Chart.

Source: local docs/reference/bbrules2007.pdf, PDF p.37 / printed p.34,
visually checked against private-data/verification/rules/page37.png.
Rows and columns retain the printed grouping: positive yards/B is one row,
SOP/BLP is one row, and defensive (TD)/[TD] is one column. No production
module or historical team data is used to construct these expectations.

Codes:
    ADD: combine the offensive and defensive yardage.
    O: use the offensive result; D: use the defensive result.
    INC: incomplete pass (including the chart's black cells).
    INT_MIN: interception at the lesser of the two printed yardages.
    F_DEF: offensive fumble at the defensive yardage.
    F_MIN: fumble at the lesser of the two printed yardages.
    F_ENDZONE: offensive fumble in the defenders' end zone.
    OPTION: nullify defense and resolve SOP/BLP under Play 7/8.
    PENALTY: penalty procedure takes priority.

The offensive INT versus defensive QR intersection literally reads QT, not QR,
INT, or INC. The QT directive is retained explicitly rather than falsely selecting
the defensive QR result. Its supplemental execution belongs to Milestone 8.

Source qualifications / discrepancies (not silently reconciled):
* Printed p.3 / PDF p.6 gives (4) versus (-1) = 3 yards, describing the
  parentheses as offsetting. The p.34 chart instead prints the offensive
  (#) in that cell; this matrix follows the chart: O. Against defensive
  positive parentheses the chart explicitly says OFF. (#), also O.
* Printed p.4 / PDF p.7 explicitly gives offensive INT 28 versus defensive
  (TD) as INC, agreeing with the chart's black cell.
* Printed p.38 / PDF p.41 says all defensive (TD) were changed to [TD]
  because this result always overrides offense except penalties. That broad
  statement conflicts with the printed INT/TD = INC and F/TD = F DEF EZ
  cells and the SOP/BLP row. This matrix preserves the actual chart.
* Basic VI-9 and VI-10 (printed p.10 / PDF p.13) say to move the ball forward
  (+) or backward (-) by the shown yards before interception/fumble handling.
  Neither paragraph defines the Priority Chart's "< #" notation. The chart
  prints "INT at < #" for INT versus (-#), [-#], and INT; "F at < #" for
  F versus (-#), [-#], and F. MIN here transcribes that lesser-yardage
  instruction; no prose example independently settles signed comparison
  versus absolute-distance comparison. Signed comparison is consistent with
  VI-9/10, but should be an explicit rules-profile decision, not a guessed
  quotation from those paragraphs.
* Printed p.3 / PDF p.6 explicitly gives F +22 versus (TD) as a fumble one
  yard deep in the defenders' end zone. The chart itself only says F DEF EZ.
* Basic VI-12 (printed p.11 / PDF p.14) nullifies defense for SOP/BLP unless
  Advanced II.1, II.2 and/or II.3 applies; the chart mentions only Wild Card.
  OPTION entries represent the basic-rule branch, not advanced defenses.
* B and QR need subsequent offensive rolls under Basic VI-2 (printed p.6 /
  PDF p.9). ADD in their chart cells is not an instruction to invent numeric
  yardage for the unexpanded symbol.
"""

# Defensive columns, left to right. The last column is printed black/INC.
COLUMNS: tuple[str, ...] = (
    "positive_yards",
    "negative_yards",
    "blank",
    "parenthesized_positive",
    "parenthesized_negative",
    "bracketed_positive",
    "bracketed_negative",
    "touchdown",
    "quarterback_run",
    "quarterback_trapped",
    "interception",
    "fumble",
    "incomplete",
)

# Offensive rows, top to bottom, exactly as grouped in the printed chart.
ROWS: tuple[str, ...] = (
    "positive_yards_or_breakaway",
    "negative_yards",
    "parenthesized_positive",
    "blank",
    "touchdown",
    "quarterback_run",
    "quarterback_trapped",
    "incomplete",
    "interception",
    "fumble",
    "sprint_out_or_bootleg_pass",
    "penalty",
)

# Each tuple has exactly thirteen literal, independently transcribed entries.
PRIORITY_MATRIX: tuple[tuple[str, ...], ...] = (
    # positive yards / B
    ("ADD", "ADD", "ADD", "D", "D", "D", "D", "D", "D", "D", "D", "D", "INC"),
    # negative yards
    ("ADD", "ADD", "ADD", "D", "D", "D", "D", "D", "D", "D", "D", "D", "INC"),
    # parenthesized positive yards
    ("O", "O", "O", "O", "O", "D", "D", "D", "O", "O", "O", "O", "O"),
    # blank
    ("ADD", "ADD", "ADD", "D", "D", "D", "D", "D", "D", "D", "D", "D", "INC"),
    # TD
    ("O", "O", "O", "D", "D", "D", "D", "D", "D", "D", "D", "D", "INC"),
    # QR
    ("ADD", "ADD", "ADD", "D", "D", "D", "D", "D", "D", "D", "D", "D", "INC"),
    # QT
    ("O", "O", "O", "D", "D", "D", "D", "D", "D", "D", "D", "D", "INC"),
    # incomplete (black)
    ("INC", "INC", "INC", "D", "D", "D", "D", "D", "D", "D", "D", "D", "INC"),
    # INT: the QR column prints QT; see the module note.
    ("O", "O", "O", "INC", "INT_MIN", "INC", "INT_MIN", "INC", "QT", "O", "INT_MIN", "O", "O"),
    # F
    ("O", "O", "O", "F_DEF", "F_MIN", "F_DEF", "F_MIN", "F_ENDZONE", "O", "O", "D", "F_MIN", "O"),
    # SOP / BLP (basic rules only)
    (
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
        "OPTION",
    ),
    # PEN
    (
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
        "PENALTY",
    ),
)
