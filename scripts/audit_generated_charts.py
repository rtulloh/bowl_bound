"""Audit pinned generated charts through normalized facts and the real resolver.

Source observations remain private: this gate verifies the candidate/model and
preserved baseline, not the truth of unavailable PBP. Local source/OOB and full
current-engine qualification remain separate required release evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass, field, replace
from itertools import combinations, product
from pathlib import Path
from typing import Any, cast

from bowl_bound.dice import BLACK_FACES, GREEN_FACES, RED_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES
from bowl_bound.models import (
    ChartColor,
    Defense,
    NormalizedCell,
    Play,
    Priority,
    Provenance,
    ResultKind,
    TeamChart,
)
from bowl_bound.normalization import CELL_LEGEND
from bowl_bound.resolution import resolve_cells
from bowl_bound.team_csv import TeamFileMetadata, load_team

POLICY_SHA256 = "bbb35953b3812769bde39d5c567fc21dece00b0899cb037feaad0db7aa88280c"
BUDGET_MODEL_SHA256 = "a46aaf838a718e012a2ce90a4438e6de475a0d810f18ab7e92d87148603a9e5f"
BUDGET_TOOL_VERSION = "bb-chartgen-budget-alpha-v1"
POLICY_YARDS = (
    (0, -2, 0, 1, 2, -1),
    (0, -2, -1, 1, 2, 0),
    (0, 2, -3, 0, 1, 0),
    (0, -2, -1, 0, 1, 2),
    (0, -1, -2, 1, 2, 0),
    (0, 0, 0, -3, 1, 2),
    (0, 1, -1, -2, 3, -1),
    (0, 1, 1, -1, -2, 1),
    (0, 2, 2, 0, -3, -1),
)
WEIGHTS = Counter(r + g for r, g in product(RED_FACES, GREEN_FACES))
OFFENSE_WEIGHTS = Counter(
    10 * b + w1 + w2 for b, w1, w2 in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
)
NUMERIC = {ResultKind.YARDS, ResultKind.NO_CHANGE}
FAMILIES = {
    ResultKind.INCOMPLETE: "INC",
    ResultKind.INTERCEPTION: "INT",
    ResultKind.QUARTERBACK_TRAPPED: "QT",
}
EXPECTATIONS = "release/generated-chart-audit.json"
SOURCE_FIELDS = {"normalized_source_sha256", "source_review_sha256", "oob_review_sha256"}
DERIVED_FIELDS = {"candidate_sha256", "baseline_expectations_sha256", "baseline_catalog_sha256"}


class ChartAuditError(ValueError):
    """A generated release candidate is incomplete, stale or tactically invalid."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


@dataclass
class _FrozenInputs:
    """Detached byte facts plus fail-closed checks of their original paths."""

    files: dict[Path, bytes] = field(default_factory=dict)

    def read(self, path: Path) -> bytes:
        if ".." in path.parts:
            raise ChartAuditError("Nonlocal generated audit input")
        path = path.absolute()
        if path not in self.files:
            self.files[path] = self._current(path)
        return self.files[path]

    @staticmethod
    def _current(path: Path) -> bytes:
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ChartAuditError(f"Symlinked generated audit input: {path.name}")
        try:
            return path.read_bytes()
        except OSError as error:
            raise ChartAuditError(
                f"Missing or changed generated audit input: {path.name}"
            ) from error

    def check(self) -> None:
        for path, content in self.files.items():
            if self._current(path) != content:
                raise ChartAuditError(f"Generated audit input changed: {path.name}")


def _json(path: Path, inputs: _FrozenInputs | None = None) -> dict[str, Any]:
    try:
        content = path.read_bytes() if inputs is None else inputs.read(path)
        value = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ChartAuditError(f"Missing or invalid chart audit input: {path.name}") from error
    if not isinstance(value, dict):
        raise ChartAuditError(f"Expected chart audit object: {path.name}")
    return value


def _execution_inputs(inputs: _FrozenInputs) -> str:
    source = Path(__file__).resolve().parents[1]
    inputs.read(Path(__file__).resolve())
    for name in _runtime_core(source, inputs):
        inputs.read(source / name)
    return _engine_identity(source)


