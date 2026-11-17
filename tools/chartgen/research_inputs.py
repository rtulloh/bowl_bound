"""Detached, type-preserving supplied facts for local research execution.

This binds complete provided values; it does not qualify their historical truth.
The guards assume a trusted process, not malicious mutation of Python internals.
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from .cohort_report import canonical_hash

INPUT_ALGORITHM = "bb-research-inputs-v1"
_COMPONENTS = ("teams", "manifest", "catalog", "targets")
_MODEL_MODULES = ("bowl_bound.models", "bowl_bound.team_csv")


def semantic_sha256(value: object) -> str:
    """Hash complete supported facts without collapsing types or source unknowns.

    Repeated aliases have the same value identity as repeated equal objects.
    Cycles, custom containers and nonfinite facts are unsupported, not coerced.
    """
    active: set[int] = set()
    memo: dict[int, bytes] = {}

    def digest(item: object) -> bytes:
        result = hashlib.sha256()
        result.update(INPUT_ALGORITHM.encode())

        def atom(tag: str, text: str = "") -> None:
            data = text.encode("utf-8")
            result.update(tag.encode() + b":" + str(len(data)).encode() + b":" + data)

        kind = type(item)
        if item is None:
            atom("null")
        elif isinstance(item, Enum):
            atom("enum", f"{kind.__module__}.{kind.__qualname__}")
            atom("member", item.name)
            result.update(digest(item.value))
        elif kind is bool:
            atom("bool", "true" if item else "false")
        elif kind is int:
            atom("int", str(item))
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("research input contains a nonfinite number")
            atom("float", item.hex())
        elif kind is str:
            atom("str", item)
        elif kind is range:
            atom("range", f"{item.start}:{item.stop}:{item.step}")
        else:
            identity = id(item)
            if identity in active:
                raise ValueError("research input contains a cycle")
            if identity in memo:
                return memo[identity]
            active.add(identity)
            try:
                if kind is dict:
                    if any(type(key) is not str for key in item):
                        raise TypeError("research input dict requires string keys")
                    atom("dict", str(len(item)))
                    for key in sorted(item):
                        result.update(digest(key))
                        result.update(digest(item[key]))
                elif kind in (list, tuple):
                    atom(kind.__name__, str(len(item)))
                    for child in item:
                        result.update(digest(child))
                elif (
                    is_dataclass(item)
                    and not isinstance(item, type)
                    and kind.__module__ in _MODEL_MODULES
                    and kind.__dataclass_params__.frozen
                ):
                    atom("dataclass", f"{kind.__module__}.{kind.__qualname__}")
                    for field in fields(item):
                        atom("field", field.name)
                        result.update(digest(getattr(item, field.name)))
                else:
                    raise TypeError("research input contains an unsupported object type")
            finally:
                active.remove(identity)
            memo[identity] = result.digest()
        return result.digest()

    return digest(value).hex()


def input_identity(values: dict[str, Any]) -> dict[str, Any]:
    """Describe all supplied components and every complete chart/metadata pair."""
    if set(values) != set(_COMPONENTS) or any(type(values[key]) is not dict for key in values):
        raise TypeError("research input requires four plain component dictionaries")
    components = {key: semantic_sha256(values[key]) for key in _COMPONENTS}
    teams = {key: semantic_sha256(values["teams"][key]) for key in sorted(values["teams"])}
    body = {
        "schema_version": 1,
        "algorithm": INPUT_ALGORITHM,
        "components": components,
        "team_sha256": teams,
    }
    return {**body, "sha256": canonical_hash(body)}


def observed_component_sha256(value: object) -> str:
    """Describe invalid late values without emitting their contents or accepting them."""
    try:
        return semantic_sha256(value)
    except (TypeError, ValueError, RuntimeError) as error:
        return f"invalid:{type(error).__name__}"


class InputConsistencyError(ValueError):
    """Carry hash-only rejection evidence, never source/chart values."""

    def __init__(
        self, stage: str, side: str, expected: dict[str, Any], observed: dict[str, Any]
    ) -> None:
        changed = sorted(
            key
            for key, value in expected["components"].items()
            if observed.get("components", {}).get(key) != value
        )
        if not changed:
            changed = [
                key for key in ("sha256", "team_sha256") if observed.get(key) != expected.get(key)
            ]
        super().__init__(f"frozen simulation inputs differ at {stage}: {side} {', '.join(changed)}")
        self.evidence = {
            "schema_version": 1,
            "stage": stage,
            "side": side,
            "changed_components": changed,
            "expected": deepcopy(expected),
            "observed": deepcopy(observed),
        }

    def __reduce__(self) -> tuple:
        """Preserve structured hash-only errors across a spawned worker boundary."""
        return (
            type(self),
            (
                self.evidence["stage"],
                self.evidence["side"],
                self.evidence["expected"],
                self.evidence["observed"],
            ),
        )


class FrozenResearchInputs:
    """Keep detached computation values and independently captured expectations."""

    def __init__(
        self, original: dict[str, Any], detached: dict[str, Any], identity: dict[str, Any]
    ) -> None:
        self._original = original
        self.values = detached
        self._identity_bytes = json.dumps(identity, sort_keys=True, allow_nan=False).encode()

    @classmethod
    def capture(
        cls, *, teams: dict, manifest: dict, catalog: dict, targets: dict
    ) -> FrozenResearchInputs:
        """Validate before copying, then verify original and whole-graph snapshot."""
        original = {"teams": teams, "manifest": manifest, "catalog": catalog, "targets": targets}
        identity = input_identity(original)
        # Existing trace observers use literal display names as lookup keys.
        # Reject ambiguity rather than making last-wins attribution deterministic.
        names = [chart.name for chart, _ in teams.values()]
        if any(type(name) is not str or not name for name in names):
            raise ValueError("research inputs require nonempty string chart names")
        if len(set(names)) != len(names):
            raise ValueError("research inputs contain duplicate chart names")
        frozen = cls(original, deepcopy(original), identity)
        frozen.check("capture")
        return frozen

    @property
    def identity(self) -> dict[str, Any]:
        """Return a copy; editing it cannot repin the checked expectation."""
        return json.loads(self._identity_bytes)

    def check(self, stage: str, *, include_teams: bool = True) -> None:
        """Require original and computation facts to retain their captured values."""
        expected = self.identity
        for side, values in (("original", self._original), ("snapshot", self.values)):
            observed = deepcopy(expected)
            for key in _COMPONENTS:
                if key == "teams" and not include_teams:
                    continue
                observed["components"][key] = observed_component_sha256(values[key])
            if observed["components"]["teams"] != expected["components"]["teams"]:
                try:
                    observed["team_sha256"] = {
                        key: semantic_sha256(values["teams"][key])
                        for key in sorted(values["teams"])
                    }
                except (TypeError, ValueError, RuntimeError):
                    observed["team_sha256"] = {}
            observed["sha256"] = canonical_hash(
                {key: value for key, value in observed.items() if key != "sha256"}
            )
            if observed["components"] != expected["components"]:
                raise InputConsistencyError(stage, side, expected, observed)


def require_team_inputs(
    teams: dict[str, Any], identity: dict[str, Any], names: tuple[str, ...] | None = None
) -> dict[str, str]:
    """Check the complete inventory and the chart pairs actually used by a game."""
    expected = identity["team_sha256"]
    selected = tuple(expected) if names is None else names
    try:
        actual = {key: semantic_sha256(teams[key]) for key in selected if key in teams}
        if set(teams) == set(expected) and actual == {key: expected.get(key) for key in selected}:
            return actual
        observed_teams = semantic_sha256(teams)
    except (TypeError, ValueError, RuntimeError) as error:
        actual = {}
        observed_teams = f"invalid:{type(error).__name__}"
    observed = deepcopy(identity)
    observed["components"]["teams"] = observed_teams
    if observed_teams.startswith("invalid:"):
        observed["team_sha256"] = {}
    else:
        observed["team_sha256"] = {key: semantic_sha256(teams[key]) for key in sorted(teams)}
    observed["sha256"] = canonical_hash(
        {key: value for key, value in observed.items() if key != "sha256"}
    )
    raise InputConsistencyError("worker charts", "snapshot", identity, observed)


def require_catalog_inputs(catalog: object, identity: dict[str, Any], stage: str) -> None:
    """Refuse changed or invalid task catalogs with structured hash-only evidence."""
    actual = observed_component_sha256(catalog)
    if actual == identity["components"]["catalog"]:
        return
    observed = deepcopy(identity)
    observed["components"]["catalog"] = actual
    observed["sha256"] = canonical_hash(
        {key: value for key, value in observed.items() if key != "sha256"}
    )
    raise InputConsistencyError(stage, "snapshot", identity, observed)
