# ruff: noqa: E501, E701, E702, B905, I001, E741
"""Paydirt-layout CSV and YAML interchange; chart colors remain provenance evidence."""

from __future__ import annotations
import csv
import io
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path
import yaml
from .models import (
    BoundingBox,
    Defense,
    DefensiveCell,
    NormalizedCell,
    OffensiveCell,
    PatOutcome,
    PenaltyCode,
    PenaltyTeam,
    Play,
    Priority,
    Provenance,
    ResultKind,
    SpecialTeamsCell,
    SpecialTeamsColumn,
    SupplementalCell,
    SupplementalColumn,
    TeamChart,
)
from .normalization import ChartColor, NormalizationError, normalize_cell

TEAM_FILES: tuple[str, ...] = ("offense.csv", "defense.csv", "special.csv", "team.yaml")
PROVENANCE_DIR = "provenance"
_PRIV = {"W", "FBO", "SPBO", "XWC"}
_SPECIAL = (
    SpecialTeamsColumn.KICKOFF,
    SpecialTeamsColumn.KICKOFF_RETURN,
    SpecialTeamsColumn.PUNT,
    SpecialTeamsColumn.PUNT_RETURN,
    SpecialTeamsColumn.INTERCEPTION_RETURN,
    SpecialTeamsColumn.FIELD_GOAL,
)
_HEADERS = {
    "offense.csv": [
        "#",
        "Line Plunge",
        "Counter",
        "End Reverse",
        "Draw",
        "Option",
        "Screen",
        "Sprint Out",
        "Boot-leg",
        "Drop Back",
        "B",
        "QT",
        "Fumble",
        "QR",
    ],
    "defense.csv": [
        "#",
        "Formation",
        "Sub",
        "Line Plunge",
        "Counter",
        "End Reverse",
        "Draw",
        "Option",
        "Screen",
        "Sprint Out",
        "Boot-leg",
        "Drop Back",
    ],
    "special.csv": [
        "#",
        "Kickoff",
        "Kickoff Return",
        "Punt",
        "Punt Return",
        "Int. Return",
        "Field Goal",
        "Extra Point",
    ],
    "provenance.csv": [
        "section",
        "column",
        "defense",
        "roll",
        "page",
        "left",
        "bottom",
        "right",
        "top",
        "original_text",
        "red",
        "green",
        "blue",
    ],
}


class TeamFormatError(ValueError):
    pass


@dataclass(frozen=True)
class TeamFileMetadata:
    power_rating: float
    privileges: tuple[str, ...]
    defense_label: str
    source_sha256: str
    evidence: tuple[tuple[str, Provenance], ...]

    def __post_init__(self) -> None:
        if (
            type(self.power_rating) not in (int, float)
            or not isfinite(self.power_rating)
            or self.power_rating <= 0
        ):
            raise TypeError("invalid rating")
        if (
            type(self.privileges) is not tuple
            or len(set(self.privileges)) != len(self.privileges)
            or any(type(x) is not str or x not in _PRIV for x in self.privileges)
        ):
            raise ValueError("invalid privileges")
        if not isinstance(self.defense_label, str) or not _sha(self.source_sha256):
            raise ValueError("invalid metadata")
        if type(self.evidence) is not tuple or any(
            type(x) is not tuple
            or len(x) != 2
            or type(x[0]) is not str
            or not isinstance(x[1], Provenance)
            for x in self.evidence
        ):
            raise TypeError("invalid evidence")


def _sha(x: object) -> bool:
    return isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x)


def validate_team_name(name: str) -> str:
    bad = (
        not isinstance(name, str)
        or not name
        or len(name) > 100
        or name != name.strip()
        or name.startswith(".")
        or name.endswith(".")
        or ".." in name
        or name.casefold() == "provenance"
    )
    allowed = set(". &'()-")
    if bad or any(not (c.isalnum() or c in allowed) for c in name):
        raise TeamFormatError("team name: unsafe folder name")
    return name


