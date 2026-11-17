"""Opt-in whole-defense budgets and known-source depth transport.

The reference exposure and role requests are authored experimental assumptions.
They are not observed historical formation/call frequencies or qualified fit.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product

from bowl_bound.models import (
    BoundingBox,
    Defense,
    DefensiveCell,
    Play,
    Priority,
    Provenance,
    ResultKind,
    TeamChart,
)
from bowl_bound.normalization import CELL_LEGEND, chart_color_for_csv_token
from bowl_bound.team_csv import format_cell, parse_cell

from .coupled_depths import DepthSupport, balance_pair, quantize_depths, split_depths
from .research_inputs import semantic_sha256

WEIGHTS = (12, 11, 9, 3, 1)
PLAYS = (Play.SIX, Play.SEVEN, Play.EIGHT, Play.NINE)
FORMS = tuple(Defense)
FAMILIES = (ResultKind.INCOMPLETE, ResultKind.INTERCEPTION, ResultKind.QUARTERBACK_TRAPPED)
NUMERIC = {ResultKind.YARDS, ResultKind.NO_CHANGE}
CONTRACT = {
    "origin": "authored-bb-coupled-local-cdf-private-v3",
    "approved_contract": "ce92b71d6da614d43cce0453a6767258665202a9c668c656cddab3cf740c2a7c",
    "weights": WEIGHTS,
    "reference": "uniform24-passing-coordinates-authored-not-historical",
    "mass": "exact-call-INC/INT;exact-formation-INT;minimal-call-QT;A-INT-and-pressure-QT-anchors",
    "roles": "DE-INC-strict-vs-revisedA;DE-INT-pairs-exact+/-2;F-QT7/9-exact+3;INC6/8-counter",
    "counterplay_revision": "root-approved-F6/8-total-normal-INC+INT+QT-strictly-below-revisedA",
    "domain": "normal/nonOOB/fixed-located-INC/INT/QT/numeric;all-other-whole-facts-fixed",
    "depth": "short6/7-lower-CDF;long8/9-upper-CDF;source-only-rational-ties-retained-tails",
    "objective": (
        "hard;requested-family-L1;complete-partition-L1;original-formation-numeric-mean;"
        "family/numeric-edits;canonical"
    ),
    "depth_objective": "subsequent-constrained-W1/CDF;not-global-layout-plus-payload-edit-optimum",
    "depth_staging": (
        "canonical-aggregate-W1/CDF-witness-then-pair-balance-conditional-on-selected-"
        "weight/atom-counts;chosen-layout-tail-failure-is-not-global-infeasibility"
    ),
    "encoder": "exact-adjacent-integers;deterministic-no-seed",
    "unknown": "source-unknown-retained;conditional-truth-and-historical-fit-UNVERIFIED",
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def model_identity() -> dict[str, object]:
    return {
        "origin": CONTRACT["origin"],
        "sha256": _digest(CONTRACT),
        "authored_experimental": True,
        "contract": json.loads(json.dumps(CONTRACT)),
    }


def _active(row: DefensiveCell) -> bool:
    c = row.cell
    return (
        c.priority is Priority.NORMAL
        and not c.out_of_bounds
        and c.variable is None
        and (
            c.kind in NUMERIC
            or c.kind in FAMILIES
            and (c.kind is not ResultKind.INTERCEPTION or type(c.yards) is int)
        )
    )


def _mass(rows: tuple[DefensiveCell, ...]) -> tuple[int, int, int]:
    return tuple(
        sum(
            WEIGHTS[r.roll - 1]
            for r in rows
            if r.cell.kind is kind
            and r.cell.priority is Priority.NORMAL
            and not r.cell.out_of_bounds
        )
        for kind in FAMILIES
    )  # type: ignore[return-value]


@dataclass(frozen=True)
class ColumnOption:
    mass: tuple[int, int, int]
    codes: tuple[int, ...]
    values: tuple[int, ...]
    mean_error: Fraction
    edits: int

    @property
    def tie(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        return self.codes, self.values


def enumerate_column(
    rows: tuple[DefensiveCell, ...], *, int_cap: int, qt_cap: int
) -> dict[tuple[int, int, int], ColumnOption]:
    """Enumerate whole-row families, then exact numeric mean/edit encodings.

    Fixed normal active-family mass is included even when its whole cell cannot
    change. All same-mass assignments compete; a mass witness alone is not an
    encoder optimum. Payload edits are accounted in the later depth stage.
    """
    if (
        tuple(r.roll for r in rows) != (1, 2, 3, 4, 5)
        or len({(r.defense, r.play) for r in rows}) != 1
    ):
        raise ValueError("coupled column requires five addressed rows of one coordinate")
    if any(type(x) is not int or not 0 <= x <= 36 for x in (int_cap, qt_cap)):
        raise ValueError("coupled mass caps require integer mass0..36")
    mutable = tuple(i for i, r in enumerate(rows) if _active(r))
    original_numeric = tuple(i for i in mutable if rows[i].cell.kind in NUMERIC)
    if not original_numeric:
        return {}
    target = Fraction(
        sum(WEIGHTS[i] * (rows[i].cell.yards or 0) for i in original_numeric),
        sum(WEIGHTS[i] for i in original_numeric),
    )
    low = target.numerator // target.denominator
    values = (low,) if target.denominator == 1 else (low, low + 1)
    fixed = tuple(
        sum(
            WEIGHTS[i]
            for i, r in enumerate(rows)
            if i not in mutable
            and r.cell.kind is k
            and r.cell.priority is Priority.NORMAL
            and not r.cell.out_of_bounds
        )
        for k in FAMILIES
    )
    result = {}
    for assignment in product(range(4), repeat=len(mutable)):
        numeric = tuple(i for i, code in zip(mutable, assignment, strict=True) if code == 0)
        if not numeric:
            continue
        mass = tuple(
            fixed[j]
            + sum(WEIGHTS[i] for i, code in zip(mutable, assignment, strict=True) if code == j + 1)
            for j in range(3)
        )
        if mass[1] > int_cap or mass[2] > qt_cap:
            continue
        codes = [-1] * 5
        for i, code in zip(mutable, assignment, strict=True):
            codes[i] = code
        for encoded in product(values, repeat=len(numeric)):
            actual = Fraction(
                sum(WEIGHTS[i] * x for i, x in zip(numeric, encoded, strict=True)),
                sum(WEIGHTS[i] for i in numeric),
            )
            full_values = [0] * 5
            for i, x in zip(numeric, encoded, strict=True):
                full_values[i] = x
            edits = sum(
                (format_cell(r.cell) != (str(full_values[i]) if full_values[i] else ""))
                if codes[i] == 0
                else r.cell.kind is not FAMILIES[codes[i] - 1]
                for i, r in enumerate(rows)
                if codes[i] != -1
            )
            option = ColumnOption(
                (mass[0], mass[1], mass[2]),
                tuple(codes),
                tuple(full_values),
                abs(actual - target),
                edits,
            )
            if mass not in result or (option.mean_error, option.edits, option.tie) < (
                result[mass].mean_error,
                result[mass].edits,
                result[mass].tie,
            ):
                result[mass] = option
    return result


Score = tuple[Fraction | int, ...]


def _add(a: Score, b: Score) -> Score:
    return tuple(x + y for x, y in zip(a, b, strict=True))


ZERO: Score = (Fraction(), Fraction(), Fraction(), 0)


def _solve(
    columns: dict[tuple[Defense, Play], tuple[DefensiveCell, ...]],
    *,
    budget_aware: bool = False,
) -> tuple[dict[tuple[Defense, Play], ColumnOption], dict[str, object]]:
    original = {key: _mass(rows) for key, rows in columns.items()}
    inc_budgets = tuple(sum(original[d, p][0] for d in FORMS) for p in PLAYS)
    int_budgets = tuple(sum(original[d, p][1] for d in FORMS) for p in PLAYS)
    form_budgets = tuple(sum(original[d, p][1] for p in PLAYS) for d in FORMS)
    positive = any(int_budgets)
    qt_budgets = []
    for p in PLAYS:
        fixed_other = sum(
            WEIGHTS[r.roll - 1]
            for d in FORMS
            if d is not Defense.F
            for r in columns[d, p]
            if not _active(r)
            and r.cell.kind is ResultKind.QUARTERBACK_TRAPPED
            and r.cell.priority is Priority.NORMAL
            and not r.cell.out_of_bounds
        )
        required = original[Defense.A, p][2] + 3 if p in (Play.SEVEN, Play.NINE) else 0
        if p in (Play.SEVEN, Play.NINE):
            # A's pressure anchor is mandatory even when that row is mutable.
            fixed_a = sum(
                WEIGHTS[r.roll - 1]
                for r in columns[Defense.A, p]
                if not _active(r)
                and r.cell.kind is ResultKind.QUARTERBACK_TRAPPED
                and r.cell.priority is Priority.NORMAL
                and not r.cell.out_of_bounds
            )
            fixed_other += original[Defense.A, p][2] - fixed_a
        baseline_qt = sum(original[d, p][2] for d in FORMS)
        qt_budgets.append(baseline_qt if budget_aware else max(baseline_qt, required + fixed_other))
    zero: Score = (0, *ZERO) if budget_aware else ZERO
    options = {
        (d, p): enumerate_column(
            columns[d, p], int_cap=min(36, int_budgets[i]), qt_cap=min(36, qt_budgets[i])
        )
        for i, p in enumerate(PLAYS)
        for d in FORMS
    }
    report: dict[str, object] = {
        "INC_call_budgets": inc_budgets,
        "INT_call_budgets": int_budgets,
        "INT_formation_budgets": form_budgets,
        "QT_call_budgets": tuple(qt_budgets),
        "int_incidence": "positive-preserved-modeled-budget"
        if positive
        else "modeled-zero-no-floor",
    }
    profiles = {}
    a_profile = tuple(original[Defense.A, p][1] for p in PLAYS)
    for j, d in enumerate(FORMS):
        domains = [sorted({o.mass[1] for o in options[d, p].values()}) for p in PLAYS]
        candidates = []
        for profile in product(*domains):
            if sum(profile) != form_budgets[j]:
                continue
            if d is Defense.A and profile != a_profile:
                continue
            if positive and d in (Defense.D, Defense.E):
                sign = 1 if d is Defense.D else -1
                if budget_aware:
                    if (sum(profile[:2]) - sum(a_profile[:2])) * sign < 0 or (
                        sum(profile[2:]) - sum(a_profile[2:])
                    ) * sign > 0:
                        continue
                elif (
                    sum(profile[:2]) != sum(a_profile[:2]) + sign * 2
                    or sum(profile[2:]) != sum(a_profile[2:]) - sign * 2
                ):
                    continue
            candidates.append(profile)
        profiles[d] = candidates
    cache: dict[tuple[int, tuple[int, ...]], tuple[Score, tuple[ColumnOption, ...]] | None] = {}

    def call_best(i: int, ints: tuple[int, ...]) -> tuple[Score, tuple[ColumnOption, ...]] | None:
        key = i, ints
        if key in cache:
            return cache[key]
        p = PLAYS[i]
        candidates = {
            d: tuple(o for o in options[d, p].values() if o.mass[1] == ints[j])
            for j, d in enumerate(FORMS)
        }
        best: tuple[Score, tuple[ColumnOption, ...]] | None = None
        for a in candidates[Defense.A]:
            if p in (Play.SEVEN, Play.NINE) and a.mass[2] != original[Defense.A, p][2]:
                continue
            allowed = {}
            for d in FORMS:
                selected = []
                for o in (a,) if d is Defense.A else candidates[d]:
                    if d in (Defense.D, Defense.E):
                        sign = 1 if (d is Defense.D) == (i < 2) else -1
                        if (o.mass[0] - a.mass[0]) * sign < (0 if budget_aware else 1):
                            continue
                    if d is Defense.F:
                        if p in (Play.SEVEN, Play.NINE):
                            if (
                                o.mass[2] < a.mass[2]
                                if budget_aware
                                else o.mass[2] != a.mass[2] + 3
                            ):
                                continue
                        elif (
                            o.mass[0] > a.mass[0] if budget_aware else o.mass[0] >= a.mass[0]
                        ) or o.mass[2] > (a.mass[2] if budget_aware else original[Defense.A, p][2]):
                            continue
                        elif (
                            sum(o.mass) > sum(a.mass)
                            if budget_aware
                            else sum(o.mass) >= sum(a.mass)
                        ):
                            # An INC concession cannot be relabelled counterplay
                            # when added INT/QT consumes all ordinary opportunity.
                            continue
                    selected.append(o)
                allowed[d] = selected
            states: dict[tuple[int, int], tuple[Score, tuple[ColumnOption, ...]]] = {
                (0, 0): (zero, ())
            }
            for d in FORMS:
                nxt = {}
                target = list(original[d, p])
                if d in (Defense.D, Defense.E):
                    sign = 1 if (d is Defense.D) == (i < 2) else -1
                    target[0] = original[Defense.A, p][0] + sign * 3
                    if positive:
                        target[1] = original[Defense.A, p][1] + sign
                if d is Defense.F:
                    target[2 if i % 2 else 0] = original[Defense.A, p][2 if i % 2 else 0] + (
                        3 if i % 2 else -3
                    )
                # Alpha signed opportunities are scored against revised A;
                # the separate anchor is the original nonnegative partition.
                if budget_aware:
                    target = list(original[d, p])
                elif any(t < 0 for t in target):
                    states = {}
                    break
                for (inc, qt), (score, witness) in states.items():
                    for o in allowed[d]:
                        after = inc + o.mass[0], qt + o.mass[2]
                        if after[0] > inc_budgets[i] or after[1] > qt_budgets[i]:
                            continue
                        family = Fraction(
                            sum(abs(v - t) for v, t in zip(o.mass, target, strict=True))
                        )
                        partition = family + abs(sum(o.mass) - sum(target))
                        local: Score = (family, partition, o.mean_error, o.edits)
                        if budget_aware:
                            role = 0
                            if d in (Defense.D, Defense.E) and inc_budgets[i]:
                                sign = 1 if (d is Defense.D) == (i < 2) else -1
                                role += abs(o.mass[0] - a.mass[0] - sign * 3)
                            if d is Defense.F:
                                if i % 2 and qt_budgets[i]:
                                    role += abs(o.mass[2] - a.mass[2] - 3)
                                elif not i % 2:
                                    if inc_budgets[i]:
                                        role += abs(o.mass[0] - a.mass[0] + 3)
                                    if inc_budgets[i] + int_budgets[i] + qt_budgets[i]:
                                        role += abs(sum(o.mass) - sum(a.mass) + 3)
                            local = (role, *local)
                        total = _add(score, local)
                        candidate = total, witness + (o,)
                        if after not in nxt or (total, tuple(x.tie for x in candidate[1])) < (
                            nxt[after][0],
                            tuple(x.tie for x in nxt[after][1]),
                        ):
                            nxt[after] = candidate
                states = nxt
            candidate = states.get((inc_budgets[i], qt_budgets[i]))
            if candidate is not None and (
                best is None
                or (candidate[0], tuple(x.tie for x in candidate[1]))
                < (best[0], tuple(x.tie for x in best[1]))
            ):
                best = candidate
        cache[key] = best
        return best

    # Enumerate complete formation INT profiles; prune call totals before the
    # expensive INC/QT DPs. No independently rounded family is committed first.
    best: tuple[Score, tuple[ColumnOption, ...]] | None = None
    evaluated = 0

    def visit(j: int, used: tuple[int, ...], chosen: tuple[tuple[int, ...], ...]) -> None:
        nonlocal best, evaluated
        if j < len(FORMS):
            for profile in profiles[FORMS[j]]:
                after = tuple(a + b for a, b in zip(used, profile, strict=True))
                if all(v <= limit for v, limit in zip(after, int_budgets, strict=True)):
                    visit(j + 1, after, chosen + (profile,))
            return
        if used != int_budgets:
            return
        evaluated += 1
        solved = [call_best(i, tuple(profile[i] for profile in chosen)) for i in range(4)]
        if any(s is None for s in solved):
            return
        score = zero
        witness = []
        for item in solved:
            assert item is not None
            score = _add(score, item[0])
            witness.extend(item[1])
        if budget_aware and positive:
            pair_loss = sum(
                abs(sum(chosen[j][:2]) - sum(a_profile[:2]) - sign * 2)
                + abs(sum(chosen[j][2:]) - sum(a_profile[2:]) + sign * 2)
                for j, sign in ((3, 1), (4, -1))
            )
            score = (score[0] + pair_loss, *score[1:])
        candidate = score, tuple(witness)
        if best is None or (score, tuple(x.tie for x in witness)) < (
            best[0],
            tuple(x.tie for x in best[1]),
        ):
            best = candidate

    visit(0, (0, 0, 0, 0), ())
    report["complete_INT_matrices_evaluated"] = evaluated
    if best is None:
        return {}, {
            **report,
            "status": "REVIEW_REQUIRED",
            "reason": "joint-budget/role/domain-infeasible",
        }
    score, witness = best
    report.update(
        status="represented",
        objective=tuple(str(x) for x in score),
        objective_scope="family/numeric-edits-before-coupled-depth-payload;not-global-layout+payload-edit-optimum",
    )
    return {
        (d, p): witness[i * 6 + j] for i, p in enumerate(PLAYS) for j, d in enumerate(FORMS)
    }, report


def apply_coupled_model(
    chart: TeamChart,
    *,
    known_depths: DepthSupport,
    unknown_locations: int,
    source_identity: str,
    _budget_aware: bool = False,
) -> tuple[TeamChart, dict[str, object]]:
    """Preserve whole-defense budgets and transport the conditional known CDF.

    Source identity binds supplied evidence, not its historical completeness.
    Unknown locations never become observed zero or additional known samples.
    """
    if type(chart) is not TeamChart or type(unknown_locations) is not int or unknown_locations < 0:
        raise ValueError(
            "coupled model requires a complete chart and nonnegative integer unknown count"
        )
    if (
        type(source_identity) is not str
        or len(source_identity) != 64
        or any(c not in "0123456789abcdef" for c in source_identity)
    ):
        raise ValueError("coupled model requires a frozen source identity")
    original = semantic_sha256(chart)
    columns = {
        (d, p): tuple(
            sorted(
                (r for r in chart.defense if r.defense is d and r.play is p), key=lambda r: r.roll
            )
        )
        for p in PLAYS
        for d in FORMS
    }
    selected, report = _solve(columns, budget_aware=_budget_aware)
    identity = model_identity()
    if _budget_aware:
        from .alpha_event_risks import model_identity as alpha_identity

        identity = alpha_identity()
    report.update(
        model_identity=identity,
        baseline_sha256=original,
        source_identity=source_identity,
        source_unknown_locations=unknown_locations,
        source_conditional_status="UNKNOWN",
        source_fit="UNVERIFIED",
    )
    if not selected:
        return chart, report
    cells = {(r.defense, r.play, r.roll): r for r in chart.defense}
    depth_locations = {}
    depth_reports = {}
    # Fixed variable/unlocated INT facts are preserved, not imputed by the known
    # located-payload model. Its CDF mixture uses only mutable located INT slots.
    total_int = sum(
        WEIGHTS[i] for o in selected.values() for i, code in enumerate(o.codes) if code == 2
    )
    short_int = sum(
        WEIGHTS[i]
        for (d, p), o in selected.items()
        if p.value <= 7
        for i, code in enumerate(o.codes)
        if code == 2
    )
    report["fixed_normal_INT_mass_outside_depth_transport"] = (
        sum(o.mass[1] for o in selected.values()) - total_int
    )
    report["depth_population"] = (
        "mutable-normal-located-INT-only;fixed-variable/unlocated-preserved"
    )
    if total_int:
        lower, upper = split_depths(known_depths, Fraction(short_int, total_int))
        for name, plays, support in (("short", PLAYS[:2], lower), ("long", PLAYS[2:], upper)):
            coords = tuple(
                (d, p, i + 1)
                for p in plays
                for d in FORMS
                for i, code in enumerate(selected[d, p].codes)
                if code == 2
            )
            allocation = quantize_depths(tuple(WEIGHTS[r - 1] for _, _, r in coords), support)
            balanced, balance_error = (
                balance_pair(
                    tuple(WEIGHTS[r - 1] for _, _, r in coords),
                    allocation.locations,
                    tuple(int(p is plays[1]) for _, p, _ in coords),
                    support,
                )
                if allocation.status in {"represented", "dormant"}
                else ((), None)
            )
            depth_reports[name] = {
                "status": allocation.status,
                "known_support": tuple((x, str(w)) for x, w in support),
                "represented_histogram": allocation.histogram,
                "wasserstein": str(allocation.wasserstein),
                "cdf_error": str(allocation.cdf_error),
                "tails": "constrained-source-only",
                "coordinate_balance": "exact-call-pair-W1-with-fixed-selected-weight/atom-counts",
                "pair_wasserstein_sum": str(balance_error),
            }
            if allocation.status not in {"represented", "dormant"}:
                return chart, {
                    **report,
                    "status": "REVIEW_REQUIRED",
                    "reason": "depth-tail-infeasible",
                    "depth": depth_reports,
                }
            depth_locations.update(zip(coords, balanced, strict=True))
    ancestry = {}
    for (d, p), option in selected.items():
        for i, code in enumerate(option.codes):
            old = columns[d, p][i]
            if code == -1:
                continue
            token = (
                (str(option.values[i]) if option.values[i] else "")
                if code == 0
                else "BLACK"
                if code == 1
                else "QT"
                if code == 3
                else f"INT {depth_locations[d, p, i + 1]}"
            )
            color = chart_color_for_csv_token(token)
            if token == format_cell(old.cell):
                continue
            recipe = {
                "model": identity["sha256"],
                "baseline": original,
                "source": source_identity,
                "coordinate": (d.value, p.value, i + 1),
                "baseline_cell": semantic_sha256(old),
                "token": token,
            }
            sha = _digest(recipe)
            ancestry[sha] = recipe
            provenance = Provenance(
                sha,
                str(identity["origin"]) + ".json",
                1,
                BoundingBox(p.value, i + 1, p.value + 1, i + 2),
                token,
                CELL_LEGEND[color].rgb_color,
            )
            cells[d, p, i + 1] = replace(old, cell=parse_cell(token, provenance))
    candidate = replace(
        chart, defense=tuple(cells[r.defense, r.play, r.roll] for r in chart.defense)
    )
    if semantic_sha256(chart) != original:
        raise ValueError("coupled input changed before returning candidate")
    report.update(
        output_sha256=semantic_sha256(candidate),
        depth=depth_reports,
        derived_ancestry=ancestry,
        columns={
            f"{d.value}/{p.value}": {
                "represented_INC_INT_QT": o.mass,
                "mean_error": str(o.mean_error),
                "family_numeric_edits": o.edits,
                "codes": o.codes,
                "original_numeric_histogram": tuple(
                    sorted(
                        Counter(
                            (r.cell.yards or 0)
                            for r in columns[d, p]
                            if _active(r) and r.cell.kind in NUMERIC
                            for _ in range(WEIGHTS[r.roll - 1])
                        ).items()
                    )
                ),
                "represented_numeric_histogram": tuple(
                    sorted(
                        Counter(
                            o.values[i]
                            for i, code in enumerate(o.codes)
                            if code == 0
                            for _ in range(WEIGHTS[i])
                        ).items()
                    )
                ),
            }
            for (d, p), o in selected.items()
        },
        depth_payload_edits=sum(
            old.cell.kind is ResultKind.INTERCEPTION
            and new.cell.kind is ResultKind.INTERCEPTION
            and old.cell.yards != new.cell.yards
            for old, new in zip(chart.defense, candidate.defense, strict=True)
        ),
    )
    return candidate, report
