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
