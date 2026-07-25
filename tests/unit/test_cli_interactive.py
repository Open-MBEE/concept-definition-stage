"""M4 — the interactive CLI authoring flow works headless (no model)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cds.core.cli import app
from cds.core.init import init_project


def test_new_interactive_prompts_and_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_project(tmp_path, name="demo")
    monkeypatch.setenv("CDS_PROJECT", str(tmp_path))

    # answers: synthesis, label, description
    result = CliRunner().invoke(
        app, ["new", "goal", "reach", "--interactive"], input="cd\nReach\nConnect to a human.\n"
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "concept-definition" / "instances" / "goal.ttl").is_file()

    text = (tmp_path / "concept-definition" / "instances" / "goal.ttl").read_text()
    assert "Reach" in text
    assert "Connect to a human." in text


def test_new_without_synthesis_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    init_project(tmp_path, name="demo")
    monkeypatch.setenv("CDS_PROJECT", str(tmp_path))
    result = CliRunner().invoke(app, ["new", "goal", "g", "--label", "G", "--description", "d"])
    assert result.exit_code == 2
    assert "synthesis" in result.output
