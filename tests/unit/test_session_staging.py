"""P2-a — session staging is a SPARSE OVERLAY over the canonical current view (ADR-5/ADR-9).

The scratch root starts empty (absence-in-staging is never a signal — kills LARP F-5's
session-pollution class); reads union canonical's current view with the staging graph,
staging winning per subject (copy-on-write shadowing); canonical files are never touched.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import RDFS, Literal

from cds.core.authoring import create_record, create_synthesis, project_graph, upsert_record
from cds.core.init import init_project
from cds.core.model.instances import Statement, Synthesis, record_iri
from cds.core.workspace import Project, load_project
from cds.mcp import staging


def _canonical(tmp_path: Path) -> Project:
    root = tmp_path / "canonical"
    init_project(root, name="canon")
    project = load_project(start=root)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="g", kind="goal", label="V1",
                                     description="Canonical statement.", synthesis="cd"))
    return project


def test_session_project_is_an_empty_scratch_root(tmp_path: Path) -> None:
    proj = staging.new_session_project("https://cds.example/test/",
                                       root=tmp_path / "session")
    assert proj is not None
    assert proj.base_iri == "https://cds.example/test/"
    assert proj.instances_dir.is_dir()
    assert list(proj.instances_dir.glob("*.ttl")) == []  # sparse: nothing pre-seeded
    assert len(project_graph(proj)) == 0


def test_two_sessions_are_isolated(tmp_path: Path) -> None:
    a = staging.new_session_project("https://cds.example/a/")
    b = staging.new_session_project("https://cds.example/b/")
    assert a.root != b.root
    create_synthesis(a, Synthesis(slug="mine", title="Mine"))
    assert len(project_graph(b)) == 0  # F-5 class dead: no cross-session bleed


def test_union_overlays_staging_over_canonical_current_view(tmp_path: Path) -> None:
    canonical = _canonical(tmp_path)
    session = staging.new_session_project(canonical.base_iri, root=tmp_path / "session")
    canon_bytes = (canonical.instances_dir / "goal.ttl").read_bytes()

    # copy-on-write edit: the staged copy shadows the canonical subject
    upsert_record(session, Statement(slug="g", kind="goal", label="V2",
                                     description="Edited in session.", synthesis="cd"))
    # plus a brand-new candidate
    create_record(session, Statement(slug="n", kind="goal", label="New",
                                     description="Only staged.", synthesis="cd"))

    union = staging.union_graph(session, canonical)
    g = record_iri(canonical.base_iri, "goal", "g")
    assert list(union.objects(g, RDFS.label)) == [Literal("V2")]  # staging wins
    n = record_iri(canonical.base_iri, "goal", "n")
    assert (n, RDFS.label, Literal("New")) in union
    # canonical untouched — candidates isolated in staging (REQ-K2.1)
    assert (canonical.instances_dir / "goal.ttl").read_bytes() == canon_bytes


def test_union_excludes_canonical_noncurrent(tmp_path: Path) -> None:
    from cds.core.authoring import retract_record

    canonical = _canonical(tmp_path)
    create_record(canonical, Statement(slug="dead", kind="goal", label="Dead",
                                       description="Retired.", synthesis="cd"))
    retract_record(canonical, "goal", "dead", reason="cut")
    session = staging.new_session_project(canonical.base_iri, root=tmp_path / "session")
    union = staging.union_graph(session, canonical)
    dead = record_iri(canonical.base_iri, "goal", "dead")
    assert (dead, None, None) not in union  # history stays out of the session read model


def test_union_without_canonical_is_just_staging(tmp_path: Path) -> None:
    session = staging.new_session_project("https://cds.example/solo/",
                                          root=tmp_path / "session")
    create_synthesis(session, Synthesis(slug="cd", title="CD"))
    union = staging.union_graph(session, None)
    assert len(union) == len(project_graph(session)) > 0


# ------------------------------------------------- overlay-aware tools (the session in use)


import pytest as _pytest  # noqa: E402

from cds.mcp import tools as _tools  # noqa: E402


@_pytest.fixture()
def bound(tmp_path: Path, monkeypatch: _pytest.MonkeyPatch) -> tuple[Project, Project]:
    canonical = _canonical(tmp_path)
    session = staging.new_session_project(canonical.base_iri, root=tmp_path / "session")
    monkeypatch.setattr(_tools.SESSION, "canonical", canonical)
    monkeypatch.setattr(_tools.SESSION, "roles", frozenset({"cds-reviewer"}))
    monkeypatch.setattr(_tools.SESSION, "approver", "https://cds.example/agent/z")
    return session, canonical


def test_tools_read_the_union(bound: tuple[Project, Project]) -> None:
    from typing import Any, cast

    session, _canonical_p = bound
    listed = cast(Any, _tools.TOOLS["cds_list"].fn(session, "goal"))
    assert ("g", "V1") in listed  # canonical record visible through the overlay
    shown = cast(Any, _tools.TOOLS["cds_show"].fn(session, "goal", "g"))
    assert shown is not None and any("V1" in ln for ln in shown)


def test_new_refuses_slug_existing_in_canonical(bound: tuple[Project, Project]) -> None:
    from cds.core.authoring import RecordExistsError

    session, _ = bound
    with _pytest.raises(RecordExistsError):
        _tools.TOOLS["cds_new"].fn(session, kind="goal", slug="g", label="Clash",
                                   description="Duplicate of canonical.", synthesis="cd")


def test_edit_copies_on_write_from_canonical(bound: tuple[Project, Project]) -> None:
    session, canonical = bound
    _tools.TOOLS["cds_edit"].fn(session, kind="goal", slug="g", label="V2",
                                description="Edited via overlay.", synthesis="cd")
    assert (session.instances_dir / "goal.ttl").exists()  # staged shadow
    canon_g = project_graph(canonical)
    g = record_iri(canonical.base_iri, "goal", "g")
    assert (g, RDFS.label, Literal("V1")) in canon_g  # canonical untouched pre-commit


def test_retract_canonical_record_via_overlay(bound: tuple[Project, Project]) -> None:
    from cds.core.namespaces import CDS

    session, canonical = bound
    from typing import Any, cast

    result = cast(Any, _tools.TOOLS["cds_retract"].fn(session, kind="goal", slug="g",
                                                      reason="descoped"))
    assert result["retracted"].endswith("/goal/g")
    staged = project_graph(session)
    assert (record_iri(canonical.base_iri, "goal", "g"), CDS.retracted,
            Literal(True)) in staged
    assert (record_iri(canonical.base_iri, "goal", "g"), CDS.retracted,
            Literal(True)) not in project_graph(canonical)  # intent only, pre-commit


def test_commit_tool_end_to_end(bound: tuple[Project, Project]) -> None:
    session, canonical = bound
    _tools.TOOLS["cds_new"].fn(session, kind="goal", slug="fresh", label="Fresh",
                               description="Session candidate.", synthesis="cd")
    from typing import Any, cast

    result = cast(Any, _tools.TOOLS["cds_commit"].fn(session))
    assert result["committed"] is True
    assert any(a.endswith("/goal/fresh") for a in result["adds"])
    merged = project_graph(canonical)
    assert (record_iri(canonical.base_iri, "goal", "fresh"), None, None) in merged


def test_commit_tool_refuses_without_role(bound: tuple[Project, Project],
                                          monkeypatch: _pytest.MonkeyPatch) -> None:
    session, _ = bound
    monkeypatch.setattr(_tools.SESSION, "roles", frozenset())
    with _pytest.raises(PermissionError):
        _tools.TOOLS["cds_commit"].fn(session)