@contextmanager
def _candidate_snapshot(
    root: Path, inputs: _FrozenInputs, *, expectations: bool, runtime: bool
) -> Iterator[Path]:
    """Parse only a private exact allowlisted copy, never later live chart bytes."""
    pins, _ = _catalog(root, inputs)
    names = {"release/manifest.json", *pins}
    if expectations and pins:
        inputs.read(root / EXPECTATIONS)
        names.add(EXPECTATIONS)
    if runtime and pins:
        _execution_inputs(inputs)
        for name in _runtime_core(root, inputs):
            inputs.read(root / name)
            names.add(name)
    with tempfile.TemporaryDirectory(prefix="bb-chart-audit-") as directory:
        snapshot = Path(directory).resolve()
        for name in sorted(names):
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            destination.write_bytes(inputs.read(root / name))
            destination.chmod(0o600)
        yield snapshot


def policy_effect(play: Play, formation: Defense) -> int:
    """Return an approved authored coefficient, not a football rule."""
    return POLICY_YARDS[play.value - 1][list(Defense).index(formation)]


def _policy_identity() -> str:
    fields = (
        "incomplete_delta",
        "interception_delta",
        "sack_delta",
        "scramble_delta",
        "breakaway_delta",
        "override_delta",
    )
    effects = [
        {
            "formation": f.value,
            "play": p.value,
            "yard_offset": policy_effect(p, f),
            **dict.fromkeys(fields, 0.0),
        }
        for p in Play
        for f in Defense
    ]
    profile = {
        "schema_version": 1,
        "origin": "authored-bb-yardage-v1",
        "source_hashes": [],
        "effects": effects,
    }
    return _sha(json.dumps(profile, sort_keys=True).encode())


def _facts(cell: NormalizedCell) -> dict[str, Any]:
    facts = asdict(cell)
    facts.pop("provenance")
    facts["rgb_color"] = cell.provenance.rgb_color if cell.provenance else None
    return facts


def _address(record: Any) -> str:
    return f"{record.defense.value}/{record.play.value}/{record.roll}"


def _defense_fingerprint(chart: TeamChart) -> str:
    return _digest(sorted((_address(r), _facts(r.cell)) for r in chart.defense))


def weighted_distributions(chart: TeamChart) -> dict[str, str]:
    """Fingerprint normalized outcomes under all 36 physical defensive pairs."""
    output = {}
    for play in Play:
        for formation in Defense:
            counts: Counter[str] = Counter()
            for r in chart.defense:
                if r.play is play and r.defense is formation:
                    counts[json.dumps(_facts(r.cell), sort_keys=True)] += WEIGHTS[r.roll]
            output[f"{formation.value}/{play.value}"] = _digest(sorted(counts.items()))
    return output


def baseline_record(root: Path, key: str) -> dict[str, Any]:
    """Build compact expected facts from an independently accepted baseline."""
    season, slug = key.split("/")
    chart, _ = load_team(root / "seasons" / season, slug)
    return {
        "nondefensive_sha256": {
            name: _sha((root / "seasons" / key / name).read_bytes())
            for name in ("offense.csv", "special.csv", "team.yaml")
        },
        "defense_semantics_sha256": _defense_fingerprint(chart),
        "explicit_numeric_zero": sorted(
            _address(r)
            for r in chart.defense
            if r.cell.kind is ResultKind.YARDS and r.cell.yards == 0
        ),
    }


def audit_candidate(root: Path) -> dict[str, Any]:
    """Compute from frozen bytes; reject changed originals before accepting."""
    inputs = _FrozenInputs()
    with _candidate_snapshot(root, inputs, expectations=True, runtime=True) as snapshot:
        result = _audit_candidate(snapshot)
        if result.get("generated_teams") and _engine_identity(snapshot) != result["engine_sha256"]:
            raise ChartAuditError("Generated audit engine changed during validation")
        if result.get("generated_teams"):
            result["auditor_sha256"] = _sha(inputs.read(Path(__file__).resolve()))
        inputs.check()
        return result


