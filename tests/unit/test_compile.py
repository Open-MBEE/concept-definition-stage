"""M5 — deterministic Markdown brief compilation."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cds.core.authoring import create_record, create_synthesis, project_graph
from cds.core.cli import app
from cds.core.compile import compile_brief
from cds.core.init import init_project
from cds.core.model.instances import Need, Statement, Synthesis
from cds.core.workspace import Project, load_project


def _project(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    return load_project(start=tmp_path)


def _author(project: Project) -> None:
    create_synthesis(project, Synthesis(slug="cd", title="Agent, get me a human"))
    create_record(project, Statement(
        slug="m", kind="mission", label="Reach a human",
        description="Get a person to a verified human.", synthesis="cd"))
    create_record(project, Statement(
        slug="reach", kind="goal", label="Reach",
        description="Connect to a verified human.", synthesis="cd"))
    create_record(project, Statement(
        slug="seeker", kind="stakeholder", label="Seeker",
        description="Person trying to reach a human.", synthesis="cd"))
    create_record(project, Need(
        slug="n1", kind="need", label="Effortless reach",
        description="The seeker needs to reach a human without skill.",
        synthesis="cd", for_stakeholder=["seeker"], serves_goal=["reach"]))


def test_brief_has_sections_and_content(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _author(project)
    md = compile_brief(project_graph(project), base=project.base_iri)
    assert md.startswith("# Agent, get me a human")
    assert "## Business / Mission Analysis" in md
    assert "### Mission" in md
    assert "## Stakeholders" in md
    assert "| Stakeholder |" in md
    assert "## Integrated Set of Needs" in md
    assert "Effortless reach" in md
    assert "stakeholder: seeker" in md


def test_brief_is_byte_stable(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _author(project)
    g = project_graph(project)
    assert compile_brief(g, base=project.base_iri) == compile_brief(g, base=project.base_iri)


def test_cds_compile_cli_writes_brief(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path)
    _author(project)
    monkeypatch.setenv("CDS_PROJECT", str(tmp_path))
    result = CliRunner().invoke(app, ["compile"])
    assert result.exit_code == 0, result.output
    brief = tmp_path / "concept-definition" / "briefs" / "concept-definition.md"
    assert brief.is_file()
    assert "Agent, get me a human" in brief.read_text()
