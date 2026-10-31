"""Read-only validation of the supported digitally generated chart PDF layout."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from .page_view import rotate_portrait_page


class ImportInspectionError(Exception):
    """Base error for a source PDF that cannot be read safely for import."""


class SafeImportInspectionError(ImportInspectionError):
    """A project-authored inspection message safe to show to the user."""


class UnsupportedDocumentError(SafeImportInspectionError):
    """Raised when a readable PDF is not the supported chart layout."""


@dataclass(frozen=True)
class PageInfo:
    """The verified role and identity recorded for one source page."""

    page: int
    role: Literal["offense", "defense_special"]
    team_name: str
    season: int
    rotation: int = 0


@dataclass(frozen=True)
class DocumentInspection:
    """Read-only result used by later PDF import stages."""

    source_sha256: str
    pages: tuple[PageInfo, ...]


_OFFENSE_LABELS = ("Line Plunge", "Option", "QT", "QR", "B")
_DEFENSE_LABELS = ("Defense", "Kickoff", "Punt", "Field Goal")
_HEADER_PATTERN = re.compile(
    r"^\s*(?P<season>(?:19|20)\d{2})\s+(?P<team>[A-Za-z][A-Za-z .&'()\-]{1,60}?)\s+"
    r"(?P<role>offense|defense)\s*$",
    re.IGNORECASE,
)
_MIN_CHART_RECTANGLES = 20
_ROLE_WORDS = {"offense": "offense", "defense_special": "defense"}


def inspect_document(path: Path) -> DocumentInspection:
    """Inspect supported paired chart pages without modifying the source.

    The supported profile uses portrait offense pages and landscape defense/special
    pages, with a rotated left-edge ``year team role`` header. Defense headers may
    name a mascot rather than the offense page's school, so only the season is
    verifiable for a pair at this stage.
    """
    try:
        source = path.read_bytes()
    except FileNotFoundError as error:
        raise SafeImportInspectionError("PDF source does not exist") from error
    except OSError as error:
        raise SafeImportInspectionError("PDF source cannot be read") from error

    try:
        import pdfplumber
        from pdfminer.pdfdocument import PDFPasswordIncorrect
        from pdfminer.pdfparser import PDFSyntaxError
        from pdfminer.psparser import PSEOF
        from pdfplumber.utils.exceptions import PdfminerException
    except ImportError as error:
        raise SafeImportInspectionError(
            "PDF inspection requires the optional PDF tools; install them with "
            '`python -m pip install -e ".[pdf]"` from the project folder'
        ) from error

    try:
        with pdfplumber.open(BytesIO(source)) as document:
            if getattr(document.doc, "encryption", None):
                raise SafeImportInspectionError("PDF source is encrypted and cannot be inspected")
            if not document.pages or len(document.pages) % 2:
                raise UnsupportedDocumentError(
                    "Supported chart documents must contain complete offense/defense page pairs"
                )
            inspected: list[PageInfo] = []
            for index, page in enumerate(document.pages):
                page_number = index + 1
                role = "offense" if index % 2 == 0 else "defense_special"
                if role == "defense_special" and _is_rotated_portrait(page):
                    view = rotate_portrait_page(page)
                    _inspect_rotated_defense(view, page_number)
                    inspected.append(PageInfo(page_number, role, "", 0, 90))
                else:
                    inspected.append(_inspect_page(page, page_number, role))
            pages = _validate_pairs(tuple(inspected))
    except PDFPasswordIncorrect as error:
        raise SafeImportInspectionError(
            "PDF source is encrypted and cannot be inspected"
        ) from error
    except PdfminerException as error:
        if error.args and isinstance(error.args[0], PDFPasswordIncorrect):
            raise SafeImportInspectionError(
                "PDF source is encrypted and cannot be inspected"
            ) from error
        raise SafeImportInspectionError(
            "PDF source is malformed or cannot be parsed by pdfplumber"
        ) from error
    except ImportInspectionError:
        raise
    except (
        PDFSyntaxError,
        PSEOF,
        OSError,
        TypeError,
        ValueError,
        AttributeError,
    ) as error:
        raise SafeImportInspectionError(
            "PDF source is malformed or cannot be parsed by pdfplumber"
        ) from error
    except Exception as error:  # noqa: BLE001 - keep document text out of messages
        raise SafeImportInspectionError(
            "PDF source could not be inspected; the layout may be unsupported"
        ) from error

    return DocumentInspection(hashlib.sha256(source).hexdigest(), pages)


def _inspect_page(
    page: object, page_number: int, role: Literal["offense", "defense_special"]
) -> PageInfo:
    _validate_geometry(page, page_number, role)
    season, team_name = _extract_rotated_header(page, page_number, role)
    if len(page.rects) < _MIN_CHART_RECTANGLES:
        raise UnsupportedDocumentError(
            f"Page {page_number} has too few vector chart rectangles to be a chart"
        )
    words = _body_words(page)
    labels = _OFFENSE_LABELS if role == "offense" else _DEFENSE_LABELS
    if not all(_has_label(words, label) for label in labels):
        raise UnsupportedDocumentError(f"Page {page_number} is missing required labels for {role}")
    return PageInfo(page_number, role, team_name, season)


def _body_words(page: object) -> list[dict]:
    """Upright words only: the rotated left-edge header must not satisfy chart labels."""
    if hasattr(page, "filter"):
        upright = page.filter(
            lambda obj: obj.get("object_type") != "char" or obj.get("upright", True)
        )
        return upright.extract_words()
    return page.extract_words()


def _is_rotated_portrait(page: object) -> bool:
    """Recognize only portrait pages whose vector text is predominantly quarter-turned."""
    width, height = page.width, page.height
    if not (height > width and 0.70 <= width / height <= 0.85):
        return False
    chars = tuple(getattr(page, "chars", ()))
    if len(chars) < 20:
        return False
    rotated = sum(not char.get("upright", True) for char in chars)
    return rotated / len(chars) >= 0.90


def _inspect_rotated_defense(page: object, page_number: int) -> None:
    """Validate the explicit portrait-sheet/rotated-content defense profile."""
    _validate_geometry(page, page_number, "defense_special")
    if len(page.rects) < _MIN_CHART_RECTANGLES:
        raise UnsupportedDocumentError(
            f"Page {page_number} has too few vector chart rectangles to be a chart"
        )
    words = _body_words(page)
    if not all(_has_label(words, label) for label in _DEFENSE_LABELS):
        raise UnsupportedDocumentError(
            f"Page {page_number} is missing required labels for defense_special"
        )


def _validate_geometry(
    page: object, page_number: int, role: Literal["offense", "defense_special"]
) -> None:
    width, height = page.width, page.height
    portrait = height > width and 0.70 <= width / height <= 0.85
    landscape = width > height and 0.70 <= height / width <= 0.85
    if (role == "offense" and not portrait) or (role == "defense_special" and not landscape):
        raise UnsupportedDocumentError(
            f"Page {page_number} has unsupported {role} page geometry; "
            "expected letter-like orientation"
        )


def _near(previous: dict, following: dict) -> bool:
    """Words of one label sit on one line, or stacked directly in one column."""
    same_line = (
        abs(previous["top"] - following["top"]) < 3 and 0 <= following["x0"] - previous["x1"] <= 20
    )
    stacked = 0 <= following["top"] - previous["bottom"] <= 12 and (
        abs((previous["x0"] + previous["x1"]) / 2 - (following["x0"] + following["x1"]) / 2) <= 25
    )
    return same_line or stacked


def _has_label(words: list[dict], label: str) -> bool:
    """Find a label by position (same line or stacked), not as scattered words."""
    parts = [part.casefold() for part in label.split()]

    def extend(previous: dict | None, index: int) -> bool:
        if index == len(parts):
            return True
        return any(
            word["text"].casefold() == parts[index]
            and (previous is None or _near(previous, word))
            and extend(word, index + 1)
            for word in words
        )

    return extend(None, 0)


def _extract_rotated_header(
    page: object, page_number: int, role: Literal["offense", "defense_special"]
) -> tuple[int, str]:
    """Read only the rotated text in the left header strip and check its role word."""
    left_edge = page.width * 0.12
    chars = [char for char in page.chars if not char["upright"] and char["x0"] <= left_edge]
    ordered = sorted(chars, key=lambda char: (round(char["x0"]), -char["top"]))
    header = "".join(char["text"] for char in ordered)
    match = _HEADER_PATTERN.match(header)
    if not match or match["role"].lower() != _ROLE_WORDS[role]:
        raise UnsupportedDocumentError(
            f"Page {page_number} lacks a supported rotated left-edge year/team header "
            f"for its {role} role"
        )
    return int(match["season"]), " ".join(match["team"].split())


def _identity(name: str, season: int) -> tuple[str, int]:
    """School identity: case/spacing-insensitive. Mascots are never identifiers."""
    return " ".join(name.split()).casefold(), season


def _validate_pairs(pages: tuple[PageInfo, ...]) -> tuple[PageInfo, ...]:
    """Pair by page order and season; rotated Mays pages inherit paired team identity."""
    offense_identities: set[tuple[str, int]] = set()
    validated = list(pages)
    for offense, defense in zip(pages[::2], pages[1::2], strict=True):
        if defense.rotation == 90 and not defense.team_name:
            validated[defense.page - 1] = PageInfo(
                defense.page,
                defense.role,
                offense.team_name,
                offense.season,
                defense.rotation,
            )
        elif offense.season != defense.season:
            raise UnsupportedDocumentError(
                f"Pages {offense.page} and {defense.page} must identify the same season"
            )
        identity = _identity(offense.team_name, offense.season)
        if identity in offense_identities:
            raise UnsupportedDocumentError(
                f"Duplicate offense team and season header in pages {offense.page}-{defense.page}"
            )
        offense_identities.add(identity)
    return tuple(validated)