def _audit_candidate(root: Path) -> dict[str, Any]:
    """Recompute evidence from isolated exact bytes."""
    pins, teams = _catalog(root)
    if not pins:
        return {"passed": True, "generated_teams": 0, "scope": "no generated charts"}
    expected = _json(root / EXPECTATIONS)
    version = expected.get("schema_version")
    if (
        type(version) is not int
        or version not in {1, 2}
        or not isinstance(expected.get("teams"), dict)
    ):
        raise ChartAuditError("Missing generated chart audit schema/team expectations")
    if set(expected["teams"]) != teams:
        raise ChartAuditError("Generated audit team inventory differs from shipped catalog")
    identity = expected.get("model_identity", {})
    _validate_identity(identity, version)
    review = expected.get("source_review", {})
    if (
        not isinstance(review, dict)
        or not SOURCE_FIELDS <= set(review) <= SOURCE_FIELDS | DERIVED_FIELDS
        or any(not _is_sha(value) for value in review.values())
    ):
        raise ChartAuditError(
            "Missing independently reviewed private source/OOB qualification hashes"
        )
    candidate_sha = _digest(pins)
    if review.get("candidate_sha256") != candidate_sha:
        raise ChartAuditError("Private source qualification is stale for this candidate catalog")
    if review.get("baseline_expectations_sha256") != _digest(expected["teams"]):
        raise ChartAuditError("Private source qualification is stale for baseline expectations")
    if version == 2 and not _is_sha(review.get("baseline_catalog_sha256")):
        raise ChartAuditError("Missing reviewed baseline catalog identity")
    engine_sha = _engine_identity(root)
    reports = {}
    for key in sorted(teams):
        season, slug = key.split("/")
        baseline = expected["teams"][key]
        if not isinstance(baseline, dict):
            raise ChartAuditError(f"Missing baseline expectations: {key}")
        if version == 1:
            files = baseline.get("nondefensive_sha256", {})
            if set(files) != {"offense.csv", "special.csv", "team.yaml"}:
                raise ChartAuditError(f"Incomplete baseline nondefensive pins: {key}")
            for name, digest in files.items():
                if not _is_sha(digest) or pins[f"seasons/{key}/{name}"] != digest:
                    raise ChartAuditError(f"Changed baseline nondefensive/OOB facts: {key}/{name}")
        try:
            chart, metadata = load_team(root / "seasons" / season, slug)
        except ValueError as error:
            raise ChartAuditError(f"Invalid strict chart/provenance codec: {key}") from error
        if version == 2:
            reports[key] = _audit_budget(chart, metadata, baseline, key)
            continue
        if metadata.source_sha256 != identity["source_sha256"]:
            raise ChartAuditError(f"Chart source identity disagrees with qualified model: {key}")
        restored = _restore_baseline(chart, baseline)
        if _defense_fingerprint(restored) != baseline.get("defense_semantics_sha256"):
            raise ChartAuditError(
                f"Unexpected baseline defense/response/priority/OOB change: {key}"
            )
        reports[key] = _audit_roles(chart, restored, key)
    return {
        "schema_version": version,
        "passed": True,
        "generated_teams": len(teams),
        "physical_defensive_mass": sum(WEIGHTS.values()),
        "candidate_sha256": candidate_sha,
        "expectations_sha256": _sha((root / EXPECTATIONS).read_bytes()),
        "policy_sha256": identity["sha256"],
        "model_identity": identity,
        "engine_sha256": engine_sha,
        "source_truth_revalidated": False,
        "source_review": review,
        "scope": (
            "normalized defense mass; primary priority roles/classes; preserved baseline"
            if version == 1
            else "exact family budgets; fixed semantics; primary partitions; role residuals"
        ),
        "limits": "PBP/OOB truth and full supplemental/game/AI qualification are separate gates.",
        "teams": reports,
    }


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _validate_identity(identity: Any, version: int = 1) -> None:
    fields = {"origin", "sha256", "authored_experimental", "tool_version", "source_sha256"}
    if (
        not isinstance(identity, dict)
        or set(identity) != fields
        or _policy_identity() != POLICY_SHA256
        or identity.get("origin")
        != ("authored-bb-yardage-v1" if version == 1 else "authored-bb-budget-aware-v1")
        or identity.get("sha256") != (POLICY_SHA256 if version == 1 else BUDGET_MODEL_SHA256)
        or identity.get("authored_experimental") is not True
        or identity.get("tool_version")
        != ("college-chartgen-v6" if version == 1 else BUDGET_TOOL_VERSION)
        or not _is_sha(identity.get("source_sha256"))
    ):
        raise ChartAuditError("Missing or unsupported approved generated chart model identity")


