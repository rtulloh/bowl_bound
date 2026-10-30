"""Original fictional sample data, authored independently of historical charts.

The versioned recipe and generated chart values are dedicated to the public domain
under CC0-1.0. See docs/sample-teams.md. No PDF or test fixture is an input.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path

from .models import (
    BoundingBox,
    Defense,
    DefensiveCell,
    NormalizedCell,
    OffensiveCell,
    PatOutcome,
    Play,
    Provenance,
    SpecialTeamsCell,
    SpecialTeamsColumn,
    SupplementalCell,
    SupplementalColumn,
    TeamChart,
)
from .normalization import CELL_LEGEND, chart_color_for_csv_token
from .team_csv import (
    TeamFileMetadata,
    parse_cell,
    provenance_to_csv,
    team_folder_name,
    team_to_files,
)

RECIPE = "Original fictional Bowl Bound sample-teams-v2: Cedar Valley / Harbor Tech; CC0-1.0"
SOURCE_HASH = sha256(RECIPE.encode()).hexdigest()


def _evidence(text: str, rgb_color: tuple[int, int, int] = (0, 0, 0)) -> Provenance:
    # Coordinates/page are schema-required synthetic placeholders, never PDF evidence.
    return Provenance(SOURCE_HASH, "sample-teams-v2", 1, BoundingBox(0, 0, 1, 1), text, rgb_color)


def _cell(text: str) -> NormalizedCell:
    color = chart_color_for_csv_token(text)
    return parse_cell(text, _evidence(text, CELL_LEGEND[color].rgb_color))


def _pat_outcome(roll: int, team_index: int) -> PatOutcome:
    good = roll not in (10, 11 + team_index)
    token = "G" if good else "NG"
    color = chart_color_for_csv_token("" if good else "NG")
    return PatOutcome(roll, good, _evidence(token, CELL_LEGEND[color].rgb_color))


def sample_teams() -> tuple[TeamChart, TeamChart]:
    """Build two complete, distinct 2007-rule-profile fictional teams deterministically."""
    charts = []
    for index, name in enumerate(("Cedar Valley", "Harbor Tech")):
        offense = []
        for play in Play:
            for roll in range(10, 40):
                running = play.value <= 5
                gain = (roll * (3 + index) + play.value * 2) % 18 - 4
                gain += (2 if index == 0 else -1) if running else (0 if index == 0 else 3)
                token = str(gain)
                if roll == 10:
                    token = "F + 2" if running else "INT 18"
                elif roll in (11, 12, 13) and not running:
                    token = "BLACK"
                elif roll == 14 and not running:
                    token = "PI 12"
                elif roll == 15:
                    token = "OFF 5"
                elif roll == 16:
                    token = "DEF 5"
                elif roll == 39:
                    token = "B" if running else "QR"
                # Only Option may redirect a called run to a passing column.
                # Exhaustive/variable-distance stress cells belong in unit fixtures.
                if play is Play.FIVE and roll in (37, 38):
                    token = "SOP" if roll == 37 else "BLP"
                offense.append(OffensiveCell(play, roll, _cell(token)))
        supplemental = tuple(
            SupplementalCell(
                column,
                roll,
                _cell(
                    str(
                        (12 + (roll * 3 + index) % 32)
                        if column is SupplementalColumn.BREAKAWAY
                        else (-9 + roll % 9)
                        if column is SupplementalColumn.QUARTERBACK_TRAPPED
                        else (-3 + (roll + index * 2) % 17)
                    )
                ),
            )
            for column in SupplementalColumn
            for roll in range(10, 40)
        )
        defense_rows = []
        for formation in Defense:
            for play in Play:
                for roll in range(1, 6):
                    token = str((roll + ord(formation.value) + play.value + index) % 7 - 3)
                    if formation is Defense.B and roll == 1:
                        token = "F - 4"
                    elif play.value >= Play.SIX.value:
                        if formation is Defense.E and roll == 1:
                            token = "INT 12"
                        elif formation is Defense.D and roll == 2:
                            token = "BLACK"
                        elif formation is Defense.F and roll == 1:
                            token = "QT"
                    defense_rows.append(DefensiveCell(formation, play, roll, _cell(token)))
        defense = tuple(defense_rows)
        special = []
        for column in SpecialTeamsColumn:
            for roll in range(10, 40):
                values = {
                    SpecialTeamsColumn.KICKOFF: 48 + (roll + index * 3) % 24,
                    SpecialTeamsColumn.KICKOFF_RETURN: 8 + (roll * 2 + index) % 25,
                    SpecialTeamsColumn.PUNT: 28 + (roll + index * 2) % 23,
                    SpecialTeamsColumn.PUNT_RETURN: -2 + (roll + index) % 20,
                    SpecialTeamsColumn.INTERCEPTION_RETURN: (roll * 2 + index) % 28,
                    SpecialTeamsColumn.FIELD_GOAL: 25 + (roll + index * 4) % 31,
                }
                special.append(SpecialTeamsCell(column, roll, _cell(str(values[column]))))
        charts.append(
            TeamChart(
                schema_version=1,
                name=name,
                season=2007,
                offense=tuple(offense),
                supplemental=supplemental,
                defense=defense,
                special_teams=tuple(special),
                pat_outcomes=tuple(_pat_outcome(roll, index) for roll in range(10, 40)),
                recovery_range=range(10, 26 + index),
            )
        )
    return tuple(charts)


def install_samples(seasons_root: Path) -> tuple[str, str]:
    """Install only absent sample files; identical files are safe to reuse.

    Conflicting files and symlinked destinations are refused before any writes.
    Existing historical teams are never inspected or modified.
    """
    pending: list[tuple[Path, str]] = []
    ids = []
    for chart in sample_teams():
        slug = team_folder_name(chart.name)
        ids.append(f"{chart.season}/{slug}")
        season = seasons_root / str(chart.season)
        meta = TeamFileMetadata(
            5.0,
            (),
            "Original fictional sample; CC0-1.0",
            SOURCE_HASH,
            (("rating", _evidence("5.0")),),
        )
        files = {season / slug / name: text for name, text in team_to_files(chart, meta).items()}
        files[season / "provenance" / f"{slug}.csv"] = provenance_to_csv(chart, meta)
        pending.extend(files.items())
    for path, text in pending:
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise FileExistsError(f"Refusing existing symlink: {path}")
        if path.exists() and (not path.is_file() or path.read_text(encoding="utf-8") != text):
            raise FileExistsError(f"Refusing to replace existing sample content: {path}")
    for path, text in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("x", encoding="utf-8", newline="") as output:
                output.write(text)
    return tuple(ids)


def main() -> None:
    """Install fictional samples without requiring the API or historical files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=Path, default=Path("seasons"))
    args = parser.parse_args()
    try:
        for team_id in install_samples(args.seasons):
            print(team_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Samples not installed: {error}\n")


if __name__ == "__main__":
    main()
