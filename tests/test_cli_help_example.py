"""CLI-042: the displayed copy/paste example is accepted by the real parser."""

import shlex
from pathlib import Path

import pytest

from bowl_bound.cli import TerminalGame, main
from bowl_bound.sample_teams import install_samples


def test_displayed_help_example_starts_medium_solitaire(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["--help"])
    assert stopped.value.code == 0
    command = shlex.split(capsys.readouterr().out.split("Example: ", 1)[1])
    assert command[:3] == ["python", "-m", "bowl_bound"]
    install_samples(tmp_path)
    seen = []

    def run(self: TerminalGame) -> int:
        seen.append(self.game.coach_policy)
        return 0

    monkeypatch.setattr(TerminalGame, "run", run)
    assert main([*command[3:], "--seasons", str(tmp_path)]) == 0
    assert seen == ["medium-v1"]