def _catalog(root: Path, inputs: _FrozenInputs | None = None) -> tuple[dict[str, str], set[str]]:
    pins = _json(root / "release/manifest.json", inputs).get("generated_sha256", {})
    if not isinstance(pins, dict):
        raise ChartAuditError("Generated catalog must be an exact pinned map")
    teams: dict[str, set[str]] = {}
    for name, digest in pins.items():
        match = re.fullmatch(
            r"seasons/(\d{4}/[a-z0-9][a-z0-9-]*)/(offense.csv|defense.csv|special.csv|team.yaml)",
            name,
        )
        provenance = re.fullmatch(r"seasons/(\d{4})/provenance/([a-z0-9][a-z0-9-]*)\.csv", name)
        if match:
            key, section = match.groups()
        elif provenance:
            key = "/".join(provenance.groups())
            section = "provenance.csv"
        else:
            raise ChartAuditError("Unexpected generated catalog resource")
        path = root / name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ChartAuditError("Symlinked generated catalog input")
        if (
            not path.is_file()
            or _sha(path.read_bytes() if inputs is None else inputs.read(path)) != digest
        ):
            raise ChartAuditError(f"Stale generated catalog pin: {key}/{section}")
        teams.setdefault(key, set()).add(section)
    sections = {"offense.csv", "defense.csv", "special.csv", "team.yaml", "provenance.csv"}
    if any(actual != sections for actual in teams.values()):
        raise ChartAuditError("Every generated team needs complete chart/provenance inputs")
    return pins, set(teams)


def _restore_baseline(chart: TeamChart, expected: dict[str, Any]) -> TeamChart:
    zeros = expected.get("explicit_numeric_zero")
    addresses = {_address(r) for r in chart.defense}
    if not isinstance(zeros, list) or len(set(zeros)) != len(zeros) or not set(zeros) <= addresses:
        raise ChartAuditError("Invalid baseline zero/blank expectations")
    records = []
    for r in chart.defense:
        cell = r.cell
        if cell.kind in NUMERIC:
            value = (cell.yards or 0) - policy_effect(r.play, r.defense)
            blank = value == 0 and cell.priority is Priority.NORMAL and _address(r) not in zeros
            color = ChartColor.WHITE if blank else ChartColor.RED if value < 0 else ChartColor.GREEN
            evidence = replace(
                cast(Provenance, cell.provenance), rgb_color=CELL_LEGEND[color].rgb_color
            )
            cell = replace(
                cell,
                kind=ResultKind.NO_CHANGE if blank else ResultKind.YARDS,
                yards=None if blank else value,
                chart_color=color,
                provenance=evidence,
            )
        records.append(replace(r, cell=cell))
    return replace(chart, defense=tuple(records))


def _primary(
    chart: TeamChart, play: Play, formation: Defense, offense: NormalizedCell
) -> tuple[int, dict[str, int]]:
    numeric_contribution = 0
    classes: Counter[str] = Counter()
    for r in chart.defense:
        if r.play is play and r.defense is formation:
            result = resolve_cells(offense, r.cell)
            classes[
                _digest((result.kind, result.operation, result.pending, result.out_of_bounds))
            ] += WEIGHTS[r.roll]
            if result.kind is ResultKind.YARDS:
                numeric_contribution += (result.yards or 0) * WEIGHTS[r.roll]
    return numeric_contribution, dict(classes)


