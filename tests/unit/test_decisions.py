"""Regression tests for the maintainer decisions after the simulated user test:
supersedes link, slug validation (friendly error), tension resolve, side-ledger rm.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cds.core.authoring import (
    create_parked,
    create_queue_item,
    create_record,
    create_synthesis,
    create_tension,
    project_graph,
    remove_parked,
    remove_queue_item,
    remove_tension,
    set_tension_status,
)
from cds.core.cli import app
from cds.core.compile import compile_brief
from cds.core.init import init_project
from cds.core.model.instances import Statement, Synthesis, record_iri
from cds.core.model.notes import ParkedItem, RetrievalItem, Tension, TensionStatus
from cds.core.namespaces import CDS
from cds.core.verify import verify
from cds.core.workspace import Project, load_project


def _p(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    return load_project(start=tmp_path)


# ---- slug validation


def test_bad_slug_rejected_by_model() -> None:
    with pytest.raises(ValueError):
        Statement(slug="bad slug", kind="goal", label="x", description="y", synthesis="cd")
    with pytest.raises(ValueError):
        Synthesis(slug="Bad_Slug", title="x")


def test_bad_slug_cli_is_friendly_not_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_project(tmp_path, name="demo")
    monkeypatch.setenv("CDS_PROJECT", str(tmp_path))
    result = CliRunner().invoke(
        app, ["new", "goal", "bad slug", "--synthesis", "cd", "--label", "X", "--description", "Y"]
    )
    assert result.exit_code == 2
    assert "kebab-case" in result.output
    assert "Traceback" not in result.output


# ---- supersedes link


def test_supersedes_serialized_and_rendered(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="v1", kind="goal", label="V1",
                                     description="old", synthesis="cd"))
    old_iri = str(record_iri(project.base_iri, "goal", "v1"))
    create_record(project, Statement(slug="v2", kind="goal", label="V2",
                                     description="new", synthesis="cd", supersedes=[old_iri]))
    g = project_graph(project)
    s = record_iri(project.base_iri, "goal", "v2")
    assert (s, CDS.supersedes, record_iri(project.base_iri, "goal", "v1")) in g
    assert "supersedes: v1" in compile_brief(g, base=project.base_iri)


def test_new_supersedes_by_slug_via_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="v1", kind="goal", label="V1",
                                     description="old", synthesis="cd"))
    monkeypatch.setenv("CDS_PROJECT", str(tmp_path))
    result = CliRunner().invoke(
        app, ["new", "goal", "v2", "--synthesis", "cd", "--label", "V2",
              "--description", "new", "--supersedes", "v1"]
    )
    assert result.exit_code == 0, result.output
    g = project_graph(load_project(start=tmp_path))
    s = record_iri(project.base_iri, "goal", "v2")
    assert (s, CDS.supersedes, record_iri(project.base_iri, "goal", "v1")) in g


# ---- tension resolve


def test_tension_resolve_drops_from_brief(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_tension(project, Tension(slug="t", label="A vs B", description="pull"))
    assert "## Tensions" in compile_brief(project_graph(project), base=project.base_iri)

    set_tension_status(project, "t", TensionStatus.RESOLVED)
    assert "## Tensions" not in compile_brief(project_graph(project), base=project.base_iri)
    assert verify(project_graph(project)).passed


# ---- side-ledger deletion


def test_side_ledger_rm(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_parked(project, ParkedItem(slug="p", label="P"))
    create_queue_item(project, RetrievalItem(slug="q", question="Q?"))
    create_tension(project, Tension(slug="z", label="Z"))
    assert remove_parked(project, "p") is True
    assert remove_parked(project, "p") is False  # already gone
    assert remove_queue_item(project, "q") is True
    assert remove_tension(project, "z") is True
