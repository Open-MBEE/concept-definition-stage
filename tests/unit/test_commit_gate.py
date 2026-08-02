"""P2-b — the K2 commit gate: ChangePlan, appends-never-deletes, held-out, determinism.

The gate is the ONLY crossing from scratch into the durable record. It composes R2's
primitives (no RDF-writing logic of its own beyond them), enumerates every change for the
approver, writes the plan as an artifact stamped with approver + content hash, refuses on
unwaived T1, holds out records citing unverified sources (X7), and never deletes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, URIRef

from cds.app import commit_gate
from cds.core.authoring import (
    create_record,
    create_synthesis,
    project_graph,
    retract_record,
    upsert_record,
)
from cds.core.init import init_project
from cds.core.model.instances import Statement, Synthesis, record_iri
from cds.core.namespaces import CDS
from cds.core.serialize import canonical_turtle
from cds.core.workspace import Project, load_project
from cds.mcp import staging

REVIEWER = frozenset({"cds-reviewer"})


def _canonical(tmp_path: Path) -> Project:
    root = tmp_path / "canonical"
    init_project(root, name="canon")
    project = load_project(start=root)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="keep", kind="goal", label="Keep",
                                     description="Stays as-is.", synthesis="cd"))
    return project


def _session(tmp_path: Path, canonical: Project) -> Project:
    return staging.new_session_project(canonical.base_iri, root=tmp_path / "session")


def test_commit_requires_reviewer_role(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        commit_gate.commit(object(), approver_roles=frozenset())
    with pytest.raises(PermissionError):
        commit_gate.commit(object(), approver_roles=frozenset({"cds-facilitator-user"}))


def test_commit_requires_a_canonical_target(tmp_path: Path) -> None:
    session = staging.new_session_project("https://cds.example/x/")
    with pytest.raises(ValueError):
        commit_gate.commit(session, None, approver_roles=REVIEWER)


def test_changeplan_enumerates_every_change(tmp_path: Path) -> None:
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    base = canonical.base_iri
    # add
    create_record(session, Statement(slug="fresh", kind="goal", label="Fresh",
                                     description="Brand new.", synthesis="cd"))
    # revision (copy-on-write edit of a canonical record)
    upsert_record(session, Statement(slug="keep", kind="goal", label="Keep v2",
                                     description="Edited in session.", synthesis="cd"))
    # supersession: new record replaces a canonical one
    create_record(canonical, Statement(slug="old", kind="goal", label="Old",
                                       description="To be replaced.", synthesis="cd"))
    create_record(session, Statement(slug="new", kind="goal", label="New",
                                     description="Replacement.", synthesis="cd",
                                     supersedes=[str(record_iri(base, "goal", "old"))]))
    plan = commit_gate.plan_commit(session, canonical)
    assert record_iri(base, "goal", "fresh") in plan.adds
    assert record_iri(base, "goal", "keep") in plan.revisions
    assert (record_iri(base, "goal", "old"), record_iri(base, "goal", "new")) \
        in plan.supersessions
    assert plan.content_hash


def test_commit_applies_and_appends_never_deletes(tmp_path: Path) -> None:
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    base = canonical.base_iri
    before = (canonical.instances_dir / "goal.ttl").read_text(encoding="utf-8")

    create_record(session, Statement(slug="fresh", kind="goal", label="Fresh",
                                     description="Brand new.", synthesis="cd"))
    # retraction intent: copy-on-write then retract in staging
    upsert_record(session, Statement(slug="keep", kind="goal", label="Keep",
                                     description="Stays as-is.", synthesis="cd"))
    retract_record(session, "goal", "keep", reason="descoped")

    plan = commit_gate.commit(session, canonical, approver_roles=REVIEWER,
                              approver="https://cds.example/agent/z")
    assert record_iri(base, "goal", "keep") in plan.retractions
    after = (canonical.instances_dir / "goal.ttl").read_text(encoding="utf-8")
    for line in before.splitlines():
        assert line in after  # nothing deleted — only appended
    g = project_graph(canonical)
    assert (record_iri(base, "goal", "keep"), CDS.retracted, Literal(True)) in g
    assert (record_iri(base, "goal", "fresh"), None, None) in g
    # the plan artifact exists, named by its content hash, and names the approver
    plans = list((canonical.root / "concept-definition" / "changeplans").glob("*.md"))
    assert len(plans) == 1 and plan.content_hash[:12] in plans[0].name
    text = plans[0].read_text(encoding="utf-8")
    assert "https://cds.example/agent/z" in text and plan.content_hash in text


def test_commit_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    create_record(session, Statement(slug="fresh", kind="goal", label="Fresh",
                                     description="Brand new.", synthesis="cd"))
    commit_gate.commit(session, canonical, approver_roles=REVIEWER)
    snapshot = {p.name: p.read_bytes() for p in canonical.instances_dir.glob("*.ttl")}
    replan = commit_gate.plan_commit(session, canonical)
    assert replan.empty  # staged state == canonical → nothing to do
    commit_gate.commit(session, canonical, approver_roles=REVIEWER)
    again = {p.name: p.read_bytes() for p in canonical.instances_dir.glob("*.ttl")}
    assert snapshot == again  # byte-identical — re-commit is a no-op (N3.1)


def test_revision_of_committed_record_commits(tmp_path: Path) -> None:
    """LARP#3 H-1 (critical): the edit→commit loop is the core P2 workflow.

    The verify preview must use the OVERLAY union (staged shadow wins per subject), not a
    naive graph sum — otherwise a revised subject carries two labels and trips maxCount 1.
    """
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    from rdflib import RDFS

    upsert_record(session, Statement(slug="keep", kind="goal", label="Keep v2",
                                     description="Revised in session.", synthesis="cd"))
    plan = commit_gate.commit(session, canonical, approver_roles=REVIEWER)
    assert record_iri(canonical.base_iri, "goal", "keep") in plan.revisions
    g = project_graph(canonical)
    assert list(g.objects(record_iri(canonical.base_iri, "goal", "keep"),
                          RDFS.label)) == [Literal("Keep v2")]


def test_blocked_commit_leaves_canonical_untouched(tmp_path: Path) -> None:
    """LARP#3 H-2: a refused commit must be a no-op on the durable record."""
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    create_record(session, Statement(slug="bad", kind="goal", label="Bad",
                                     description="Will be corrupted.", synthesis="cd"))
    from rdflib import RDFS as _RDFS
    path = session.instances_dir / "goal.ttl"
    graph = Graph()
    graph.parse(path, format="turtle")
    graph.remove((None, _RDFS.label, None))
    path.write_text(graph.serialize(format="turtle"), encoding="utf-8")
    before = {p.name: p.read_bytes() for p in canonical.instances_dir.glob("*.ttl")}
    with pytest.raises(commit_gate.CommitBlockedError):
        commit_gate.commit(session, canonical, approver_roles=REVIEWER)
    after = {p.name: p.read_bytes() for p in canonical.instances_dir.glob("*.ttl")}
    assert before == after


