"""Independent JSON oracle for symbolic ordinary Priority Chart observations.

Authority: docs/priority-chart.md and explicit docs/rules-profile.md decisions.
This transcription imports no engine, parses no chart tokens and does not prove
lookup provenance, physical draw consumption or complete-game correctness.
"""

from typing import Any, cast


class PriorityEvidenceError(ValueError):
    """A typed observation disagrees with independent priority authority."""


# Independently transcribed printed rows/columns; no production table import.
_ROWS = (
    "positive",
    "negative",
    "parenthesized",
    "blank",
    "TD",
    "QR",
    "QT",
    "INC",
    "INT",
    "F",
    "OPTION",
    "PENALTY",
)
_COLUMNS = (
    "positive",
    "negative",
    "blank",
    "paren_positive",
    "paren_negative",
    "bracket_positive",
    "bracket_negative",
    "TD",
    "QR",
    "QT",
    "INT",
    "F",
    "INC",
)
_MATRIX = (
    "ADD ADD ADD D D D D D D D D D INC",
    "ADD ADD ADD D D D D D D D D D INC",
    "O O O O O D D D O O O O O",
    "ADD ADD ADD D D D D D D D D D INC",
    "O O O D D D D D D D D D INC",
    "ADD ADD ADD D D D D D D D D D INC",
    "O O O D D D D D D D D D INC",
    "INC INC INC D D D D D D D D D INC",
    "O O O INC INT_MIN INC INT_MIN INC QT O INT_MIN O O",
    "O O O F_DEF F_MIN F_DEF F_MIN F_ENDZONE O O D F_MIN O",
    "OPTION OPTION OPTION OPTION OPTION OPTION OPTION OPTION OPTION OPTION OPTION OPTION OPTION",
    "PENALTY PENALTY PENALTY PENALTY PENALTY PENALTY PENALTY "
    "PENALTY PENALTY PENALTY PENALTY PENALTY PENALTY",
)
_VARIABLES = {
    "variable_ds": "DS",
    "variable_x": "X",
    "variable_t1": "T1",
    "variable_t2": "T2",
    "variable_t3": "T3",
}
_SYMBOLS = {
    "no_change": "blank",
    "touchdown": "TD",
    "incomplete": "INC",
    "B": "positive",
    "QR": "QR",
    "QT": "QT",
    "interception": "INT",
    "fumble": "F",
    "SOP": "OPTION",
    "BLP": "OPTION",
    "penalty": "PENALTY",
}
_PENDING = {*_VARIABLES, "B", "QR", "QT", "SOP", "BLP", "penalty", "interception", "fumble"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PriorityEvidenceError(message)


def _cell(value: Any, label: str) -> tuple[dict[str, Any], str]:
    """Validate normalized semantic operands without consulting a codec or prose."""
    fields = {
        "kind",
        "yards",
        "variable",
        "variable_multiplier",
        "priority",
        "out_of_bounds",
        "penalty",
    }
    _require(isinstance(value, dict) and fields <= value.keys(), f"{label}: missing typed facts")
    kind, yards, variable, multiplier = (
        value[key] for key in ("kind", "yards", "variable", "variable_multiplier")
    )
    _require(type(kind) is str and kind in {"yards", *_VARIABLES, *_SYMBOLS}, f"{label}: kind")
    _require(yards is None or type(yards) is int, f"{label}: yards")
    _require(type(value["out_of_bounds"]) is bool, f"{label}: out_of_bounds")
    _require(
        type(value["priority"]) is str
        and value["priority"] in {"normal", "parenthesized", "bracketed"},
        f"{label}: priority",
    )
    has_variable = variable is not None or multiplier is not None
    if has_variable:
        _require(
            type(variable) is str
            and variable in set(_VARIABLES.values())
            and type(multiplier) is int
            and multiplier != 0,
            f"{label}: variable distance",
        )
    if kind == "yards":
        _require(type(yards) is int and not has_variable, f"{label}: fixed numeric distance")
    elif kind in _VARIABLES:
        _require(
            variable == _VARIABLES[kind] and has_variable and yards is None,
            f"{label}: variable reference",
        )
    elif kind in {"interception", "fumble"}:
        _require((type(yards) is int) != has_variable, f"{label}: turnover distance")
    else:
        _require(yards is None and not has_variable, f"{label}: unexpected distance")
    penalty = value["penalty"]
    if kind == "penalty":
        _require(isinstance(penalty, dict), f"{label}: penalty")
        _require(
            {"team", "code", "yards", "variable", "variable_multiplier"} <= penalty.keys(),
            f"{label}: penalty facts",
        )
        _require(
            type(penalty["team"]) is str and penalty["team"] in {"offense", "defense"},
            f"{label}: penalty team",
        )
        _require(
            type(penalty["code"]) is str
            and penalty["code"] in {"fixed", "S", "R", "PI", "5Y", "5X"},
            f"{label}: penalty code",
        )
        py, pv, pm = (penalty[k] for k in ("yards", "variable", "variable_multiplier"))
        _require(py is None or type(py) is int, f"{label}: penalty yards")
        if penalty["code"] in {"S", "R", "5Y", "5X"}:
            _require(py is pv is pm is None, f"{label}: penalty distance")
        else:
            variable_ok = (
                type(pv) is str and pv in set(_VARIABLES.values()) and type(pm) is int and pm != 0
            )
            _require(
                (type(py) is int and pv is pm is None) or (py is None and variable_ok),
                f"{label}: penalty distance",
            )
            if penalty["code"] == "fixed":
                _require(type(py) is int and py > 0, f"{label}: fixed penalty distance")
            else:
                _require(penalty["team"] == "defense", f"{label}: PI team")
    else:
        _require(penalty is None, f"{label}: unexpected penalty")
    _require(
        not value["out_of_bounds"] or kind in {"yards", "no_change", *_VARIABLES},
        f"{label}: invalid out_of_bounds kind",
    )
    return value, kind


def _coordinate(value: Any, defensive: bool) -> tuple[dict[str, Any], str]:
    label = "defense" if defensive else "offense"
    cell, kind = _cell(value, label)
    decoration = cell["priority"]
    if kind == "yards" or kind in _VARIABLES:
        negative = (cell["yards"] is not None and cell["yards"] < 0) or (
            cell["variable_multiplier"] is not None and cell["variable_multiplier"] < 0
        )
        sign = "negative" if negative else "positive"
        if not defensive:
            _require(decoration != "bracketed", "offense: bracketed numeric row unavailable")
            if decoration == "parenthesized":
                _require(not negative, "offense: parenthesized negative row unavailable")
                return cell, "parenthesized"
            return cell, sign
        return cell, {"normal": "", "parenthesized": "paren_", "bracketed": "bracket_"}[
            decoration
        ] + sign
    if defensive and kind == "B" and decoration == "parenthesized":
        return cell, "paren_breakaway"
    _require(decoration == "normal" or (defensive and kind == "touchdown"), f"{label}: decoration")
    _require(
        not defensive or kind not in {"B", "SOP", "BLP", "penalty"},
        "defense: result has no ordinary priority column",
    )
    return cell, _SYMBOLS[kind]


def expected_priority(offense: Any, defense: Any) -> dict[str, Any]:
    """Derive symbolic priority solely from the independent rule transcription."""
    offense, row = _coordinate(offense, False)
    defense, column = _coordinate(defense, True)
    if column == "paren_breakaway":
        operation = {"parenthesized": "O", "OPTION": "OPTION", "PENALTY": "PENALTY"}.get(row, "D")
    else:
        operation = _MATRIX[_ROWS.index(row)].split()[_COLUMNS.index(column)]
    result: dict[str, Any] = dict(
        operation=operation,
        source="priority_chart",
        kind=None,
        yards=None,
        pending=False,
        offense=offense,
        defense=defense,
        offense_category="B" if offense["kind"] == "B" else row,
        defense_category=column,
        out_of_bounds=False,
        penalty=None,
        defensive_end_zone_depth=None,
    )
    if operation in {"O", "D", "OPTION", "PENALTY"}:
        selected = defense if operation == "D" else offense
        result.update(
            source="defense" if operation == "D" else "offense",
            kind=selected["kind"],
            yards=selected["yards"],
            pending=selected["kind"] in _PENDING,
            out_of_bounds=selected["out_of_bounds"],
            penalty=selected["penalty"],
        )
    elif operation in {"INC", "QT"}:
        result.update(kind="incomplete" if operation == "INC" else "QT", pending=operation == "QT")
    elif operation == "ADD":
        result.update(
            source="both", out_of_bounds=offense["out_of_bounds"] or defense["out_of_bounds"]
        )
        result["pending"] = offense["kind"] in _PENDING or defense["kind"] in _PENDING
        if offense["kind"] in {"B", "QR"}:
            result["kind"] = offense["kind"]
        elif offense["kind"] not in _VARIABLES and defense["kind"] not in _VARIABLES:
            result.update(kind="yards", yards=(offense["yards"] or 0) + (defense["yards"] or 0))
    else:
        result.update(
            source="both", pending=True, kind="interception" if operation == "INT_MIN" else "fumble"
        )
        if operation == "F_ENDZONE":
            result["defensive_end_zone_depth"] = 1
        elif operation == "F_DEF":
            result["yards"] = defense["yards"]
        elif offense["yards"] is not None and defense["yards"] is not None:
            result["yards"] = min(offense["yards"], defense["yards"])
    return result


def _same_fact(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _same_fact(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _same_fact(a, b) for a, b in zip(actual, expected, strict=True)
        )
    return actual == expected


def audit_priority(evidence: Any) -> int:
    """Check supplied typed observations; do not imply capture completeness."""
    _require(
        isinstance(evidence, dict) and evidence.get("version") == "1", "priority evidence: version"
    )
    events = evidence.get("events")
    _require(
        isinstance(events, list) and bool(events), "priority evidence: nonempty events required"
    )
    events = cast(list[dict[str, Any]], events)
    for number, event in enumerate(events, 1):
        prefix = f"priority event {number}"
        _require(
            isinstance(event, dict)
            and type(event.get("number")) is int
            and event["number"] == number,
            f"{prefix}: identity",
        )
        try:
            expected = expected_priority(event.get("offense"), event.get("defense"))
        except PriorityEvidenceError as error:
            raise PriorityEvidenceError(f"{prefix}: {error}") from error
        observed = event.get("result")
        _require(isinstance(observed, dict), f"{prefix}: result")
        observed = cast(dict[str, Any], observed)
        for field, value in expected.items():
            actual = observed.get(field)
            _require(
                field in observed and _same_fact(actual, value),
                f"{prefix}: {field} differs",
            )
    return len(events)
