"""Opt-in subject observations at reviewed inline chart-row selection sites.

No expectations are derived here. Successful generator yields expose the actual
record, chart and roll; ambiguity remains explicit rather than guessed away.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import sys
from collections import Counter
from pathlib import Path
from types import CodeType, FrameType
from typing import Any, cast

from .game_audit_capture import _json_value

# Authored site inventory of current row-selection source. Ordinals count only
# chart-row generators in each enclosing function, not unrelated selectors.
_SITES = (
    ("resolution", "resolve_advanced_play", 0, "offense", "offense", "record", "off_roll"),
    ("resolution", "resolve_advanced_play", 1, "offense", "offense", "record", "option_roll"),
    ("resolution", "resolve_qb_sneak", 0, "offense", "offense", "record", "roll"),
    (
        "resolution",
        "resolve_razzle_dazzle_result",
        0,
        "offense",
        "offense",
        "record",
        "selected_roll",
    ),
    (
        "resolution",
        "resolve_razzle_dazzle_result",
        1,
        "defense",
        "defense",
        "record",
        "defensive_roll",
    ),
    (
        "resolution",
        "resolve_razzle_dazzle_result",
        2,
        "offense",
        "offense",
        "record",
        "option_roll",
    ),
    (
        "resolution",
        "resolve_razzle_dazzle_result",
        3,
        "offense",
        "offense",
        "record",
        "option_roll",
    ),
    ("resolution", "_supplemental_result", 0, "supplemental", "offense", "record", "roll"),
    ("resolution", "resolve_play", 0, "offense", "offense", "record", "off_roll"),
    ("resolution", "resolve_play", 1, "defense", "defense", "record", "def_roll"),
    ("resolution", "resolve_play", 2, "offense", "offense", "record", "option_roll"),
    ("penalties", "prepare_resolution", 0, "offense", "offense", "r", "roll"),
    ("penalties", "prepare_resolution", 1, "offense", "offense", "r", "option_roll"),
    ("special_teams", "SpecialTeamsPlay._roll", 0, "special_teams", "chart", "record", "roll"),
    ("turnovers", "_return_cell", 0, "special_teams", "chart", "record", "roll"),
    ("scoring", "resolve_pat", 0, "pat_outcomes", "chart", "outcome", "roll"),
)
_COLLECTIONS = {"offense", "defense", "supplemental", "special_teams", "pat_outcomes"}
_MODULES = ("resolution", "penalties", "special_teams", "turnovers", "scoring")
_CELL_FIELDS = (
    "kind",
    "yards",
    "variable",
    "variable_multiplier",
    "priority",
    "out_of_bounds",
    "penalty",
    "chart_color",
)


def _source_sites(tree: ast.AST) -> dict[str, list[ast.GeneratorExp]]:
    """Find declared chart-row generators; do not infer football meaning."""
    result: dict[str, list[ast.GeneratorExp]] = {}

    def visit(node: ast.AST, owners: tuple[str, ...]) -> None:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            owners = (*owners, node.name)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "next"
        ):
            if node.args and isinstance(node.args[0], ast.GeneratorExp):
                generator = node.args[0]
                iterable = generator.generators[0].iter
                if isinstance(iterable, ast.Attribute) and iterable.attr in _COLLECTIONS:
                    result.setdefault(".".join(owners), []).append(generator)
        for child in ast.iter_child_nodes(node):
            visit(child, owners)

    visit(tree, ())
    return result


class LookupRowCapture:
    """Observe selected row subjects; this producer cannot certify completeness."""

    def __init__(self, capture: Any) -> None:
        self.capture = capture
        self.events: list[dict[str, Any]] = []
        self.errors: list[dict[str, str]] = []
        self.sites: list[dict[str, Any]] = []
        self._codes: dict[CodeType, dict[str, Any]] = {}
        self._parents: list[tuple[Any, str, Any, CodeType]] = []
        self._sources: dict[Path, bytes] = {}
        self._modules: list[tuple[Any, str, str]] = []
        self._aliases: list[tuple[Any, str, Any]] = []
        self._draw_objects: list[tuple[Any, Any, int]] = []
        self._initial_objects: list[tuple[Any, list[Any], int, bool]] = []
        self.initial_tapes: list[dict[str, Any]] = []
        by_module: dict[str, dict[str, list[ast.GeneratorExp]]] = {}
        for short in _MODULES:
            module = importlib.import_module(f"bowl_bound.{short}")
            module_file = cast(str, module.__file__)
            path = Path(module_file).resolve()
            origin = getattr(getattr(module, "__spec__", None), "origin", None)
            if not isinstance(origin, str) or Path(origin).resolve() != path:
                raise ValueError("lookup-row module origin mismatch")
            content = path.read_bytes()
            self._sources[path] = content
            self._modules.append((module, module_file, origin))
            by_module[short] = _source_sites(ast.parse(content))
            expected = Counter(name for mod, name, *_ in _SITES if mod == short)
            if {name: len(nodes) for name, nodes in by_module[short].items()} != dict(expected):
                raise ValueError("lookup-row source site inventory changed")
        for short, name, ordinal, table, chart_slot, record_slot, roll_slot in _SITES:
            module = sys.modules[f"bowl_bound.{short}"]
            owner = module
            pieces = name.split(".")
            for piece in pieces[:-1]:
                owner = getattr(owner, piece)
            function = getattr(owner, pieces[-1])
            code = function.__code__
            node = by_module[short][name][ordinal]
            iterable = node.generators[0].iter
            if (
                not isinstance(iterable, ast.Attribute)
                or ast.unparse(iterable.value) != chart_slot
                or iterable.attr != table
                or ast.unparse(node.generators[0].target) != record_slot
                or ast.unparse(node.elt)
                != (record_slot if table == "pat_outcomes" else record_slot + ".cell")
            ):
                raise ValueError("lookup-row declared site shape changed")
            matches = [
                item
                for item in code.co_consts
                if isinstance(item, CodeType)
                and item.co_name == "<genexpr>"
                and item.co_firstlineno == node.lineno
            ]
            if len(matches) != 1:
                raise ValueError("lookup-row loaded code site mismatch")
            path = Path(code.co_filename).resolve()
            if path not in self._sources:
                raise ValueError("lookup-row enclosing source mismatch")
            site = dict(
                id=f"{short}.{name}:{ordinal}",
                module=module.__name__,
                function=name,
                table=table,
                chart_slot=chart_slot,
                record_slot=record_slot,
                roll_slot=roll_slot,
                line=node.lineno,
                path=str(path),
                source_sha256=hashlib.sha256(self._sources[path]).hexdigest(),
            )
            self.sites.append(site)
            self._codes[matches[0]] = site
            binding = (owner, pieces[-1], function, code)
            if not any(parent[2] is function for parent in self._parents):
                self._parents.append(binding)
        if len(self._codes) != len(_SITES):
            raise ValueError("lookup-row duplicate loaded sites")
        functions = [parent[2] for parent in self._parents]
        for name, module in tuple(sys.modules.items()):
            if name.startswith("bowl_bound.") and module is not None:
                for attribute, value in tuple(vars(module).items()):
                    if any(value is function for function in functions):
                        self._aliases.append((module, attribute, value))
        self.check_bindings()
        self.check_sources()

    def check_bindings(self) -> None:
        """Check frozen function/code identities, including imported aliases."""
        if any(
            getattr(owner, name, None) is not function or function.__code__ is not code
            for owner, name, function, code in self._parents
        ):
            raise ValueError("lookup-row enclosing binding changed")
        if any(
            getattr(module, name, None) is not function for module, name, function in self._aliases
        ):
            raise ValueError("lookup-row imported alias changed")

    def check_sources(self) -> None:
        """Check origins and current bytes, without loaded-code attestation."""
        if any(
            module.__file__ != filename
            or getattr(getattr(module, "__spec__", None), "origin", None) != origin
            for module, filename, origin in self._modules
        ):
            raise ValueError("lookup-row module origin changed")
        if any(path.read_bytes() != content for path, content in self._sources.items()):
            raise ValueError("lookup-row source changed")

    def observe_draw(self, game: Any, roll: Any, number: int) -> None:
        """Retain actual identities separately from detached public observations."""
        self._draw_objects.append((game, roll, number))

    def observe_initial(self, game: Any, number: int) -> None:
        """Freeze positive prior-window tape membership before the delegate."""
        if any(known is game for known, *_ in self._initial_objects):
            raise ValueError("lookup-row repeated initial tape")
        rolls = list(game._tape.rolls)
        position, replaying = game._tape.position, game._tape.replaying
        detached = dict(
            game_number=number,
            position=position,
            replaying=replaying,
            recorded_rolls=[dict(faces=_json_value(roll), total=roll.total) for roll in rolls],
        )
        self._initial_objects.append((game, rolls, position, replaying))
        self.initial_tapes.append(detached)

    def profile(
        self, frame: FrameType, event: str, result: Any, game: Any, command: dict[str, Any]
    ) -> None:
        if event != "return" or result is None or frame.f_code not in self._codes:
            return
        try:
            site = self._codes[frame.f_code]
            parent = frame.f_back
            if parent is None:
                raise ValueError("lookup-row parent missing")
            chart = parent.f_locals[site["chart_slot"]]
            roll = parent.f_locals[site["roll_slot"]]
            record = frame.f_locals[site["record_slot"]]
            pat = site["table"] == "pat_outcomes"
            actual = record if pat else record.cell
            if result is not actual:
                raise ValueError("lookup-row yielded value differs from record")
            sides = [side for side, known in game._charts.items() if known is chart]
            copies = sum(known is record for known in getattr(chart, site["table"]))
            positions = [index for index, known in enumerate(game._tape.rolls) if known is roll]
            draws = [
                number
                for known_game, known_roll, number in self._draw_objects
                if known_game is game and known_roll is roll
            ]
            initial = next((item for item in self._initial_objects if item[0] is game), None)
            prior = bool(
                initial is not None
                and len(positions) == 1
                and positions[0] < len(initial[1])
                and initial[1][positions[0]] is roll
                and (not initial[3] or positions[0] < initial[2])
            )
            identity = (
                "AMBIGUOUS"
                if len(positions) > 1 or len(draws) > 1
                else "MISSING"
                if not positions
                else "PREWINDOW"
                if not draws and prior
                else "UNOBSERVED"
                if not draws
                else "BOUND"
            )
            table = "pat" if pat else site["table"]
            address = dict(
                team_id=game._teams[sides[0]]["id"] if len(sides) == 1 else None,
                season=chart.season,
                table=table,
                play=_json_value(record.play) if table in {"offense", "defense"} else None,
                column=_json_value(record.column)
                if table in {"supplemental", "special_teams"}
                else None,
                formation=_json_value(record.defense) if table == "defense" else None,
                roll=record.roll,
            )
            self.events.append(
                dict(
                    number=len(self.events) + 1,
                    command_number=command["number"],
                    game_number=command["game_number"],
                    captured_draw_frontier=len(self.capture.draws),
                    site_id=site["id"],
                    address=address,
                    facts=dict(good=record.good)
                    if pat
                    else {name: _json_value(getattr(actual, name)) for name in _CELL_FIELDS},
                    chart_binding="BOUND"
                    if len(sides) == 1
                    else "AMBIGUOUS"
                    if sides
                    else "MISSING",
                    record_binding="BOUND" if copies == 1 else "AMBIGUOUS" if copies else "MISSING",
                    draw_binding=dict(
                        status=identity, tape_indices=positions, captured_draw_numbers=draws
                    ),
                    roll=dict(faces=_json_value(roll), total=roll.total),
                )
            )
        except Exception as error:
            self.errors.append(dict(stage="lookup_row", exception_type=type(error).__name__))
            self.capture._error("lookup_row", error)

    def payload(self) -> dict[str, Any]:
        """Return raw detached observations, never a completeness/authority pass."""
        counts = Counter(event["site_id"] for event in self.events)
        return json.loads(
            json.dumps(
                dict(
                    version="2",
                    sites=self.sites,
                    events=self.events,
                    errors=self.errors,
                    usable=not self.capture.errors,
                    qualification="UNVERIFIED",
                    sources=[
                        dict(
                            module=module.__name__,
                            module_file=filename,
                            module_spec_origin=origin,
                            path=str(Path(filename).resolve()),
                            source_sha256=hashlib.sha256(
                                self._sources[Path(filename).resolve()]
                            ).hexdigest(),
                        )
                        for module, filename, origin in self._modules
                    ],
                    aliases=[
                        dict(
                            module=module.__name__,
                            name=name,
                            function_module=function.__module__,
                            function_name=function.__qualname__,
                        )
                        for module, name, function in self._aliases
                    ],
                    initial_tapes=self.initial_tapes,
                    exercised_sites={site["id"]: counts[site["id"]] for site in self.sites},
                    site_status={
                        site["id"]: "OBSERVED" if counts[site["id"]] else "NOTRUN"
                        for site in self.sites
                    },
                    scope=(
                        "Successful reviewed chart-row yields only; "
                        "external completeness/source truth UNVERIFIED."
                    ),
                ),
                allow_nan=False,
            )
        )
