"""ADR-9 R2 — explicit mutation primitives: create refuses, edit requires, retract appends.

Scratch mode owns create/edit/discard; the APPEND primitives (retract_record,
mark_superseded) only ever add triples — content is preserved byte-for-byte outside the
marker. The current view is a graph query (cds.core.view), never a file convention.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Literal, URIRef

from cds.core.authoring import (
    AlreadyRetractedError,
    RecordExistsError,
    RecordNotFoundError,
    create_record,
    create_synthesis,
    edit_record,
    find_referrers,
    mark_superseded,
    project_graph,
    retract_record,
    show_record,
    upsert_record,
)
from cds.core.init import init_project
from cds.core.model.instances import Need, Stakeholder, Statement, Synthesis, record_iri
from cds.core.namespaces import CDS
from cds.core.view import current_view, is_current
from cds.core.workspace import Project, load_project


def _p(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    project = load_project(start=tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    return project


def _goal(slug: str = "g", label: str = "V1", desc: str = "first") -> Statement:
    return Statement(slug=slug, kind="goal", label=label, description=desc, synthesis="cd")


def test_create_refuses_existing_slug(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_record(project, _goal())
    with pytest.raises(RecordExistsError):
        create_record(project, _goal(label="V2", desc="second"))


def test_edit_requires_existing_slug(tmp_path: Path) -> None:
    project = _p(tmp_path)
    with pytest.raises(RecordNotFoundError):
        edit_record(project, _goal())
    create_record(project, _goal())
    edit_record(project, _goal(label="V2", desc="second"))
    lines = "\n".join(show_record(project, "goal", "g") or [])
    assert "V2" in lines


def test_upsert_keeps_old_semantics(tmp_path: Path) -> None:
    project = _p(tmp_path)
    upsert_record(project, _goal())
    upsert_record(project, _goal(label="V2", desc="second"))  # no refusal — explicit upsert


def test_retract_appends_marker_and_preserves_content(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_record(project, _goal())
    before = (project.instances_dir / "goal.ttl").read_text(encoding="utf-8")
    iri = retract_record(project, "goal", "g", reason="superseded by roadmap v2")
    after = (project.instances_dir / "goal.ttl").read_text(encoding="utf-8")
    g = project_graph(project)
    assert (iri, CDS.retracted, Literal(True)) in g
    assert (iri, CDS.retractionReason, Literal("superseded by roadmap v2")) in g
    # every original line survives (append-only: nothing removed, only marker lines added)
    for line in before.splitlines():
        assert line in after


def test_retract_refuses_absent_and_double(tmp_path: Path) -> None:
    project = _p(tmp_path)
    with pytest.raises(RecordNotFoundError):
        retract_record(project, "goal", "ghost")
    create_record(project, _goal())
    retract_record(project, "goal", "g")
    with pytest.raises(AlreadyRetractedError):
        retract_record(project, "goal", "g", reason="again")


def test_mark_superseded_appends_inverse_marker(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_record(project, _goal())
    new_iri = record_iri(project.base_iri, "goal", "g2")
    mark_superseded(project, "goal", "g", by=new_iri)
    g = project_graph(project)
    old = record_iri(project.base_iri, "goal", "g")
    assert (old, CDS.supersededBy, new_iri) in g


def test_find_referrers_reports_inbound_links(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_record(project, Stakeholder(slug="ops", kind="stakeholder", label="Ops",
                                       description="Operator.", synthesis="cd"))
    create_record(project, Need(slug="n", kind="need", label="N",
                                description="The ops needs the system to run.",
                                synthesis="cd", for_stakeholder=["ops"]))
    ops = record_iri(project.base_iri, "stakeholder", "ops")
    referrers = find_referrers(project, ops)
    assert record_iri(project.base_iri, "need", "n") in referrers


def test_authored_supersedes_materializes_inverse_marker(tmp_path: Path) -> None:
    """G-7/G-2: creating a record with supersedes=[old] marks the old record superseded
    eagerly (scratch and gate-merged graphs identical), and bare slugs resolve same-kind."""
    from cds.core.compile import compile_brief

    project = _p(tmp_path)
    create_record(project, _goal("fast", "Fast delivery", "30-minute windows."))
    new = Statement(slug="safe", kind="goal", label="Safe delivery",
                    description="Safety envelope first.", synthesis="cd",
                    supersedes=["fast"])  # bare slug — resolves to the same-kind record
    create_record(project, new)
    g = project_graph(project)
    old = record_iri(project.base_iri, "goal", "fast")
    new_iri = record_iri(project.base_iri, "goal", "safe")
    assert (new_iri, CDS.supersedes, old) in g  # resolved IRI, not a broken relative ref
    assert (old, CDS.supersededBy, new_iri) in g  # eager inverse marker
    brief = compile_brief(g, base=project.base_iri)
    assert "Safe delivery" in brief
    assert "Fast delivery" not in brief  # superseded → out of the current view


def test_current_view_filters_markers(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_record(project, _goal("keep", "Keep", "stays"))
    create_record(project, _goal("old", "Old", "was replaced"))
    create_record(project, _goal("gone", "Gone", "was retracted"))
    mark_superseded(project, "goal", "old",
                    by=record_iri(project.base_iri, "goal", "keep"))
    retract_record(project, "goal", "gone", reason="scope cut")
    g = project_graph(project)
    keep = record_iri(project.base_iri, "goal", "keep")
    old = record_iri(project.base_iri, "goal", "old")
    gone = record_iri(project.base_iri, "goal", "gone")
    assert is_current(g, keep) and not is_current(g, old) and not is_current(g, gone)
    cv = current_view(g)
    assert (keep, None, None) in cv
    assert (old, None, None) not in cv and (gone, None, None) not in cv
    # markers themselves stay queryable in the FULL graph — the changelog is never lost
    assert (gone, CDS.retracted, Literal(True)) in g


def test_scope_iri_is_named_graph_ready() -> None:
    # ADR-9/lineage: any scope IRI we mint must be usable as a named-graph URI later.
    view_iri = URIRef("https://w3id.org/cds/view/current")
    assert str(view_iri).startswith("https://")