def _audit_roles(chart: TeamChart, baseline: TeamChart, key: str) -> dict[str, Any]:
    distributions = weighted_distributions(chart)
    if all(len({distributions[f"{f.value}/{p.value}"] for f in Defense}) == 1 for p in Play):
        raise ChartAuditError(f"Equivalent formation probabilities: {key}")
    for gain in (4, 10, 18):
        offense = NormalizedCell(ResultKind.YARDS, None, yards=gain)
        contributions = {(p, f): _primary(chart, p, f, offense)[0] for p in Play for f in Defense}
        ordered = (
            (Play.ONE, (Defense.B, Defense.A, Defense.E)),
            (Play.THREE, (Defense.C, Defense.A, Defense.B)),
            (Play.FOUR, (Defense.A, Defense.F)),
            (Play.SIX, (Defense.D, Defense.A, Defense.F)),
            (Play.SEVEN, (Defense.D, Defense.F, Defense.E)),
            (Play.NINE, (Defense.E, Defense.F, Defense.B)),
            (Play.EIGHT, (Defense.A, Defense.F)),
        )
        for play, formations in ordered:
            values = [contributions[play, f] for f in formations]
            if any(a >= b for a, b in zip(values[:-1], values[1:], strict=True)):
                raise ChartAuditError(f"Missing declared role/tradeoff: {key}, play {play.value}")
        for first, second in combinations(Defense, 2):
            differences = [contributions[p, first] - contributions[p, second] for p in Play]
            if not (min(differences) < 0 < max(differences)):
                raise ChartAuditError(
                    f"Tactical dominance or inert formation: {key}, {first.value}/{second.value}"
                )
    # Every normalized actual offense cell is checked. Multiplicity cannot affect
    # equality: each cell's exact 36-pair primary class distribution must match.
    # Pending/supplemental kinds remain kinds, never zero-yard resolved outcomes.
    for play in Play:
        facts = {_digest(_facts(r.cell)): r.cell for r in chart.offense if r.play is play}
        for cell in facts.values():
            for formation in Defense:
                before = _primary(baseline, play, formation, cell)[1]
                after = _primary(chart, play, formation, cell)[1]
                if before != after:
                    raise ChartAuditError(
                        f"Unintended primary outcome class change: {key}, play {play.value}"
                    )
    return {
        "formation_counterplay": True,
        "primary_class_invariance": True,
        "distinct_weighted_defense_columns": len(set(distributions.values())),
    }


def _semantic(cell: NormalizedCell) -> dict[str, Any]:
    facts = asdict(cell)
    facts.pop("provenance")
    return facts


def _normal(cell: NormalizedCell) -> bool:
    return cell.priority is Priority.NORMAL and not cell.out_of_bounds


def _mutable(cell: NormalizedCell) -> bool:
    return (
        _normal(cell)
        and cell.variable is None
        and cell.kind in NUMERIC | set(FAMILIES)
        and (cell.kind is not ResultKind.INTERCEPTION or cell.yards is not None)
    )


def _family_mass(chart: TeamChart) -> dict[tuple[int, Defense], dict[str, int]]:
    mass = {(p, f): dict.fromkeys(FAMILIES.values(), 0) for p in range(6, 10) for f in Defense}
    for r in chart.defense:
        if r.play.value >= 6 and _normal(r.cell) and r.cell.kind in FAMILIES:
            mass[r.play.value, r.defense][FAMILIES[r.cell.kind]] += WEIGHTS[r.roll]
    return mass


