"""Cold-start learner features: cds explain, cds guide, cds --version."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cds.core.cli import app
from cds.core.explain import explain, glossary
from cds.core.model.instances import KINDS
from cds.core.workspace import package_dir

runner = CliRunner()


def test_explain_covers_every_authorable_kind() -> None:
    for kind in KINDS:
        lines = explain(kind)
        assert lines is not None, kind
        assert any("In plain terms" in ln for ln in lines), kind


def test_explain_need_mentions_need_form() -> None:
    lines = explain("need")
    assert lines is not None
    assert any("need-form" in ln for ln in lines)


def test_explain_unknown_term_exits_2() -> None:
    result = runner.invoke(app, ["explain", "bogus"])
    assert result.exit_code == 2
    assert "unknown term" in result.output


def test_explain_no_arg_lists_glossary() -> None:
    result = runner.invoke(app, ["explain"])
    assert result.exit_code == 0
    assert "Record kinds you can author" in result.output
    assert glossary()  # non-empty


def test_guide_prints_the_getting_started() -> None:
    result = runner.invoke(app, ["guide"])
    assert result.exit_code == 0
    assert "Getting started" in result.output


def test_packaged_guide_matches_docs_source() -> None:
    """DRY: the guide shipped in the wheel must match docs/getting-started.md."""
    packaged = package_dir() / "assets" / "guide" / "getting-started.md"
    repo_root = package_dir().resolve().parents[1]  # src/cds -> repo root
    docs_source = repo_root / "docs" / "getting-started.md"
    assert packaged.read_text() == docs_source.read_text()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip().startswith("cds ")


def test_missing_project_message_is_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # a project command with no project resolvable: the error text is clean, not a raw traceback
    monkeypatch.delenv("CDS_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["list", "goal"])
    assert "cds.toml" in str(result.output) + str(result.exception)
