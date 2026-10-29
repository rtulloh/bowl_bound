"""College offensive credit from semantic engine facts, never presentation text.

Sacks are rushing attempts/losses, not pass attempts. Chart classification policy
and source boundaries are documented in docs/statistics.md.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

from .game_state import Possession
from .models import ResultKind
from .resolution import PlayResolution
from .turnovers import TurnoverTrace


class StatKind(str, Enum):
    EXCLUDED = "excluded"
    RUSH = "rush"
    COMPLETE = "completion"
    INCOMPLETE = "incomplete"
    INTERCEPTION = "interception"
    SACK = "sack"


@dataclass(frozen=True)
class PlayStatistics:
    """One committed snap's offensive credit; returns and penalties are not offense."""

    kind: StatKind = StatKind.EXCLUDED
    team: Possession | None = None
    yards: int = 0
    touchdown: bool = False


@dataclass(frozen=True)
class TeamStatistics:
    rushing_attempts: int = 0
    rushing_yards: int = 0
    rushing_touchdowns: int = 0
    passing_attempts: int = 0
    completions: int = 0
    passing_yards: int = 0
    passing_touchdowns: int = 0
    interceptions: int = 0
    sacks_taken: int = 0
    sack_yards_lost: int = 0
    total_plays: int = field(init=False)
    total_yards: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "total_plays", self.rushing_attempts + self.passing_attempts)
        object.__setattr__(self, "total_yards", self.rushing_yards + self.passing_yards)


@dataclass(frozen=True)
class StatisticsRow:
    label: str
    home: str
    away: str


@dataclass(frozen=True)
class StatisticsView:
    home: TeamStatistics = TeamStatistics()
    away: TeamStatistics = TeamStatistics()
    rows: tuple[StatisticsRow, ...] = ()


def clipped_yards(yards: int, yards_to_goal: int) -> int:
    """Measure to the goal lines, not chart overshoot or the depth of an end zone."""
    return max(yards_to_goal - 100, min(yards, yards_to_goal))


def scrimmage_credit(
    resolution: PlayResolution,
    team: Possession,
    yards: int,
    *,
    incomplete: bool = False,
    touchdown: bool = False,
) -> PlayStatistics:
    """Classify the final result, retaining Option and actual QR/QT branch evidence."""
    if resolution.bad_snap:
        return PlayStatistics(StatKind.RUSH, team, yards, touchdown)
    if incomplete or resolution.result.kind is ResultKind.INCOMPLETE:
        return PlayStatistics(StatKind.INCOMPLETE, team)
    if resolution.result.kind is ResultKind.INTERCEPTION:
        return PlayStatistics(StatKind.INTERCEPTION, team)
    branch = None
    for entry in reversed(resolution.trace):
        if entry.section in {"supplemental:QR", "supplemental:QT"}:
            branch = entry.section
            break
        if entry.section == "penalty_reroll":
            break  # Earlier branches belong to a discarded chart result.
    if branch == "supplemental:QT" and yards < 0:
        kind = StatKind.SACK
    elif branch or resolution.resolved_play.value <= 5:
        kind = StatKind.RUSH
    else:
        kind = StatKind.COMPLETE
    return PlayStatistics(kind, team, yards, touchdown)


def fumble_yards(
    location: int,
    yards_to_goal: int,
    trace: tuple[TurnoverTrace, ...],
    recovery_range: range,
    *,
    return_credit: int | None = None,
) -> int:
    """Audit original-team advances only up to the first observed opponent recovery.

    Recovery rolls and normalized return cells are already resolved evidence. No
    dice, field transitions or source-token parsing occurs here. Later reacquisition
    cannot turn a defensive return into rushing/passing yardage.
    """
    gain = clipped_yards(location, yards_to_goal)
    return_sections = {"turnover_return", "turnover_return_reroll"}
    last_return = max((i for i, e in enumerate(trace) if e.section in return_sections), default=-1)
    for index, entry in enumerate(trace):
        if entry.section == "fumble_recovery" and entry.roll.total not in recovery_range:
            break
        if entry.section not in return_sections or entry.cell is None:
            continue
        if return_credit is not None and index == last_return:
            return clipped_yards(gain + return_credit, yards_to_goal)
        cell = entry.cell
        if cell.kind is ResultKind.TOUCHDOWN:
            return yards_to_goal
        if cell.kind in {ResultKind.YARDS, ResultKind.FUMBLE} and cell.yards is not None:
            gain = clipped_yards(gain + cell.yards, yards_to_goal)
    return gain


def _team_statistics(credits: tuple[PlayStatistics, ...], team: Possession) -> TeamStatistics:
    own = tuple(c for c in credits if c.team is team and c.kind is not StatKind.EXCLUDED)
    rushes = tuple(c for c in own if c.kind in {StatKind.RUSH, StatKind.SACK})
    passes = tuple(
        c
        for c in own
        if c.kind
        in {
            StatKind.COMPLETE,
            StatKind.INCOMPLETE,
            StatKind.INTERCEPTION,
        }
    )
    return TeamStatistics(
        rushing_attempts=len(rushes),
        rushing_yards=sum(c.yards for c in rushes),
        rushing_touchdowns=sum(c.touchdown for c in rushes),
        passing_attempts=len(passes),
        completions=sum(c.kind is StatKind.COMPLETE for c in passes),
        passing_yards=sum(c.yards for c in passes),
        passing_touchdowns=sum(c.touchdown for c in passes),
        interceptions=sum(c.kind is StatKind.INTERCEPTION for c in passes),
        sacks_taken=sum(c.kind is StatKind.SACK for c in rushes),
        sack_yards_lost=-sum(c.yards for c in rushes if c.kind is StatKind.SACK),
    )


def summarize(credits: Iterable[PlayStatistics]) -> StatisticsView:
    """Fold committed credits, with engine-formatted labels for display-only clients."""
    credits = tuple(credits)
    home, away = (_team_statistics(credits, team) for team in Possession)
    rows = []
    for label, attribute in (
        ("Rushing attempts", "rushing_attempts"),
        ("Rushing yards", "rushing_yards"),
        ("Rushing touchdowns", "rushing_touchdowns"),
        ("Pass attempts", "passing_attempts"),
        ("Completions", "completions"),
        ("Passing yards", "passing_yards"),
        ("Passing touchdowns", "passing_touchdowns"),
        ("Interceptions thrown", "interceptions"),
        ("Sacks taken", "sacks_taken"),
        ("Sack yards lost", "sack_yards_lost"),
        ("Total offensive plays", "total_plays"),
        ("Total offense yards", "total_yards"),
    ):
        rows.append(
            StatisticsRow(label, str(getattr(home, attribute)), str(getattr(away, attribute)))
        )
    return StatisticsView(home, away, tuple(rows))