def _budget_record(chart: TeamChart, metadata: TeamFileMetadata) -> dict[str, Any]:
    """Compact baseline facts independent of replaced virtual provenance."""
    metadata_facts = {
        k: v for k, v in asdict(metadata).items() if k not in {"source_sha256", "evidence"}
    }
    nondefense = {
        "name": chart.name,
        "season": chart.season,
        "metadata": metadata_facts,
        "offense": sorted((r.play.value, r.roll, _semantic(r.cell)) for r in chart.offense),
        "supplemental": sorted(
            (r.column.value, r.roll, _semantic(r.cell)) for r in chart.supplemental
        ),
        "special": sorted((r.column.value, r.roll, _semantic(r.cell)) for r in chart.special_teams),
        "pat": sorted((r.roll, r.good) for r in chart.pat_outcomes),
        "recovery": sorted(chart.recovery_range),
    }
    mass = _family_mass(chart)
    return {
        "nondefensive_semantics_sha256": _digest(nondefense),
        "run_semantics_sha256": _digest(
            sorted((_address(r), _semantic(r.cell)) for r in chart.defense if r.play.value <= 5)
        ),
        "fixed_pass_semantics_sha256": _digest(
            sorted(
                (_address(r), "mutable" if _mutable(r.cell) else _semantic(r.cell))
                for r in chart.defense
                if r.play.value >= 6
            )
        ),
        "call_family_mass": {
            str(p): {k: sum(mass[p, f][k] for f in Defense) for k in FAMILIES.values()}
            for p in range(6, 10)
        },
        "formation_int_mass": {
            f.value: sum(mass[p, f]["INT"] for p in range(6, 10)) for f in Defense
        },
        "anchor_mass": {
            str(p): {k: mass[p, Defense.A][k] for k in ("INT", "QT")} for p in range(6, 10)
        },
    }


def _audit_budget(
    chart: TeamChart, metadata: TeamFileMetadata, expected: dict[str, Any], key: str
) -> dict[str, Any]:
    actual = _budget_record(chart, metadata)
    if set(expected) != set(actual):
        raise ChartAuditError(f"Invalid budget baseline fields: {key}")
    # JSON canonical equality distinguishes integer mass from bool/float values.
    if _digest(actual) != _digest(expected):
        raise ChartAuditError(f"Changed baseline semantic facts or family budgets: {key}")
    for gain in (4, 10, 18):
        offense = NormalizedCell(ResultKind.YARDS, None, yards=gain)
        for play, ordered in (
            (Play.ONE, (Defense.B, Defense.A, Defense.E)),
            (Play.THREE, (Defense.C, Defense.A, Defense.B)),
            (Play.FOUR, (Defense.A, Defense.F)),
        ):
            values = [_primary(chart, play, f, offense)[0] for f in ordered]
            if any(a >= b for a, b in zip(values[:-1], values[1:], strict=True)):
                raise ChartAuditError(
                    f"Missing preserved run tactical contrast: {key}/{play.value}"
                )
    mass = _family_mass(chart)
    for p in range(6, 10):
        for f in Defense:
            if not any(
                r.play.value == p and r.defense is f and _mutable(r.cell) and r.cell.kind in NUMERIC
                for r in chart.defense
            ):
                raise ChartAuditError(f"Missing ordinary numeric support: {key}/{f.value}/{p}")
    roles = {}

    def role(name: str, delta: int, request: int, support: int) -> None:
        if delta < 0:
            raise ChartAuditError(f"Reversed declared budget role: {key}/{name}")
        status = (
            "dormant" if support == 0 else "requested-attained" if delta == request else "limited"
        )
        roles[name] = {
            "requested": request if support else None,
            "represented": delta,
            "residual": abs(request - delta) if support else None,
            "status": status,
            "strict_direction_achieved": delta > 0 if support else None,
        }

    for p in range(6, 10):
        for f in (Defense.D, Defense.E):
            direction = 1 if (f is Defense.D) == (p <= 7) else -1
            role(
                f"{f.value}/{p}/INC",
                direction * (mass[p, f]["INC"] - mass[p, Defense.A]["INC"]),
                3,
                expected["call_family_mass"][str(p)]["INC"],
            )
        if p in {7, 9}:
            role(
                f"F/{p}/QT",
                mass[p, Defense.F]["QT"] - mass[p, Defense.A]["QT"],
                3,
                expected["call_family_mass"][str(p)]["QT"],
            )
        else:
            role(
                f"F/{p}/INC",
                mass[p, Defense.A]["INC"] - mass[p, Defense.F]["INC"],
                3,
                expected["call_family_mass"][str(p)]["INC"],
            )
            if mass[p, Defense.F]["QT"] > mass[p, Defense.A]["QT"]:
                raise ChartAuditError(f"Reversed declared pressure counterplay: {key}/F/{p}")
            role(
                f"F/{p}/noncompletion",
                sum(mass[p, Defense.A].values()) - sum(mass[p, Defense.F].values()),
                3,
                sum(expected["call_family_mass"][str(p)].values()),
            )
    for plays in ((6, 7), (8, 9)):
        for f in (Defense.D, Defense.E):
            direction = 1 if (f is Defense.D) == (plays == (6, 7)) else -1
            delta = sum(mass[p, f]["INT"] - mass[p, Defense.A]["INT"] for p in plays)
            role(
                f"{f.value}/{plays[0]}-{plays[1]}/INT",
                direction * delta,
                2,
                sum(v["INT"] for v in expected["call_family_mass"].values()),
            )
    # Run/Option cells remain the exact accepted baseline, while pass classes
    # intentionally change. Do not impose legacy primary-class invariance.
    primary = {}
    for p in Play:
        for f in Defense:
            classes: Counter[str] = Counter()
            for r in chart.offense:
                if r.play is p:
                    for outcome, weight in _primary(chart, p, f, r.cell)[1].items():
                        classes[outcome] += weight * OFFENSE_WEIGHTS[r.roll]
            if sum(classes.values()) != 216 * 36:
                raise ChartAuditError(
                    f"Invalid full primary denominator: {key}/{f.value}/{p.value}"
                )
            primary[f"{f.value}/{p.value}"] = _digest(sorted(classes.items()))
    stripes = []
    for p in range(6, 10):
        for roll in range(1, 6):
            kinds = {r.cell.kind for r in chart.defense if r.play.value == p and r.roll == roll}
            if len(kinds) == 1 and not kinds <= NUMERIC:
                stripes.append({"play": p, "roll": roll, "kind": next(iter(kinds)).value})
    return {
        "family_budgets_preserved": True,
        "fixed_whole_facts_preserved": True,
        "nondefensive_gameplay_preserved": True,
        "roles": roles,
        "primary_physical_mass": 216 * 36,
        "primary_class_sha256": primary,
        "pattern_diagnostics": {"all_formation_family_rows": stripes},
        "source_fit": "UNVERIFIED",
        "optimizer_optimality_revalidated": False,
        "limits": (
            "Primary classes include pending procedures; "
            "no terminal utility or historical fit claim."
        ),
    }


