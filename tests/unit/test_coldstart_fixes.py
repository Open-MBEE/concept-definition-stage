"""Regression tests for the correctness bugs found in the cold-start user test (P4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cds.core.authoring import create_record, create_synthesis, project_graph
from cds.core.init import init_project
from cds.core.model.instances import Need, Synthesis
from cds.core.verify import verify
from cds.core.workspace import Project, load_project


def _p(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    return load_project(start=tmp_path)


# ---- C1: comma-list link corruption / unvalidated link targets


def test_comma_list_splits_into_multiple_slugs() -> None:
    n = Need(slug="n", kind="need", label="N", description="d", synthesis="cd",
             for_stakeholder=["eng,platform"])
    assert n.for_stakeholder == ["eng", "platform"]  # not one bad "eng,platform"


def test_bad_link_slug_rejected() -> None:
    with pytest.raises(ValueError):
        Need(slug="n", kind="need", label="N", description="d", synthesis="cd",
             serves_goal=["Bad Slug"])


# ---- C2: verify catches dangling references (link to a nonexistent record)


def test_dangling_reference_is_flagged(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Need(slug="n", kind="need", label="N", description="need it",
                                synthesis="cd", for_stakeholder=["ghost"], serves_goal=["nope"]))
    rules = {f.rule for f in verify(project_graph(project), check_conflicts=True).findings}
    assert "DanglingReference" in rules


def test_resolved_links_are_not_flagged_dangling(tmp_path: Path) -> None:
    from cds.core.model.instances import Statement

    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="reach", kind="goal", label="Reach",
                                     description="x", synthesis="cd"))
    create_record(project, Statement(slug="seeker", kind="stakeholder", label="Seeker",
                                     description="y", synthesis="cd"))
    create_record(project, Need(slug="n", kind="need", label="N", description="the seeker needs it",
                                synthesis="cd", for_stakeholder=["seeker"], serves_goal=["reach"]))
    rules = {f.rule for f in verify(project_graph(project), check_conflicts=True).findings}
    assert "DanglingReference" not in rules


# ---- C3: missing-project errors are clean, not tracebacks


def test_main_turns_project_not_found_into_clean_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from cds.core import cli
    from cds.core.workspace import CdsProjectNotFound

    def boom() -> None:
        raise CdsProjectNotFound("no cds.toml found. Run `cds init` first.")

    monkeypatch.setattr(cli, "app", boom)
    with pytest.raises(SystemExit) as excinfo:
        cli.main()
    assert excinfo.value.code == 2
