"""M0 — the TOOL_ROOT (packaged canon) / DATA_ROOT (user project) split."""

from __future__ import annotations

from pathlib import Path

import pytest

from cds.core import workspace as ws


def test_packaged_canon_is_resolvable_and_present() -> None:
    # TOOL_ROOT: the canon ships inside the package and is found via the install location.
    assert ws.canon_dir().is_dir()
    assert ws.shapes_dir().is_dir()
    assert sorted(ws.shapes_dir().glob("*.ttl")), "no packaged SHACL shapes found"
    assert ws.core_ttl_path().is_file()
    assert ws.concept_definition_ttl_path().is_file()
    assert ws.waivers_path().is_file()


def test_find_data_root_returns_none_outside_a_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ws.DATA_ROOT_ENV, raising=False)
    assert ws.find_data_root(start=tmp_path) is None


def test_find_data_root_walks_up_to_the_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ws.DATA_ROOT_ENV, raising=False)
    (tmp_path / ws.DATA_MARKER).write_text("[project]\nname = 'x'\n", encoding="utf-8")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert ws.find_data_root(start=nested) == tmp_path.resolve()


def test_env_override_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ws.DATA_ROOT_ENV, str(tmp_path))
    assert ws.find_data_root(start=Path("/nowhere")) == tmp_path.resolve()


def test_data_root_raises_when_unresolvable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ws.DATA_ROOT_ENV, raising=False)
    with pytest.raises(ws.CdsProjectNotFound):
        ws.data_root(start=tmp_path)


def test_load_project_reads_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ws.DATA_ROOT_ENV, raising=False)
    (tmp_path / ws.DATA_MARKER).write_text(
        "[project]\nname='demo'\n[layout]\ninstances='foo/i'\nbriefs='foo/b'\n",
        encoding="utf-8",
    )
    project = ws.load_project(start=tmp_path)
    assert project.root == tmp_path.resolve()
    assert project.instances_dir == tmp_path.resolve() / "foo" / "i"
    assert project.briefs_dir == tmp_path.resolve() / "foo" / "b"
