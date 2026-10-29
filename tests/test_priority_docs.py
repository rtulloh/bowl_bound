"""Keep the human-readable chart equal to the independently transcribed test matrix."""

from pathlib import Path

from tests.priority_matrix import PRIORITY_MATRIX


def test_ascii_chart_matches_every_independent_expected_intersection() -> None:
    text = (Path(__file__).resolve().parents[1] / "docs/priority-chart.md").read_text(
        encoding="utf-8"
    )
    block = text.split("<!-- priority-matrix:start -->")[1].split("<!-- priority-matrix:end -->")[0]
    rows = [line for line in block.splitlines() if "|" in line][1:]
    aliases = {"OPT": "OPTION", "PEN": "PENALTY"}
    parsed = tuple(
        tuple(aliases.get(x.strip(), x.strip()) for x in line.split("|")[1:]) for line in rows
    )
    assert len(parsed) == 12
    assert parsed == PRIORITY_MATRIX


def test_source_comment_chart_has_every_printed_coordinate() -> None:
    text = (Path(__file__).resolve().parents[1] / "bowl_bound/resolution.py").read_text(
        encoding="utf-8"
    )
    lines = [line for line in text.splitlines() if line.startswith("# |")][1:]
    rows = [tuple(x.strip() for x in line.split("|")[2:-1]) for line in lines]
    offense = (
        "# / B",
        "-#",
        "O(#)",
        "blank",
        "TD",
        "QR",
        "QT",
        "INC",
        "INT #",
        "F #",
        "OPT",
        "PEN",
    )
    defense = (
        "#",
        "-#",
        "blank",
        "(#)",
        "(-#)",
        "[#]",
        "[-#]",
        "TD",
        "QR",
        "QT",
        "INT #",
        "F #",
        "INC",
    )
    aliases = {
        "INT_MIN": "INT<",
        "F_DEF": "Fdef",
        "F_MIN": "F<",
        "F_ENDZONE": "FdEZ",
        "OPTION": "OPT",
        "PENALTY": "PEN",
    }
    assert len(rows) == 12
    for row, expected in enumerate(PRIORITY_MATRIX):
        assert len(rows[row]) == 13
        for col, op in enumerate(expected):
            token = (
                offense[row] if op == "O" else defense[col] if op == "D" else aliases.get(op, op)
            )
            assert rows[row][col] == token, (row + 1, col + 1)