def test_stale_plan_hash_is_refused(tmp_path: Path) -> None:
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    create_record(session, Statement(slug="a", kind="goal", label="A",
                                     description="First.", synthesis="cd"))
    plan = commit_gate.plan_commit(session, canonical)
    create_record(session, Statement(slug="b", kind="goal", label="B",
                                     description="Sneaked in after approval.", synthesis="cd"))
    with pytest.raises(PermissionError):
        commit_gate.commit(session, canonical, approver_roles=REVIEWER, plan=plan)


def test_held_out_pending_source_excluded_but_rest_commits(tmp_path: Path) -> None:
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    base = canonical.base_iri
    # a source present in the session graph but NOT verified
    src = URIRef(f"{base}src/sebok-pending")
    g = Graph()
    g.add((src, RDF.type, CDS.Source))
    (session.instances_dir / "sources.ttl").write_text(
        canonical_turtle(g, prefixes={"cds": str(CDS)}), encoding="utf-8")
    create_record(session, Statement(slug="risky", kind="goal", label="Risky",
                                     description="Leans on unverified canon.",
                                     synthesis="cd", cites=[str(src)]))
    create_record(session, Statement(slug="safe", kind="goal", label="Safe",
                                     description="No citation needed.", synthesis="cd"))
    plan = commit_gate.commit(session, canonical, approver_roles=REVIEWER)
    assert record_iri(base, "goal", "risky") in plan.held  # X7: held, surfaced
    merged = project_graph(canonical)
    assert (record_iri(base, "goal", "risky"), None, None) not in merged
    assert (record_iri(base, "goal", "safe"), None, None) in merged


def test_t1_violation_blocks_the_commit(tmp_path: Path) -> None:
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    create_record(session, Statement(slug="bad", kind="goal", label="Bad",
                                     description="Will be corrupted.", synthesis="cd"))
    # simulate corruption (break-a-term UAT): strip the mandatory label
    from rdflib import RDFS
    path = session.instances_dir / "goal.ttl"
    graph = Graph()
    graph.parse(path, format="turtle")
    graph.remove((None, RDFS.label, None))
    path.write_text(graph.serialize(format="turtle"), encoding="utf-8")
    with pytest.raises(commit_gate.CommitBlockedError):
        commit_gate.commit(session, canonical, approver_roles=REVIEWER)


def test_content_hash_is_stable(tmp_path: Path) -> None:
    canonical = _canonical(tmp_path)
    session = _session(tmp_path, canonical)
    create_record(session, Statement(slug="a", kind="goal", label="A",
                                     description="First.", synthesis="cd"))
    h1 = commit_gate.plan_commit(session, canonical).content_hash
    h2 = commit_gate.plan_commit(session, canonical).content_hash
    assert h1 == h2 and len(h1) == len(hashlib.sha256(b"").hexdigest())
