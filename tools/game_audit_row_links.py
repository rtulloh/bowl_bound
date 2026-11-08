"""Engine-free agreement of supplied chart rows with command/tape observations.

Source/site declarations are structural inputs, never runtime/source authority.
Row input agreement requires a separately established typed chart inventory.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, cast

from . import game_audit_envelope as envelope
from . import game_audit_lookup as lookup


class RowLinkEvidenceError(ValueError):
    """Supplied row data disagrees with its recorded identities or chronology."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RowLinkEvidenceError(f"captured row {message}")


def _keys(value: Any, fields: set[str], label: str) -> None:
    _require(type(value) is dict and value.keys() == fields, f"{label} fields")


def _integer(value: Any) -> bool:
    return type(value) is int and value >= 0


def _text(value: Any) -> bool:
    return type(value) is str and bool(value.strip())


def _sha(value: Any) -> bool:
    return _text(value) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _content(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError) as error:
        raise RowLinkEvidenceError("captured row facts must be finite JSON") from error


def _roll(value: Any) -> dict[str, Any]:
    _keys(value, {"faces", "total"}, "physical roll")
    faces = value["faces"]
    _require(type(faces) is dict, "physical face object")
    offensive = faces.keys() == {"black", "white_one", "white_two"}
    draw = dict(number=1, kind="offensive" if offensive else "defensive", **value)
    if offensive:
        _require(all(type(v) is int for v in faces.values()), "physical face types")
        draw["direct_sum"] = sum(faces.values())
    lookup.audit_physical_draws([draw])
    return {key: item for key, item in draw.items() if key != "number"}