def team_folder_name(name: str) -> str:
    """Return the lowercase, hyphenated, ASCII folder name for a team (``Miami (Florida)`` ->
    ``miami-florida``). The real name stays in ``team.yaml``; callers must reject collisions."""
    if not isinstance(name, str):
        raise TeamFormatError("team name: unsafe folder name")
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")
    if not slug or len(slug) > 100 or slug == PROVENANCE_DIR:
        raise TeamFormatError("team name: unsafe folder name")
    return slug


def _dist(c: NormalizedCell) -> str:
    if c.yards is not None:
        return str(c.yards)
    if c.variable is None or c.variable_multiplier not in (-1, 1):
        raise TeamFormatError("cell: unrepresentable variable")
    return ("-" if c.variable_multiplier < 0 else "") + c.variable.value


def format_cell(c: NormalizedCell) -> str:
    names = {
        ResultKind.BREAKAWAY: "B",
        ResultKind.QUARTERBACK_RUN: "QR",
        ResultKind.QUARTERBACK_TRAPPED: "QT",
        ResultKind.SPRINT_OUT_PASS: "SOP",
        ResultKind.BOOTLEG_PASS: "BLP",
        ResultKind.FIELD_GOAL_REFERENCE: "FG",
        ResultKind.KICKOFF_REFERENCE: "KO",
        ResultKind.NO_GOOD_FIELD_GOAL: "NG",
    }
    if c.kind is ResultKind.NO_CHANGE:
        t = ""
    elif c.kind is ResultKind.INCOMPLETE:
        return "BLACK"
    elif c.kind is ResultKind.YARDS or c.kind.name.startswith("VARIABLE_"):
        t = _dist(c)
    elif c.kind is ResultKind.TOUCHDOWN:
        t = "TD"
    elif c.kind in names:
        t = names[c.kind]
    elif c.kind in {ResultKind.FUMBLE, ResultKind.INTERCEPTION, ResultKind.BLOCKED_KICK}:
        n = {ResultKind.FUMBLE: "F", ResultKind.INTERCEPTION: "INT", ResultKind.BLOCKED_KICK: "BK"}[
            c.kind
        ]
        if c.kind is ResultKind.FUMBLE and c.yards == 0:
            return "F"
        v = _dist(c)
        return (
            f"{n} {'-' if v.startswith('-') else '+'} {v.lstrip('-')}" if n == "F" else f"{n} {v}"
        )
    elif c.kind is ResultKind.PENALTY:
        p = c.penalty
        if p is None:
            raise TeamFormatError("cell: invalid penalty")
        pre = (
            "PI"
            if p.code is PenaltyCode.PI
            else ("OFF" if p.team is PenaltyTeam.OFFENSE else "DEF")
        )
        if p.code in {PenaltyCode.FIXED, PenaltyCode.PI}:
            v = (
                str(p.yards)
                if p.yards is not None
                else ("-" if p.variable_multiplier < 0 else "") + p.variable.value
            )
        else:
            v = p.code.value
        return f"{pre} {v}"
    else:
        raise TeamFormatError("cell: unsupported")
    decor = (
        c.kind is ResultKind.YARDS
        or c.kind.name.startswith("VARIABLE_")
        or c.kind is ResultKind.TOUCHDOWN
    )
    if c.priority is Priority.PARENTHESIZED and decor:
        t = f"({t})"
    elif c.priority is Priority.BRACKETED and decor:
        t = f"[{t}]"
    elif c.priority is not Priority.NORMAL:
        raise TeamFormatError("cell: priority")
    return t + ("*" if c.out_of_bounds else "")


