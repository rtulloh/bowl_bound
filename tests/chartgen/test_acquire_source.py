"""The public source command uses synthetic HTTP responses in CI."""

import json
from pathlib import Path

from scripts.acquire_chart_source import acquire_source
from tests.chartgen.test_espn_core import play
from tools.chartgen.source import read_normalized


def test_acquisition_retains_raw_bytes_and_normalized_evidence(tmp_path: Path) -> None:
    def fetch(url: str) -> bytes:
        if "scoreboard" in url:
            value = {
                "events": [
                    {
                        "id": "123",
                        "season": {"year": 2002},
                        "competitions": [
                            {
                                "competitors": [
                                    {"team": {"id": "1", "location": "Cedar Valley"}},
                                    {"team": {"id": "2", "location": "Harbor Tech"}},
                                ]
                            }
                        ],
                    }
                ]
            }
        elif "/plays?" in url:
            row = play("Rush")
            row["id"] = "123001"
            row["teamParticipants"] = [{"id": "1"}, {"id": "2"}]
            value = {"count": 1, "pageCount": 1, "items": [row]}
        else:
            value = {
                "count": 1,
                "pageCount": 1,
                "items": [{"$ref": "https://example.test/events/123?lang=en"}],
            }
        return json.dumps(value).encode()

    output = tmp_path / "private-data" / "snapshot"
    report = acquire_source(2002, output, fetch=fetch, workers=1)
    assert report["status"] == "complete"
    assert report["games_with_plays"] == 1
    events, source = read_normalized(output / "normalized.json")
    assert len(events) == 1 and events[0].yards == 9
    assert source["game_source_sha256"]["123"]
    assert (output / "raw/plays-123.json").is_file()
    assert json.loads((output / "teams.json").read_text()) == {
        "1": "Cedar Valley",
        "2": "Harbor Tech",
    }