def _runtime_core(root: Path, inputs: _FrozenInputs | None = None) -> list[str]:
    runtime = _json(root / "release/manifest.json", inputs).get("runtime")
    if not isinstance(runtime, list) or any(not isinstance(name, str) for name in runtime):
        raise ChartAuditError("Missing or invalid runtime core inventory")
    return sorted(
        name for name in runtime if name.startswith("bowl_bound/") and name.endswith(".py")
    )


def _engine_identity(root: Path) -> str:
    # Hash the code actually used, and reject a different supplied candidate core.
    source = Path(__file__).resolve().parents[1]
    for name, module in tuple(sys.modules.items()):
        if name == "bowl_bound" or name.startswith("bowl_bound."):
            expected = source / (name.replace(".", "/") + ".py")
            if name == "bowl_bound":
                expected = source / "bowl_bound/__init__.py"
            actual = getattr(module, "__file__", None)
            if actual is None or Path(actual).resolve() != expected.resolve():
                raise ChartAuditError("Foreign imported engine module cannot certify candidate")
    # Development-only auditing modules are deliberately absent from native
    # stages. Identify the same exact approved runtime core in both layouts.
    names = _runtime_core(source)
    required = {
        "bowl_bound/__init__.py",
        "bowl_bound/dice.py",
        "bowl_bound/models.py",
        "bowl_bound/normalization.py",
        "bowl_bound/resolution.py",
        "bowl_bound/team_csv.py",
    }
    if not required <= set(names) or _runtime_core(root) != names:
        raise ChartAuditError("Candidate runtime core differs from the approved audit engine")
    hashes = {}
    for name in names:
        digest = _sha((source / name).read_bytes())
        candidate = root / name
        if not candidate.is_file() or _sha(candidate.read_bytes()) != digest:
            raise ChartAuditError("Candidate engine differs from the audit's imported engine")
        hashes[name] = digest
    return _digest(hashes)