def parse_cell(text: str, p: Provenance) -> NormalizedCell:
    bare = text.translate(str.maketrans("", "", "*()[]"))
    if text == "BLACK":
        color, source = ChartColor.BLACK, ""
    elif text in {"", "*"}:
        color, source = ChartColor.WHITE, text
    elif text.startswith(("F", "INT", "BK")):
        color, source = ChartColor.RED, text
    elif text.startswith(("OFF ", "DEF ", "PI ")):
        color, source = ChartColor.YELLOW, text
    elif bare in {"TD", "B", "KO", "DS", "X", "T1", "T2", "T3"}:
        color, source = ChartColor.GREEN, text
    elif bare in {"QR", "SOP", "BLP"}:
        color, source = ChartColor.WHITE, text
    elif bare in {"QT", "FG", "NG"} or bare.startswith("-"):
        color, source = ChartColor.RED, text
    else:
        color, source = ChartColor.GREEN, text
    try:
        r = replace(normalize_cell(replace(p, original_text=source), color), provenance=p)
    except (NormalizationError, ValueError, TypeError) as e:
        raise TeamFormatError("cell: invalid grammar") from e
    if format_cell(r) != text:
        raise TeamFormatError("cell: noncanonical grammar")
    return r


def _csv(rows: list[list[object]]) -> str:
    s = io.StringIO(newline="")
    csv.writer(s, lineterminator="\n").writerows(rows)
    return s.getvalue()


def _facts(chart: TeamChart, meta: TeamFileMetadata) -> tuple[list[Provenance], str]:
    ps = (
        [x.cell.provenance for x in chart.offense]
        + [x.cell.provenance for x in chart.supplemental]
        + [x.cell.provenance for x in chart.defense]
        + [x.cell.provenance for x in chart.special_teams]
        + [x.provenance for x in chart.pat_outcomes]
        + [x[1] for x in meta.evidence]
    )
    if any(x.source_sha256 != meta.source_sha256 for x in ps):
        raise TeamFormatError("provenance: hash mismatch")
    if any(x.filename != ps[0].filename for x in ps):
        raise TeamFormatError("provenance: filename mismatch")
    return ps, ps[0].filename


