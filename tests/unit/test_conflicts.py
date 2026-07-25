"""M3 — deterministic cross-record conflict/consistency checks + the Tension construct."""

from __future__ import annotations

from pathlib import Path

from cds.core.authoring import create_record, create_synthesis, create_tension, project_graph
from cds.core.init import init_project
from cds.core.model.instances import Need, Statement, Synthesis
from cds.core.model.notes import Tension
from cds.core.verify import VerifyResult, verify
from cds.core.workspace import Project, load_project


def _project(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    return load_project(start=tmp_path)


def _rules(result: VerifyResult) -> set[str]:
    return {f.rule for f in result.findings}


def test_need_form_shall_is_flagged(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Need(slug="n", kind="need", label="Bad",
                                description="The system shall connect the user.", synthesis="cd",
                                for_stakeholder=["seeker"]))
    result = verify(project_graph(project), check_conflicts=True)
    assert "NeedFormShall" in _rules(result)


def test_orphan_need_is_flagged(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Need(slug="n", kind="need", label="Orphan",
                                description="The seeker needs to reach a human.", synthesis="cd"))
    result = verify(project_graph(project), check_conflicts=True)
    assert "NeedWithoutStakeholder" in _rules(result)


def test_duplicate_statements_are_flagged(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="g1", kind="goal", label="A",
                                     description="Connect to a verified human.", synthesis="cd"))
    create_record(project, Statement(slug="g2", kind="goal", label="B",
                                     description="connect to a verified human.", synthesis="cd"))
    result = verify(project_graph(project), check_conflicts=True)
    assert "DuplicateStatement" in _rules(result)


def test_empty_integrated_set_is_info(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    result = verify(project_graph(project), check_conflicts=True)
    assert "SynthesisWithoutNeeds" in _rules(result)


def test_conflicts_are_off_by_default(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    # default verify (no flag) must NOT run the instance conflict pass
    assert "SynthesisWithoutNeeds" not in _rules(verify(project_graph(project)))


def test_conflicts_never_fail_the_gate(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Need(slug="n", kind="need", label="Bad",
                                description="The system shall do it.", synthesis="cd"))
    result = verify(project_graph(project), check_conflicts=True)
    assert result.passed  # conflicts are surfaced (T2/T3), never gate-failing


def test_tension_authoring_verifies_clean(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    iri = create_tension(project, Tension(slug="t1", label="Disrupt-ToS vs Trust",
                                          description="Power vs. buyer trust.",
                                          between=[f"{project.base_iri}need/a"]))
    assert (project.instances_dir / "tension.ttl").is_file()
    assert str(iri).endswith("tension/t1")
    result = verify(project_graph(project), check_conflicts=True)
    assert result.passed, [f.message for f in result.violations]
