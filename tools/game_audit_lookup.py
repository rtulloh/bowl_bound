"""Independent physical-dice and frozen typed chart lookup agreement.

No engine/codec imports or token parsing. An externally pinned inventory binds
bytes, not source truth or capture completeness. Authority: docs/dice.md and the
documented v1 chart axes. Normalized color is compared as a fact, never interpreted.
"""

from itertools import product
from typing import Any, cast

from .game_audit_priority import _same_fact


class LookupEvidenceError(ValueError):
    """Supplied lookup evidence is incomplete or disagrees with its inventory."""


# Independent transcription of Basic IV-1; duplicates are physical multiplicities.
OFFENSIVE_FACES = ((1, 2, 2, 3, 3, 3), (0, 0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5))
DEFENSIVE_FACES = ((1, 1, 1, 2, 2, 3), (0, 0, 0, 0, 1, 2))
_SPECIAL = ("kickoff", "kickoff_return", "punt", "punt_return", "field_goal", "interception_return")
_ADDRESS = {"team_id", "season", "table", "play", "column", "formation", "roll"}
_FACTS = {
    "kind",
    "yards",
    "variable",
    "variable_multiplier",
    "priority",
    "out_of_bounds",
    "penalty",
    "chart_color",
}
_KINDS = {
    "yards",
    "no_change",
    "incomplete",
    "touchdown",
    "variable_ds",
    "variable_x",
    "variable_t1",
    "variable_t2",
    "variable_t3",
    "B",
    "QR",
    "QT",
    "SOP",
    "BLP",
    "penalty",
    "fumble",
    "interception",
    "blocked_kick",
    "punt_reference",
    "field_goal_reference",
    "kickoff_reference",
    "NG",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LookupEvidenceError(f"lookup {message}")


def _address(value: Any) -> tuple[Any, ...]:
    _require(type(value) is dict and value.keys() == _ADDRESS, "address fields")
    team, season, table, play, column, formation, roll = (
        value[k] for k in ("team_id", "season", "table", "play", "column", "formation", "roll")
    )
    _require(type(team) is str and bool(team.strip()), "team identity")
    _require(type(season) is int and season > 0, "season identity")
    _require(
        type(table) is str
        and table in {"offense", "defense", "supplemental", "special_teams", "pat"},
        "table",
    )
    numeric_play = table in {"offense", "defense"}
    _require(
        (type(play) is int and 1 <= play <= 9) if numeric_play else play is None, "play address"
    )
    if table == "supplemental":
        _require(type(column) is str and column in {"B", "QR", "QT"}, "column address")
    elif table == "special_teams":
        _require(type(column) is str and column in _SPECIAL, "column address")
    else:
        _require(column is None, "unexpected column address")
    _require(
        (type(formation) is str and formation in tuple("ABCDEF"))
        if table == "defense"
        else formation is None,
        "formation address",
    )
    _require(
        type(roll) is int and (1 <= roll <= 5 if table == "defense" else 10 <= roll <= 39),
        "roll address",
    )
    return team, season, table, play, column, formation, roll


def _facts(value: Any, pat: bool) -> None:
    """Check structural types only; pinned equality cannot certify codec validity.

    Kind/distance/penalty consistency and allowed chart placements remain separate
    codec/model checks. A consistently invalid inventory is not source authority.
    """
    if pat:
        _require(
            type(value) is dict and value.keys() == {"good"} and type(value["good"]) is bool,
            "PAT facts",
        )
        return
    _require(type(value) is dict and value.keys() == _FACTS, "typed fact fields")
    _require(type(value["kind"]) is str and value["kind"] in _KINDS, "typed kind")
    for key in ("yards", "variable_multiplier"):
        _require(value[key] is None or type(value[key]) is int, f"typed {key}")
    _require(
        value["variable"] is None
        or (type(value["variable"]) is str and value["variable"] in {"DS", "X", "T1", "T2", "T3"}),
        "typed variable",
    )
    _require(
        type(value["priority"]) is str
        and value["priority"] in {"normal", "parenthesized", "bracketed"},
        "typed priority",
    )
    _require(type(value["out_of_bounds"]) is bool, "typed out_of_bounds")
    _require(
        value["chart_color"] is None
        or (
            type(value["chart_color"]) is str
            and value["chart_color"] in {"red", "green", "white", "black", "yellow"}
        ),
        "typed chart_color",
    )
    penalty = value["penalty"]
    if penalty is not None:
        _require(
            type(penalty) is dict
            and penalty.keys() == {"team", "code", "yards", "variable", "variable_multiplier"},
            "penalty fields",
        )
        penalty = cast(dict[str, Any], penalty)
        _require(
            type(penalty["team"]) is str and penalty["team"] in {"offense", "defense"},
            "penalty team",
        )
        _require(
            type(penalty["code"]) is str
            and penalty["code"] in {"fixed", "PI", "S", "R", "5Y", "5X"},
            "penalty code",
        )
        for key in ("yards", "variable_multiplier"):
            _require(penalty[key] is None or type(penalty[key]) is int, f"penalty {key}")
        _require(
            penalty["variable"] is None
            or (
                type(penalty["variable"]) is str
                and penalty["variable"] in {"DS", "X", "T1", "T2", "T3"}
            ),
            "penalty variable",
        )


class LookupInventory:
    """Validate a complete address set, then compare immutable typed facts.

    This is data agreement, not a replacement chart codec or source qualification.
    The caller must separately establish expected input bytes and review authority.
    """

    def __init__(self, value: Any) -> None:
        from copy import deepcopy

        _require(
            type(value) is dict
            and value.keys() == {"version", "teams", "cells"}
            and type(value["version"]) is str
            and value["version"] in {"1", "2"},
            "inventory version/fields",
        )
        _require(type(value["teams"]) is list and bool(value["teams"]), "inventory teams")
        teams = set()
        self._recoveries: dict[tuple[str, int], tuple[str, int, int]] = {}
        for team in cast(list[dict[str, Any]], value["teams"]):
            fields = {"team_id", "season"}
            if value["version"] == "2":
                fields |= {"fingerprint", "object_sha256", "metadata_sha256", "recovery_range"}
            _require(type(team) is dict and team.keys() == fields, "inventory team fields")
            ident, season = team["team_id"], team["season"]
            _require(
                type(ident) is str and bool(ident.strip()) and type(season) is int and season > 0,
                "inventory team identity",
            )
            _require((ident, season) not in teams, "duplicate inventory team")
            teams.add((ident, season))
            if value["version"] == "2":
                for name in ("fingerprint", "object_sha256", "metadata_sha256"):
                    digest = team[name]
                    _require(
                        type(digest) is str
                        and len(digest) == 64
                        and all(char in "0123456789abcdef" for char in digest),
                        "recovery metadata SHA",
                    )
                interval: Any = team["recovery_range"]
                _require(
                    type(interval) is list
                    and len(interval) == 2
                    and all(type(endpoint) is int for endpoint in interval)
                    and 10 <= cast(int, interval[0]) <= cast(int, interval[1]) <= 39,
                    "recovery interval",
                )
                interval = cast(list[int], interval)
                self._recoveries[ident, season] = (team["fingerprint"], interval[0], interval[1])
        expected = set()
        for team, season in teams:
            for play, roll in product(range(1, 10), range(10, 40)):
                expected.add((team, season, "offense", play, None, None, roll))
            for column, roll in product(("B", "QR", "QT"), range(10, 40)):
                expected.add((team, season, "supplemental", None, column, None, roll))
            for formation, play, roll in product("ABCDEF", range(1, 10), range(1, 6)):
                expected.add((team, season, "defense", play, None, formation, roll))
            for column, roll in product(_SPECIAL, range(10, 40)):
                expected.add((team, season, "special_teams", None, column, None, roll))
            for roll in range(10, 40):
                expected.add((team, season, "pat", None, None, None, roll))
        _require(type(value["cells"]) is list, "inventory cells")
        self._cells = {}
        for row in cast(list[dict[str, Any]], value["cells"]):
            _require(type(row) is dict and row.keys() == {"address", "facts"}, "inventory record")
            key = _address(row["address"])
            _require(key not in self._cells, "duplicate inventory address")
            _facts(row["facts"], key[2] == "pat")
            self._cells[key] = deepcopy(row["facts"])
        _require(self._cells.keys() == expected, "incomplete or unexpected inventory address set")
        self._teams = frozenset(teams)
        self.team_count = len(teams)
        self.cell_count = len(self._cells)

    def recovery_interval(self, team_id: str, fingerprint: str) -> tuple[int, int] | None:
        """Return externally declared metadata only for a unique matching team.

        This binds supplied chart identity, not historical source truth. Version
        one inventories and absent/ambiguous teams supply no recovery authority.
        """
        entries = [value for (ident, _), value in self._recoveries.items() if ident == team_id]
        if len(entries) != 1:
            return None
        expected, lower, upper = entries[0]
        _require(type(fingerprint) is str and fingerprint == expected, "recovery fingerprint")
        return lower, upper

    def unique_season(self, team_id: str) -> int | None:
        """Return unique pinned metadata, never infer a year from a team label."""
        seasons = {season for ident, season in self._teams if ident == team_id}
        return next(iter(seasons)) if len(seasons) == 1 else None

    def check(self, address: Any, facts: Any) -> tuple[Any, ...]:
        """Compare exact typed payload at an independently validated address."""
        key = _address(address)
        _require(key in self._cells, "address absent from frozen inventory")
        _facts(facts, key[2] == "pat")
        _require(_same_fact(facts, self._cells[key]), "facts differ from frozen inventory")
        return key


def audit_physical_draws(values: Any) -> dict[int, tuple[str, int]]:
    """Check supplied ordered draws; an empty inventory proves no exposure."""
    _require(type(values) is list, "draw inventory")
    draws = {}
    for number, draw in enumerate(values, 1):
        _require(type(draw) is dict, f"draw {number} fields")
        _require(type(draw.get("number")) is int and draw["number"] == number, "draw numbering")
        kind = draw.get("kind")
        _require(type(kind) is str and kind in {"offensive", "defensive"}, "draw kind")
        offensive = kind == "offensive"
        names = ("black", "white_one", "white_two") if offensive else ("red", "green")
        faces = draw.get("faces")
        _require(type(faces) is dict and faces.keys() == set(names), "physical face fields")
        allowed = OFFENSIVE_FACES if offensive else DEFENSIVE_FACES
        _require(
            all(
                type(faces[k]) is int and faces[k] in values
                for k, values in zip(names, allowed, strict=True)
            ),
            "physical face",
        )
        faces = cast(dict[str, int], faces)
        total = (
            10 * faces["black"] + faces["white_one"] + faces["white_two"]
            if offensive
            else faces["red"] + faces["green"]
        )
        _require(type(draw.get("total")) is int and draw["total"] == total, "physical total")
        fields = {"number", "kind", "faces", "total"}
        if offensive:
            fields.add("direct_sum")
            _require(
                type(draw.get("direct_sum")) is int and draw["direct_sum"] == sum(faces.values()),
                "physical direct sum",
            )
        _require(draw.keys() == fields, "draw fields")
        draws[number] = kind, total
    return draws


def audit_lookup(evidence: Any, inventory: LookupInventory) -> dict[str, int]:
    """Validate supplied physical draws and chart lookups, not capture completeness."""
    _require(
        type(evidence) is dict
        and evidence.keys() == {"version", "draws", "events"}
        and evidence["version"] == "1",
        "evidence version/fields",
    )
    _require(type(evidence["draws"]) is list and bool(evidence["draws"]), "draw inventory")
    draws = audit_physical_draws(evidence["draws"])
    _require(type(evidence["events"]) is list and bool(evidence["events"]), "event inventory")
    linked = set()
    events = cast(list[dict[str, Any]], evidence["events"])
    for number, event in enumerate(events, 1):
        _require(
            type(event) is dict and event.keys() == {"number", "draw_number", "address", "facts"},
            "event fields",
        )
        _require(type(event["number"]) is int and event["number"] == number, "event numbering")
        event = cast(dict[str, Any], event)
        draw_number = event["draw_number"]
        _require(type(draw_number) is int and draw_number in draws, "event draw reference")
        key = inventory.check(event["address"], event["facts"])
        kind, total = draws[draw_number]
        _require(
            (kind == "defensive") == (key[2] == "defense") and total == key[-1],
            "physical draw/address disagreement",
        )
        linked.add(draw_number)
    return dict(
        draws_checked=len(draws),
        lookups_checked=len(events),
        draws_without_lookup=len(draws) - len(linked),
    )