def team_to_files(chart: TeamChart, meta: TeamFileMetadata) -> dict[str, str]:
    validate_team_name(chart.name)
    _, fn = _facts(chart, meta)
    o = {(x.roll, x.play): x.cell for x in chart.offense}
    u = {(x.roll, x.column): x.cell for x in chart.supplemental}
    d = {(x.defense, x.roll, x.play): x.cell for x in chart.defense}
    s = {(x.roll, x.column): x.cell for x in chart.special_teams}
    pat = {x.roll: x for x in chart.pat_outcomes}
    offense = [_HEADERS["offense.csv"]] + [
        [
            r,
            *[format_cell(o[r, p]) for p in Play],
            format_cell(u[r, SupplementalColumn.BREAKAWAY]),
            format_cell(u[r, SupplementalColumn.QUARTERBACK_TRAPPED]),
            "R" if r in chart.recovery_range else "L",
            format_cell(u[r, SupplementalColumn.QUARTERBACK_RUN]),
        ]
        for r in range(10, 40)
    ]
    defense = [_HEADERS["defense.csv"]] + [
        [f"{x.value}-{r}", x.value, r, *[format_cell(d[x, r, p]) for p in Play]]
        for x in Defense
        for r in range(1, 6)
    ]
    special = [_HEADERS["special.csv"]] + [
        [r, *[format_cell(s[r, c]) for c in _SPECIAL], "" if pat[r].good else "NG"]
        for r in range(10, 40)
    ]
    data = {
        "team_name": chart.name,
        "nickname": meta.defense_label,
        "season": chart.season,
        "power_rating": float(meta.power_rating),
        "privileges": list(meta.privileges),
        "source_sha256": meta.source_sha256,
        "source_filename": fn,
        "team_file_version": 1,
        "status": "validated",
    }
    y = (
        f"# Team metadata for the {chart.season} {chart.name} (generated by bowl-bound-import)\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    )
    return {
        "offense.csv": _csv(offense),
        "defense.csv": _csv(defense),
        "special.csv": _csv(special),
        "team.yaml": y,
    }


def provenance_to_csv(chart: TeamChart, meta: TeamFileMetadata) -> str:
    validate_team_name(chart.name)
    _, _ = _facts(chart, meta)
    o = {(x.roll, x.play): x.cell for x in chart.offense}
    u = {(x.roll, x.column): x.cell for x in chart.supplemental}
    d = {(x.defense, x.roll, x.play): x.cell for x in chart.defense}
    s = {(x.roll, x.column): x.cell for x in chart.special_teams}
    pat = {x.roll: x for x in chart.pat_outcomes}
    rows = [_HEADERS["provenance.csv"]]

    def add(a: str, b: str, c: str, r: int | str, p: Provenance) -> None:
        rows.append(
            [
                a,
                b,
                c,
                r,
                p.page,
                repr(p.bounding_box.left),
                repr(p.bounding_box.bottom),
                repr(p.bounding_box.right),
                repr(p.bounding_box.top),
                p.original_text,
                *p.rgb_color,
            ]
        )

    for r in range(10, 40):
        for p in Play:
            add("offense", str(p.value), "", r, o[r, p].provenance)
        for c in SupplementalColumn:
            add("supplemental", c.value, "", r, u[r, c].provenance)
        for c in _SPECIAL:
            add("special_teams", c.value, "", r, s[r, c].provenance)
        add("pat", "pat", "", r, pat[r].provenance)
    for x in Defense:
        for r in range(1, 6):
            for p in Play:
                add("defense", str(p.value), x.value, r, d[x, r, p].provenance)
    for label, p in meta.evidence:
        add("metadata", label, "", "", p)
    return _csv(rows)


def _err(file: str, row: int, reason: str) -> TeamFormatError:
    return TeamFormatError(f"{file} row {row}: {reason}")


def _rows(text: object, file: str) -> list[list[str]]:
    if type(text) is not str or text.startswith("\ufeff") or "\x00" in text or "\r" in text:
        raise _err(file, 0, "invalid text")
    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as e:
        raise _err(file, 0, "invalid CSV") from e
    if not rows or rows[0] != _HEADERS[file]:
        raise _err(file, 1, "unexpected header")
    return rows[1:]


def _num(x: str, file: str, row: int, pos: bool = False) -> int:
    if not x.isascii() or not x.isdecimal() or (len(x) > 1 and x[0] == "0"):
        raise _err(file, row, "invalid integer")
    n = int(x)
    if pos and n < 1:
        raise _err(file, row, "integer out of range")
    return n


def _strict_tree(text: str) -> bool:
    """True only for YAML without anchors, aliases, explicit tags, merge keys, or duplicate keys.

    PyYAML resolves anchors while composing and keeps no record of them, so the raw event
    stream is scanned for anchors, aliases, and tags. The composed tree then checks keys:
    a duplicate key would otherwise silently keep its last value.
    """
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if getattr(event, "anchor", None) is not None or getattr(event, "tag", None) is not None:
            return False
        if type(event).__name__ == "AliasEvent":
            return False
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    return root is not None and _walk_unique(root)


def _walk_unique(node: yaml.Node) -> bool:
    if isinstance(node, yaml.ScalarNode):
        return node.tag != "tag:yaml.org,2002:merge"
    if isinstance(node, yaml.SequenceNode):
        return all(_walk_unique(item) for item in node.value)
    if not isinstance(node, yaml.MappingNode):
        return False
    keys: list[str] = []
    for key_node, value_node in node.value:
        if not isinstance(key_node, yaml.ScalarNode):
            return False
        if key_node.tag == "tag:yaml.org,2002:merge" or key_node.value in keys:
            return False
        keys.append(key_node.value)
        if not _walk_unique(value_node):
            return False
    return True


def _yaml(text: str) -> dict[str, object]:
    if "\x00" in text or text.startswith("\ufeff"):
        raise _err("team.yaml", 0, "invalid YAML")
    try:
        if not _strict_tree(text):
            raise ValueError
        data = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as e:
        raise _err("team.yaml", 0, "invalid YAML") from e
    keys = [
        "team_name",
        "nickname",
        "season",
        "power_rating",
        "privileges",
        "source_sha256",
        "source_filename",
        "team_file_version",
        "status",
    ]
    if type(data) is not dict or list(data) != keys:
        raise _err("team.yaml", 0, "invalid metadata")
    return data


def team_from_files(
    files: Mapping[str, str], provenance_csv: str
) -> tuple[TeamChart, TeamFileMetadata]:
    if set(files) != set(TEAM_FILES):
        raise TeamFormatError("files row 0: required file set")
    o, d, s = (_rows(files[x], x) for x in ("offense.csv", "defense.csv", "special.csv"))
    y = _yaml(files["team.yaml"])
    if (
        len(o) != 30
        or any(len(x) != 14 for x in o)
        or len(d) != 30
        or any(len(x) != 12 for x in d)
        or len(s) != 30
        or any(len(x) != 8 for x in s)
    ):
        raise _err("files", 0, "incorrect row shape")
    if (
        type(y["team_name"]) is not str
        or type(y["nickname"]) is not str
        or type(y["season"]) is not int
        or y["season"] < 1
        or type(y["power_rating"]) not in (int, float)
        or (type(y["power_rating"]) is float and not isfinite(y["power_rating"]))
        or len(str(y["power_rating"])) > 12
        or y["power_rating"] <= 0
        or type(y["privileges"]) is not list
        or any(type(x) is not str for x in y["privileges"])
        or not _sha(y["source_sha256"])
        or type(y["source_filename"]) is not str
        or not y["source_filename"]
        or type(y["team_file_version"]) is not int
        or y["team_file_version"] != 1
        or y["status"] != "validated"
    ):
        raise _err("team.yaml", 0, "invalid metadata")
    try:
        meta = TeamFileMetadata(
            float(y["power_rating"]), tuple(y["privileges"]), y["nickname"], y["source_sha256"], ()
        )
    except (TypeError, ValueError) as e:
        raise _err("team.yaml", 0, "invalid metadata") from e
    pr = _rows(provenance_csv, "provenance.csv")
    expected = set()
    prov = {}
    ev = []
    for r in range(10, 40):
        expected |= (
            {("offense", str(p.value), "", r) for p in Play}
            | {("supplemental", c.value, "", r) for c in SupplementalColumn}
            | {("special_teams", c.value, "", r) for c in _SPECIAL}
            | {("pat", "pat", "", r)}
        )
    expected |= {
        ("defense", str(p.value), x.value, r) for x in Defense for r in range(1, 6) for p in Play
    }
    for n, row in enumerate(pr, 2):
        if len(row) != 13:
            raise _err("provenance.csv", n, "incorrect columns")
        a, b, c, r, page, l, bo, ri, t, orig, re, gr, bl = row
        key = (a, b, c, "" if not r else _num(r, "provenance.csv", n))
        if a == "metadata":
            if c or r:
                raise _err("provenance.csv", n, "invalid metadata key")
        elif key not in expected or key in prov:
            raise _err("provenance.csv", n, "unexpected provenance key")
        try:
            p = Provenance(
                y["source_sha256"],
                y["source_filename"],
                _num(page, "provenance.csv", n, True),
                BoundingBox(*(float(z) for z in (l, bo, ri, t))),
                orig,
                tuple(_num(z, "provenance.csv", n) for z in (re, gr, bl)),
            )
        except (TypeError, ValueError) as e:
            raise _err("provenance.csv", n, "invalid provenance") from e
        if a == "metadata":
            ev.append((b, p))
        else:
            prov[key] = p
    if set(prov) != expected:
        raise _err("provenance.csv", 0, "missing provenance")
    meta = replace(meta, evidence=tuple(ev))
    off = []
    sup = []
    rec = []
    for n, row in enumerate(o, 2):
        r = _num(row[0], "offense.csv", n)
        if r != n + 8 or row[12] not in {"R", "L"}:
            raise _err("offense.csv", n, "invalid recovery")
        if row[12] == "R":
            rec.append(r)
        for p, z in zip(Play, row[1:10]):
            off.append(OffensiveCell(p, r, parse_cell(z, prov["offense", str(p.value), "", r])))
        for c, z in zip(
            (
                SupplementalColumn.BREAKAWAY,
                SupplementalColumn.QUARTERBACK_TRAPPED,
                SupplementalColumn.QUARTERBACK_RUN,
            ),
            (row[10], row[11], row[13]),
        ):
            sup.append(SupplementalCell(c, r, parse_cell(z, prov["supplemental", c.value, "", r])))
    if not rec or rec != list(range(10, max(rec) + 1)) or not 10 <= max(rec) < 39:
        raise _err("offense.csv", 0, "invalid recovery range")
    de = []
    for n, row in enumerate(d, 2):
        x = list(Defense)[(n - 2) // 5]
        r = (n - 2) % 5 + 1
        if row[:3] != [f"{x.value}-{r}", x.value, str(r)]:
            raise _err("defense.csv", n, "invalid defense row")
        for p, z in zip(Play, row[3:]):
            de.append(
                DefensiveCell(x, p, r, parse_cell(z, prov["defense", str(p.value), x.value, r]))
            )
    sp = []
    pa = []
    for n, row in enumerate(s, 2):
        r = _num(row[0], "special.csv", n)
        if r != n + 8 or row[-1] not in {"", "NG"}:
            raise _err("special.csv", n, "invalid special row")
        for c, z in zip(_SPECIAL, row[1:7]):
            sp.append(SpecialTeamsCell(c, r, parse_cell(z, prov["special_teams", c.value, "", r])))
        pa.append(PatOutcome(r, row[-1] == "", prov["pat", "pat", "", r]))
    try:
        return TeamChart(
            1,
            y["team_name"],
            y["season"],
            tuple(sorted(off, key=lambda x: (x.play.value, x.roll))),
            tuple(sorted(sup, key=lambda x: (x.column.value, x.roll))),
            tuple(sorted(de, key=lambda x: (x.defense.value, x.play.value, x.roll))),
            tuple(sorted(sp, key=lambda x: (list(SpecialTeamsColumn).index(x.column), x.roll))),
            tuple(pa),
            range(10, max(rec) + 1),
        ), meta
    except (TypeError, ValueError) as e:
        raise _err("team.yaml", 0, "invalid chart") from e


def load_team(season_dir: Path, folder_name: str) -> tuple[TeamChart, TeamFileMetadata]:
    """Load ``<season>/<folder_name>/`` plus ``<season>/provenance/<folder_name>.csv``.

    ``folder_name`` is the slug from :func:`team_folder_name`; the real team name is read
    from ``team.yaml`` and must slug back to the folder it was found in.
    """
    if not isinstance(folder_name, str) or team_folder_name(folder_name) != folder_name:
        raise TeamFormatError("team folder: not a canonical folder name")
    name = season_dir.name
    if not (name.isascii() and name.isdecimal()) or str(int(name)) != name or int(name) < 1:
        raise TeamFormatError("season directory: invalid name")
    season = int(name)
    if season_dir.is_symlink():
        raise TeamFormatError("season directory: symlinked")
    folder = season_dir / folder_name
    paths = [folder / x for x in TEAM_FILES] + [season_dir / PROVENANCE_DIR / f"{folder_name}.csv"]
    if any(p.is_symlink() or not p.is_file() or p.parent.is_symlink() for p in paths):
        raise TeamFormatError("team files row 0: missing or symlinked file")
    try:
        texts = []
        for p in paths:
            with p.open(encoding="utf-8", newline="") as handle:
                texts.append(handle.read())
        result = team_from_files(dict(zip(TEAM_FILES, texts[:-1], strict=True)), texts[-1])
    except (OSError, UnicodeError) as e:
        raise TeamFormatError("team files row 0: unreadable") from e
    if result[0].season != season or team_folder_name(result[0].name) != folder_name:
        raise TeamFormatError("team metadata row 0: folder mismatch")
    return result
