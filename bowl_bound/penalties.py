"""Bowl Bound penalty rerolls (Basic VI-4); no accept/decline or state mutation here."""

from dataclasses import dataclass, replace

from .dice import DiceSource
from .models import (
    Defense,
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
    TeamChart,
)
from .penalty_yardage import AssessedPenalty, assess_penalty
from .resolution import (
    LookupTrace,
    PlayResolution,
    _supplemental_result,
    _variable_result,
    resolve_cells,
    resolve_play,
)

MAX_PENALTY_REROLLS = 100


@dataclass(frozen=True)
class PreparedPlay:
    resolution: PlayResolution
    penalties: tuple[AssessedPenalty, ...] = ()
    offsetting: bool = False
    pre_snap: bool = False
    no_elapsed_time: bool = False


def prepare_play(
    offense: TeamChart,
    defense: TeamChart,
    play: Play,
    formation: Defense,
    dice: DiceSource,
    *,
    hurried: bool = False,
    hail_mary: bool = False,
) -> PreparedPlay:
    """Resolve a snap and penalty rerolls, retaining the original effective defense.

    S/R assessment dice precede the next offensive chart roll. PI cancels defense and
    stops all offensive rerolls; pre-snap 5A and offsetting fouls also stop immediately.
    All observed cells and assessment rolls are kept in their actual order.
    """
    initial = (
        _hail_mary_resolution(offense, dice)
        if hail_mary
        else resolve_play(offense, defense, play, formation, dice)
    )
    resolution = initial
    trace = list(initial.trace)
    penalties: list[AssessedPenalty] = []
    attempts = 0
    while resolution.result.kind is ResultKind.PENALTY:
        if attempts >= MAX_PENALTY_REROLLS:
            raise ValueError("penalty reroll limit exceeded; inspect the chart")
        attempts += 1
        cell = resolution.result.offense
        data = cell.penalty
        if data is None:
            raise ValueError("penalty result is missing its penalty data")
        assessed = assess_penalty(data, dice, hurried=hurried)
        if (
            not hail_mary
            and data.code is PenaltyCode.PI
            and any(entry.section in {"supplemental:QR", "supplemental:QT"} for entry in trace)
        ):
            assessed = replace(assessed, yards=10, automatic_first_down=False, pi_as_def10=True)
        if assessed.roll is not None:
            trace.append(
                LookupTrace(
                    "penalty_yardage",
                    offense.name,
                    offense.season,
                    resolution.resolved_play,
                    None,
                    assessed.roll,
                    cell,
                )
            )
        for distance_roll in assessed.distance_rolls:
            trace.append(
                LookupTrace(
                    "penalty_distance",
                    offense.name,
                    offense.season,
                    resolution.resolved_play,
                    None,
                    distance_roll,
                    cell,
                )
            )
        if assessed.bad_snap:
            fumble = NormalizedCell(ResultKind.FUMBLE, cell.provenance, yards=-2)
            blank = NormalizedCell(ResultKind.NO_CHANGE, cell.provenance)
            return PreparedPlay(
                PlayResolution(
                    play,
                    resolution.resolved_play,
                    resolve_cells(fumble, blank),
                    tuple(trace),
                    bad_snap=True,
                )
            )
        if assessed.no_elapsed_time:
            blank = NormalizedCell(ResultKind.NO_CHANGE, cell.provenance)
            return PreparedPlay(
                PlayResolution(
                    play, resolution.resolved_play, resolve_cells(blank, blank), tuple(trace)
                ),
                (assessed,),
                pre_snap=True,
                no_elapsed_time=True,
            )
        if not assessed.no_foul:
            penalties.append(assessed)
        # Offsetting fouls end the attempt, even if the latest result was PI.
        if len({p.source.team for p in penalties}) > 1:
            return PreparedPlay(_with_trace(resolution, trace), tuple(penalties), offsetting=True)
        if assessed.pre_snap:
            return PreparedPlay(_with_trace(resolution, trace), tuple(penalties), pre_snap=True)
        effective_defense = resolution.result.defense
        if data.code is PenaltyCode.PI:
            incomplete = NormalizedCell(ResultKind.INCOMPLETE, cell.provenance)
            blank = NormalizedCell(ResultKind.NO_CHANGE, effective_defense.provenance)
            resolution = PlayResolution(
                play, resolution.resolved_play, resolve_cells(incomplete, blank), tuple(trace)
            )
            return PreparedPlay(resolution, tuple(penalties))
        roll = dice.offensive()
        current_play = resolution.resolved_play
        rerolled = next(
            r.cell for r in offense.offense if r.play is current_play and r.roll == roll.total
        )
        trace.append(
            LookupTrace(
                "penalty_reroll", offense.name, offense.season, current_play, None, roll, rerolled
            )
        )
        if rerolled.kind in {ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS}:
            current_play = Play.SEVEN if rerolled.kind is ResultKind.SPRINT_OUT_PASS else Play.EIGHT
            effective_defense = NormalizedCell(ResultKind.NO_CHANGE, effective_defense.provenance)
            option_roll = dice.offensive()
            rerolled = next(
                r.cell
                for r in offense.offense
                if r.play is current_play and r.roll == option_roll.total
            )
            trace.append(
                LookupTrace(
                    "option",
                    offense.name,
                    offense.season,
                    current_play,
                    None,
                    option_roll,
                    rerolled,
                )
            )
        combined = resolve_cells(rerolled, effective_defense)
        combined = _supplemental_result(offense, combined, current_play, dice, trace)
        combined = _variable_result(combined, offense, defense, current_play, dice, trace)
        resolution = PlayResolution(play, current_play, combined, tuple(trace))
    return PreparedPlay(_with_trace(resolution, trace), tuple(penalties))