def build_expectations(root: Path, baseline_root: Path, qualification: Path) -> dict[str, Any]:
    """Export byte-bound safe expectations, without qualifying source truth."""
    inputs = _FrozenInputs()
    engine = _execution_inputs(inputs)
    with (
        _candidate_snapshot(root, inputs, expectations=False, runtime=False) as candidate,
        _candidate_snapshot(baseline_root, inputs, expectations=False, runtime=False) as baseline,
    ):
        source = _json(qualification, inputs)
        result = _build_expectations(candidate, baseline, source)
        if _engine_identity(Path(__file__).resolve().parents[1]) != engine:
            raise ChartAuditError("Generated expectation engine changed during validation")
        inputs.check()
        return result


def _build_expectations(root: Path, baseline_root: Path, source: dict[str, Any]) -> dict[str, Any]:
    """Interpret frozen baseline and independently reviewed model/source facts."""
    pins, keys = _catalog(root)
    baseline_pins, baseline_keys = _catalog(baseline_root)
    if baseline_keys != keys:
        raise ChartAuditError("Baseline and candidate generated team inventories differ")
    if set(source) != SOURCE_FIELDS | {"model_identity"}:
        raise ChartAuditError(
            "Unsupported qualification fields; export only approved SHA identities"
        )
    identity = source.pop("model_identity", None)
    version = (
        2
        if isinstance(identity, dict) and identity.get("origin") == "authored-bb-budget-aware-v1"
        else 1
    )
    _validate_identity(identity, version)
    teams = {}
    for key in sorted(keys):
        if version == 1:
            teams[key] = baseline_record(baseline_root, key)
        else:
            season, slug = key.split("/")
            teams[key] = _budget_record(*load_team(baseline_root / "seasons" / season, slug))
    if any(not _is_sha(value) for value in source.values()):
        raise ChartAuditError("Source qualification fields must be SHA-256 identities")
    source["candidate_sha256"] = _digest(pins)
    source["baseline_catalog_sha256"] = _digest(baseline_pins)
    source["baseline_expectations_sha256"] = _digest(teams)
    return {
        "schema_version": version,
        "model_identity": identity,
        "source_review": source,
        "teams": teams,
    }


def main(argv: list[str] | None = None) -> int:
    """Compute an actual candidate report, or export baseline expectations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path)
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument("--qualification", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.baseline_root or args.qualification:
            if not args.baseline_root or not args.qualification:
                raise ChartAuditError(
                    "Baseline export requires both baseline root and qualification"
                )
            result = build_expectations(args.root, args.baseline_root, args.qualification)
            destination = args.root / EXPECTATIONS
            destination.write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print("Exported baseline expectations; actual candidate audit still required")
        else:
            result = audit_candidate(args.root)
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
            print(f"Generated chart audit passed: {result['generated_teams']} teams")
    except (ChartAuditError, OSError, ValueError, TypeError, KeyError) as error:
        if args.report:
            rejected = {
                "schema_version": 1,
                "passed": False,
                "reason": str(error),
                "policy_sha256": POLICY_SHA256,
                "source_truth_revalidated": False,
            }
            with suppress(ChartAuditError, OSError):
                expected = _json(args.root / EXPECTATIONS)
                if type(expected.get("schema_version")) is int and expected["schema_version"] == 2:
                    rejected["schema_version"] = 2
                    rejected["policy_sha256"] = BUDGET_MODEL_SHA256
            # Preserve identities that remain readable after the original error;
            # missing/broken inputs stay absent, never invented as zero hashes.
            with suppress(ChartAuditError, OSError):
                pins = _json(args.root / "release/manifest.json").get("generated_sha256")
                if isinstance(pins, dict):
                    rejected["candidate_sha256"] = _digest(pins)
            with suppress(OSError):
                rejected["expectations_sha256"] = _sha((args.root / EXPECTATIONS).read_bytes())
            with suppress(ChartAuditError, OSError):
                rejected["engine_sha256"] = _engine_identity(args.root)
            with suppress(OSError):
                rejected["auditor_sha256"] = _sha(Path(__file__).read_bytes())
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(rejected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        print(f"Generated chart audit failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
