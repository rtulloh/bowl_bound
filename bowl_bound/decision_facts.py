"""Engine-projected public outcomes for choices that can be decided without new rolls."""

from dataclasses import dataclass
from enum import Enum


class DecisionOutcomeKind(str, Enum):
    """How much of a choice's next result is deterministic before another roll."""

    FIELD = "field"
    TOUCHDOWN = "touchdown"
    SAFETY = "safety"
    TURNOVER = "turnover"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class DecisionOutcome:
    """A deterministic or explicitly unresolved result for one enabled choice."""

    choice_id: str
    kind: DecisionOutcomeKind
    possession: str | None = None
    yards_to_goal: int | None = None
    down: int | None = None
    yards_to_go: int | None = None
    scoring_side: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.choice_id, str) or not self.choice_id:
            raise ValueError("choice_id must be a non-empty string")
        if type(self.kind) is not DecisionOutcomeKind:
            raise TypeError("kind must be a DecisionOutcomeKind")
        for name in ("possession", "scoring_side"):
            value = getattr(self, name)
            if value is not None and value not in {"home", "away"}:
                raise ValueError(f"{name} must be home, away or None")
        for name, value in (
            ("yards_to_goal", self.yards_to_goal),
            ("down", self.down),
            ("yards_to_go", self.yards_to_go),
        ):
            if value is not None and type(value) is not int:
                raise TypeError(f"{name} must be an integer or None")
        if self.kind is DecisionOutcomeKind.FIELD and any(
            value is None
            for value in (
                self.possession,
                self.yards_to_goal,
                self.down,
                self.yards_to_go,
            )
        ):
            raise ValueError("field outcomes require a complete field state")
        if self.kind in {DecisionOutcomeKind.TOUCHDOWN, DecisionOutcomeKind.SAFETY} and (
            self.scoring_side is None
        ):
            raise ValueError("scoring outcomes require a scoring side")