def _metadata(block: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sources = {}
    _require(type(block["sources"]) is list and bool(block["sources"]), "source declarations")
    for source in block["sources"]:
        _keys(
            source,
            {"module", "module_file", "module_spec_origin", "path", "source_sha256"},
            "source",
        )
        source = cast(dict[str, Any], source)
        _require(
            all(_text(value) for value in source.values()) and _sha(source["source_sha256"]),
            "source types",
        )
        _require(source["module"] not in sources, "duplicate source")
        sources[source["module"]] = source
    sites = {}
    _require(type(block["sites"]) is list and bool(block["sites"]), "site declarations")
    fields = {
        "id",
        "module",
        "function",
        "table",
        "chart_slot",
        "record_slot",
        "roll_slot",
        "line",
        "path",
        "source_sha256",
    }
    for site in block["sites"]:
        _keys(site, fields, "site")
        site = cast(dict[str, Any], site)
        _require(
            _integer(site["line"])
            and site["line"] > 0
            and all(_text(site[k]) for k in fields - {"line"}),
            "site types",
        )
        _require(
            site["table"]
            in {"offense", "defense", "supplemental", "special_teams", "pat_outcomes"},
            "site table",
        )
        source = sources.get(site["module"])
        _require(
            source is not None
            and site["path"] == source["path"]
            and site["source_sha256"] == source["source_sha256"],
            "site/source mismatch",
        )
        _require(site["id"] not in sites, "duplicate site")
        sites[site["id"]] = site
    aliases = set()
    parents = {(site["module"], site["function"]) for site in sites.values()}
    _require(type(block["aliases"]) is list and bool(block["aliases"]), "alias declarations")
    for alias in block["aliases"]:
        _keys(alias, {"module", "name", "function_module", "function_name"}, "alias")
        alias = cast(dict[str, Any], alias)
        _require(all(_text(v) for v in alias.values()), "alias types")
        _require((alias["function_module"], alias["function_name"]) in parents, "alias parent")
        key = alias["module"], alias["name"]
        _require(key not in aliases, "duplicate alias")
        aliases.add(key)
    return sites


def _tapes(capture: dict[str, Any], block: dict[str, Any]) -> tuple[dict[int, Any], dict[int, Any]]:
    typed = capture["typed_capture"]
    draws = typed["draws"]
    lookup.audit_physical_draws(draws)
    initial = {}
    _require(type(block["initial_tapes"]) is list, "initial tapes inventory")
    for tape in block["initial_tapes"]:
        _keys(tape, {"game_number", "position", "replaying", "recorded_rolls"}, "initial tape")
        game = tape["game_number"]
        _require(_integer(game) and game > 0 and game not in initial, "initial object identity")
        _require(
            _integer(tape["position"])
            and type(tape["replaying"]) is bool
            and type(tape["recorded_rolls"]) is list,
            "initial tape types",
        )
        _require(tape["position"] <= len(tape["recorded_rolls"]), "initial position")
        initial[game] = tape
    objects, commands = {}, {}
    for command in typed["commands"]:
        game = command["game_number"]
        before, after = command["before"]["tape"], command["after"]["tape"]
        if game not in objects:
            _require(game in initial, "missing initial tape")
            source = initial[game]
            _require(
                source["position"] == before["position"]
                and source["replaying"] is before["replaying"]
                and len(source["recorded_rolls"]) == before["roll_count"],
                "initial tape/boundary mismatch",
            )
            objects[game] = dict(
                initial_count=len(source["recorded_rolls"]),
                initial_consumed=len(source["recorded_rolls"])
                if not source["replaying"]
                else source["position"],
                tape=[
                    dict(roll=_roll(roll), draw_number=None, command_number=None)
                    for roll in source["recorded_rolls"]
                ],
            )
        state = objects[game]
        _require(len(state["tape"]) == before["roll_count"], "before tape count")
        for index in range(*command["draw_range"]):
            state["tape"].append(
                dict(
                    roll={key: item for key, item in draws[index].items() if key != "number"},
                    draw_number=index + 1,
                    command_number=command["number"],
                )
            )
        _require(len(state["tape"]) == after["roll_count"], "after tape count")
        commands[command["number"]] = dict(command=command, tape_end=len(state["tape"]))
    _require(initial.keys() == objects.keys(), "orphan initial tape")
    return objects, commands


def audit_row_links(
    capture: dict[str, Any], inventory: lookup.LookupInventory | None
) -> dict[str, int]:
    """Check supplied links and optional input agreement, never omitted events."""
    try:
        return _audit(capture, inventory)
    except (lookup.LookupEvidenceError, envelope.CaptureEvidenceError) as error:
        raise RowLinkEvidenceError(f"captured row {error}") from error


def _audit(capture: dict[str, Any], inventory: lookup.LookupInventory | None) -> dict[str, int]:
    _require("lookup" not in capture, "simultaneous legacy/new row inventories")
    _require("typed_capture" in capture, "missing command envelope")
    envelope.audit_capture_links(capture)
    block = capture["lookup_rows"]
    _keys(
        block,
        {
            "version",
            "sites",
            "events",
            "errors",
            "usable",
            "qualification",
            "sources",
            "aliases",
            "initial_tapes",
            "exercised_sites",
            "site_status",
            "scope",
        },
        "block",
    )
    _require(type(block["version"]) is str and block["version"] in {"1", "2"}, "version")
    _require(
        block["usable"] is True and type(block["errors"]) is list and not block["errors"],
        "producer failure",
    )
    _require(
        block["qualification"] == "UNVERIFIED" and _text(block["scope"]), "raw qualification/scope"
    )
    _content(block)
    sites = _metadata(block)
    objects, commands = _tapes(capture, block)
    _require(type(block["events"]) is list, "events inventory")
    counts: Counter[str] = Counter()
    linked = compared = typed_checked = prewindow = 0
    last_command = last_frontier = 0
    fields = {
        "number",
        "command_number",
        "game_number",
        "site_id",
        "address",
        "facts",
        "chart_binding",
        "record_binding",
        "draw_binding",
        "roll",
    }
    if block["version"] == "2":
        fields.add("captured_draw_frontier")
    for number, event in enumerate(block["events"], 1):
        _keys(event, fields, "event")
        _require(type(event["number"]) is int and event["number"] == number, "event numbering")
        command_number, game = event["command_number"], event["game_number"]
        _require(
            _integer(command_number)
            and command_number in commands
            and command_number >= last_command,
            "event command",
        )
        last_command = command_number
        context = commands[command_number]
        command = context["command"]
        _require(type(game) is int and game == command["game_number"], "event object")
        _require(_text(event["site_id"]) and event["site_id"] in sites, "unknown site")
        site = sites[event["site_id"]]
        counts[site["id"]] += 1
        for field in ("chart_binding", "record_binding"):
            _require(
                type(event[field]) is str and event[field] in {"BOUND", "AMBIGUOUS", "MISSING"},
                "record/chart binding",
            )
        address = event["address"]
        _require(type(address) is dict, "address object")
        normalized = dict(address)
        if event["chart_binding"] != "BOUND":
            _require(address.get("team_id") is None, "unbound team identity")
            normalized["team_id"] = "unbound"
        lookup._address(normalized)
        table = "pat" if site["table"] == "pat_outcomes" else site["table"]
        _require(address["table"] == table, "site/address table mismatch")
        lookup._facts(event["facts"], table == "pat")
        if event["chart_binding"] == "BOUND":
            _require(
                address["team_id"] in {team["id"] for team in command["before"]["teams"].values()},
                "foreign team",
            )
            if inventory is not None:
                inventory.check(address, event["facts"])
                compared += 1
        roll = _roll(event["roll"])
        _require(
            roll["kind"] == ("defensive" if table == "defense" else "offensive")
            and roll["total"] == address["roll"],
            "row roll/address mismatch",
        )
        binding = event["draw_binding"]
        _keys(binding, {"status", "tape_indices", "captured_draw_numbers"}, "draw binding")
        status = binding["status"]
        _require(
            type(status) is str
            and status in {"BOUND", "PREWINDOW", "AMBIGUOUS", "MISSING", "UNOBSERVED"},
            "draw binding status",
        )
        positions, draws = binding["tape_indices"], binding["captured_draw_numbers"]
        for values in (positions, draws):
            _require(
                type(values) is list
                and all(_integer(v) for v in values)
                and values == sorted(set(values)),
                "draw reference types/order",
            )
        state = objects[game]
        for position in positions:
            _require(
                position < context["tape_end"]
                and _content(state["tape"][position]["roll"]) == _content(roll),
                "tape position/roll mismatch",
            )
        owned = {
            entry["draw_number"]: entry
            for entry in state["tape"]
            if entry["draw_number"] is not None
        }
        for draw in draws:
            _require(
                draw in owned
                and owned[draw]["command_number"] <= command_number
                and _content(owned[draw]["roll"]) == _content(roll),
                "foreign/future draw",
            )
        if status == "BOUND":
            _require(
                len(positions) == len(draws) == 1
                and state["tape"][positions[0]]["draw_number"] == draws[0],
                "bound draw mismatch",
            )
        elif status == "PREWINDOW":
            _require(
                len(positions) == 1
                and not draws
                and positions[0] < state["initial_consumed"]
                and state["tape"][positions[0]]["draw_number"] is None,
                "prewindow membership",
            )
            prewindow += 1
        elif status == "UNOBSERVED":
            _require(
                len(positions) == 1 and not draws and positions[0] >= state["initial_count"],
                "unobserved classification",
            )
        elif status == "MISSING":
            _require(not positions and len(draws) <= 1, "missing binding classification")
        else:
            _require(len(positions) > 1 or len(draws) > 1, "ambiguous binding classification")
        if block["version"] == "2":
            frontier = event["captured_draw_frontier"]
            _require(
                _integer(frontier)
                and command["draw_range"][0] <= frontier <= command["draw_range"][1]
                and frontier >= last_frontier
                and all(draw <= frontier for draw in draws)
                and all(
                    state["tape"][position]["draw_number"] is None
                    or state["tape"][position]["draw_number"] <= frontier
                    for position in positions
                ),
                "draw frontier",
            )
            last_frontier = frontier
        bound = event["chart_binding"] == event["record_binding"] == "BOUND" and status in {
            "BOUND",
            "PREWINDOW",
        }
        linked += bound and block["version"] == "2"
        typed_checked += bound and inventory is not None
    for field in ("exercised_sites", "site_status"):
        _require(
            type(block[field]) is dict and block[field].keys() == sites.keys(),
            "site exposure inventory",
        )
    for site in sites:
        _require(
            type(block["exercised_sites"][site]) is int
            and block["exercised_sites"][site] == counts[site],
            "site exposure count",
        )
        _require(
            block["site_status"][site] == ("OBSERVED" if counts[site] else "NOTRUN"),
            "site exposure status",
        )
    return dict(
        rows_observed=len(block["events"]),
        rows_linked=linked,
        rows_unverified=len(block["events"]) - linked,
        typed_rows_checked=typed_checked,
        typed_rows_unknown=len(block["events"]) - typed_checked,
        diagnostic_input_comparisons=compared,
        prewindow_rows=prewindow,
        physical_draws=len(capture["typed_capture"]["draws"]),
    )