def _with_trace(resolution: PlayResolution, trace: list[LookupTrace]) -> PlayResolution:
    return PlayResolution(
        resolution.called_play, resolution.resolved_play, resolution.result, tuple(trace)
    )


def prepare_hail_mary(
    offense: TeamChart, dice: DiceSource, *, hurried: bool = False
) -> PreparedPlay:
    """Prepare the rule-table pass with a blank defense, including QT and PI."""
    return prepare_play(
        offense, offense, Play.EIGHT, Defense.A, dice, hurried=hurried, hail_mary=True
    )


def _hail_mary_resolution(offense: TeamChart, dice: DiceSource) -> PlayResolution:
    from hashlib import sha256

    from .models import BoundingBox, Provenance

    # Explicit engine-generated provenance, not a fabricated imported chart cell.
    provenance = Provenance(
        sha256(b"Bowl Bound Advanced I-3").hexdigest(),
        "engine:rules/hail-mary",
        1,
        BoundingBox(0, 0, 1, 1),
        "Advanced I-3 Hail Mary table",
        (255, 255, 255),
    )
    roll = dice.offensive()
    total = roll.total
    kind = (
        ResultKind.YARDS
        if total <= 18
        else ResultKind.TOUCHDOWN
        if total == 19
        else ResultKind.QUARTERBACK_TRAPPED
        if total in {24, 25}
        else ResultKind.INTERCEPTION
        if total <= 29
        else ResultKind.INCOMPLETE
        if total <= 38
        else ResultKind.PENALTY
    )
    # The first trace is the rule-table consultation. Distance rolls are separate.
    cell = NormalizedCell(
        kind,
        provenance,
        yards=0 if kind in {ResultKind.YARDS, ResultKind.INTERCEPTION} else None,
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, yards=15)
        if kind is ResultKind.PENALTY
        else None,
    )
    trace = [LookupTrace("hail_mary", offense.name, offense.season, Play.EIGHT, None, roll, cell)]
    if kind in {ResultKind.YARDS, ResultKind.INTERCEPTION, ResultKind.PENALTY}:
        distance = dice.offensive()
        trace.append(
            LookupTrace(
                "hail_mary_distance", offense.name, offense.season, Play.EIGHT, None, distance, cell
            )
        )
        yards = 25 + distance.total
        cell = (
            replace(cell, yards=yards)
            if kind is not ResultKind.PENALTY
            else replace(
                cell, penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.PI, yards=yards)
            )
        )
    blank = NormalizedCell(ResultKind.NO_CHANGE, provenance)
    result = _supplemental_result(offense, resolve_cells(cell, blank), Play.EIGHT, dice, trace)
    return PlayResolution(Play.EIGHT, Play.EIGHT, result, tuple(trace))
