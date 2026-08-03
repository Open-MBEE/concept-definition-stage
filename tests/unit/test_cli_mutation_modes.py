"""ADR-9 R4 — the CLI speaks both modes: scratch CRUD with durable-record vocabulary.

`cds new` refuses collisions with a three-way hint; `cds edit` requires existence;
`cds retract` appends the marker (and lists inbound referrers); `cds rm` warns — and
proceeds — when the record is part of the git-committed record; `cds compile` hides
history unless --include-history.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cds.core.authoring import project_graph
from cds.core.cli import app
from cds.core.init import init_project
from cds.core.model.instances import record_iri
from cds.core.namespaces import CDS
from cds.core.workspace import load_project

runner = CliRunner()


@pytest.fixture()
def proj(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    init_project(tmp_path, name="demo")
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["synthesis", "cd", "--title", "CD"]).exit_code == 0
    return tmp_path


def _new_goal(slug: str = "g", label: str = "G", desc: str = "A goal.") -> list[str]:
    return ["new", "goal", slug, "--synthesis", "cd", "--label", label,
            "--description", desc]


def test_new_collision_has_three_way_hint(proj: Path) -> None:
    assert runner.invoke(app, _new_goal()).exit_code == 0
    result = runner.invoke(app, _new_goal(label="G2", desc="Changed."))
    assert result.exit_code == 2
    assert "already exists" in result.output
    assert "cds edit" in result.output and "--supersedes" in result.output


def test_edit_requires_existing(proj: Path) -> None:
    result = runner.invoke(app, ["edit", "goal", "ghost", "--synthesis", "cd",
                                 "--label", "X", "--description", "Y."])
    assert result.exit_code == 2
    assert "cds new" in result.output
    assert runner.invoke(app, _new_goal()).exit_code == 0
    ok = runner.invoke(app, ["edit", "goal", "g", "--synthesis", "cd",
                             "--label", "G2", "--description", "Changed."])
    assert ok.exit_code == 0
    show = runner.invoke(app, ["show", "goal", "g"])
    assert "G2" in show.output


def test_retract_appends_marker_and_lists_referrers(proj: Path) -> None:
    assert runner.invoke(app, ["new", "stakeholder", "ops", "--synthesis", "cd",
                               "--label", "Ops", "--description", "Operator."]).exit_code == 0
    assert runner.invoke(app, ["new", "need", "n", "--synthesis", "cd",
                               "--label", "N", "--description", "Ops needs uptime.",
                               "--for-stakeholder", "ops"]).exit_code == 0
    result = runner.invoke(app, ["retract", "stakeholder", "ops",
                                 "--reason", "left the program"])
    assert result.exit_code == 0
    assert "retracted" in result.output
    assert "need/n" in result.output  # inbound referrer surfaced, not silently dangled
    project = load_project(start=proj)
    ops = record_iri(project.base_iri, "stakeholder", "ops")
    assert (ops, CDS.retracted, None) in project_graph(project)
    again = runner.invoke(app, ["retract", "stakeholder", "ops"])
    assert again.exit_code == 2
    assert "already retracted" in again.output


def test_rm_warns_when_record_is_git_committed(proj: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"],
                   cwd=proj, check=True)
    assert runner.invoke(app, _new_goal()).exit_code == 0
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "record"], cwd=proj, check=True)
    # D1 (live-QA 2026-08-02): warn, then ask; proceed on Y
    result = runner.invoke(app, ["rm", "goal", "g"], input="y\n")
    assert result.exit_code == 0
    assert "committed record" in result.output
    assert "cds retract" in result.output
    assert "removed goal g" in result.output


def test_rm_on_committed_record_declined_keeps_it(proj: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
    assert runner.invoke(app, _new_goal()).exit_code == 0
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "record"], cwd=proj, check=True)
    result = runner.invoke(app, ["rm", "goal", "g"], input="n\n")
    assert result.exit_code != 0
    assert "removed goal g" not in result.output
    listed = runner.invoke(app, ["list", "goal"])
    assert "g" in listed.output  # still there


def test_rm_yes_flag_skips_the_prompt(proj: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
    assert runner.invoke(app, _new_goal()).exit_code == 0
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "record"], cwd=proj, check=True)
    result = runner.invoke(app, ["rm", "goal", "g", "--yes"])
    assert result.exit_code == 0
    assert "removed goal g" in result.output


def test_rm_no_warning_for_uncommitted(proj: Path) -> None:
    assert runner.invoke(app, _new_goal()).exit_code == 0
    result = runner.invoke(app, ["rm", "goal", "g"])
    assert result.exit_code == 0
    assert "committed record" not in result.output


def test_compile_history_flag(proj: Path) -> None:
    assert runner.invoke(app, _new_goal("old", "Old goal", "Was replaced.")).exit_code == 0
    assert runner.invoke(app, ["retract", "goal", "old", "--reason", "cut"]).exit_code == 0
    out = proj / "brief.md"
    assert runner.invoke(app, ["compile", "--output", str(out)]).exit_code == 0
    assert "Superseded & retracted" not in out.read_text(encoding="utf-8")
    hist = proj / "brief-hist.md"
    assert runner.invoke(app, ["compile", "--output", str(hist),
                               "--include-history"]).exit_code == 0
    text = hist.read_text(encoding="utf-8")
    assert "Superseded & retracted" in text and "Old goal" in text
