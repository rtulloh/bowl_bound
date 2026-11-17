"""Source parsing and receipts consume one captured fictional byte sequence."""

import csv
import hashlib
import io
import sys
from pathlib import Path
from types import FrameType, SimpleNamespace
from typing import Any

import pytest

from tools.chartgen import source


def payload(yards: int) -> bytes:
    stream = io.StringIO()
    row = {
        "season": 2026,
        "game_id": "snapshot-fictional",
        "id": "rush",
        "pos_team_id": "a",
        "def_pos_team_id": "b",
        "type.text": "Rush",
        "text": "Runner rush.",
        "yds_rushed": yards,
    }
    writer = csv.DictWriter(stream, fieldnames=list(row), lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return stream.getvalue().encode()


@pytest.mark.parametrize("boundary", ["classify", "metadata"])
def test_permanent_source_change_at_real_processing_boundary_is_refused(
    tmp_path: Path, boundary: str
) -> None:
    path = tmp_path / "fictional.csv"
    path.write_bytes(payload(4))
    changed = False
    code = (
        source.classify_espn.__code__
        if boundary == "classify"
        else source._optional_observations_sha256.__code__
    )
    previous = sys.getprofile()

    def mutate(frame: FrameType, event: str, argument: object) -> None:
        nonlocal changed
        if (
            not changed
            and frame.f_code is code
            and event == ("call" if boundary == "classify" else "return")
        ):
            path.write_bytes(payload(9))
            changed = True

    sys.setprofile(mutate)
    try:
        with pytest.raises(ValueError, match="source.*changed"):
            source.import_espn(path, url="https://example.invalid/fictional")
    finally:
        sys.setprofile(previous)
    assert changed


def test_transient_source_substitution_cannot_mix_parsed_and_hashed_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "fictional.csv"
    original = payload(4)
    path.write_bytes(original)
    reader_type = csv.DictReader

    class TransientReader:
        def __init__(self, stream: Any, *args: Any, **kwargs: Any) -> None:
            path.write_bytes(payload(9))
            self.reader = reader_type(stream, *args, **kwargs)

        @property
        def fieldnames(self) -> list[str] | None:
            return self.reader.fieldnames

        def __iter__(self) -> Any:
            try:
                yield from self.reader
            finally:
                path.write_bytes(original)

    monkeypatch.setattr(source.csv, "DictReader", TransientReader)
    events, receipt = source.import_espn(path, url="https://example.invalid/fictional")
    assert path.read_bytes() == original
    assert [event.yards for event in events] == [4]
    assert receipt["raw_sha256"] == hashlib.sha256(original).hexdigest()


@pytest.mark.parametrize("window", ["entry", "final"])
def test_change_in_source_byte_read_window_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, window: str
) -> None:
    path = tmp_path / "fictional.csv"
    path.write_bytes(payload(4))
    read_bytes = Path.read_bytes
    changed = False
    reads = 0

    def mutate(item: Path) -> bytes:
        nonlocal changed, reads
        value = read_bytes(item)
        if item == path:
            reads += 1
        if item == path and not changed and reads == (1 if window == "entry" else 2):
            changed = True
            path.write_bytes(payload(9))
        return value

    monkeypatch.setattr(Path, "read_bytes", mutate)
    with pytest.raises(ValueError, match="source.*changed"):
        source.import_espn(path, url="https://example.invalid/fictional")
    assert changed


@pytest.mark.parametrize("fail", [False, True])
def test_parquet_transport_consumes_private_captured_bytes_and_always_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    # This deliberately tests transport, not the optional real Parquet codec.
    path = tmp_path / "fictional.parquet"
    original = payload(4)
    path.write_bytes(original)
    consumed: list[Path] = []
    permissions: list[int] = []

    class Relation:
        def __init__(self, content: bytes) -> None:
            reader = csv.DictReader(io.StringIO(content.decode()))
            self.columns = list(reader.fieldnames or ())
            self.rows = [tuple(row[name] for name in self.columns) for row in reader]

        def create_view(self, name: str) -> None:
            assert name == "raw_events"

    class Connection:
        closed = False
        relation: Relation

        def read_parquet(self, name: str) -> Relation:
            selected = Path(name)
            consumed.append(selected)
            permissions.append(selected.stat().st_mode & 0o777)
            path.write_bytes(payload(9))
            self.relation = Relation(selected.read_bytes())
            return self.relation

        def sql(self, query: str) -> SimpleNamespace:
            if fail:
                raise RuntimeError("fictional parquet consumer failure")
            # The production projection can differ from the synthetic file order.
            projection = query.split("SELECT ", 1)[1].split(" FROM", 1)[0]
            names = [name.strip('"') for name in projection.split(",")]
            rows = [
                tuple(dict(zip(self.relation.columns, row, strict=True))[name] for name in names)
                for row in self.relation.rows
            ]
            path.write_bytes(original)
            return SimpleNamespace(fetchall=lambda: rows)

        def close(self) -> None:
            self.closed = True

    connection = Connection()
    monkeypatch.setitem(sys.modules, "duckdb", SimpleNamespace(connect=lambda: connection))
    if fail:
        with pytest.raises(RuntimeError, match="fictional parquet"):
            source.import_espn(path, url="https://example.invalid/fictional")
    else:
        events, receipt = source.import_espn(path, url="https://example.invalid/fictional")
        assert [event.yards for event in events] == [4]
        assert receipt["raw_sha256"] == hashlib.sha256(original).hexdigest()
    assert consumed and consumed[0] != path
    assert permissions == [0o600]
    assert not consumed[0].exists()
    assert connection.closed
