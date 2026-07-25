"""M0 — ``cds init`` scaffolds a data root in the user's repo (not the CDS install)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cds.core.cli import app
from cds.core.init import init_project
from cds.core.workspace import find_data_root, load_project


def test_init_scaffolds_marker_dirs_and_assets(tmp_path: Path) -> None:
    result = init_project(tmp_path, name="demo")

    marker = tmp_path / "cds.toml"
    assert marker.is_file()
    assert tomllib.loads(marker.read_text())["project"]["name"] == "demo"
    assert (tmp_path / "concept-definition" / "instances" / ".gitkeep").is_file()
    assert (tmp_path / "concept-definition" / "briefs" / ".gitkeep").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / ".claude" / "settings.json").is_file()
    assert "cds.toml" in result.created


def test_init_defaults_project_name_to_dir(tmp_path: Path) -> None:
    proj = tmp_path / "my-analysis"
    init_project(proj)
    assert tomllib.loads((proj / "cds.toml").read_text())["project"]["name"] == "my-analysis"


def test_init_is_idempotent_without_force(tmp_path: Path) -> None:
    init_project(tmp_path)
    second = init_project(tmp_path)
    assert second.created == []
    assert "cds.toml" in second.skipped


def test_init_force_overwrites(tmp_path: Path) -> None:
    init_project(tmp_path)
    (tmp_path / "cds.toml").write_text("garbage", encoding="utf-8")
    init_project(tmp_path, name="demo", force=True)
    assert tomllib.loads((tmp_path / "cds.toml").read_text())["project"]["name"] == "demo"


def test_init_then_project_is_discoverable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CDS_PROJECT", raising=False)
    init_project(tmp_path, name="demo")
    nested = tmp_path / "concept-definition" / "instances"
    assert find_data_root(start=nested) == tmp_path.resolve()
    project = load_project(start=nested)
    assert project.instances_dir == tmp_path.resolve() / "concept-definition" / "instances"


def test_cds_init_cli(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["init", str(tmp_path), "--name", "cli-demo"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "cds.toml").is_file()
    assert "cds project ready" in result.output
