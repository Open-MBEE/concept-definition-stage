"""P3 — K4: PROV-O attribution + verifiable append-only audit.

REQ-K4.1: every canonical subject traces to a generating activity with agent attribution.
REQ-K4.2: the audit log is append-only (hash-chained, tamper-evident) and replayable.
Determinism: activities key on the ChangePlan content hash — no build-time clocks.
"""

from __future__ import annotations

import json
from pathlib import Path

from rdflib import RDF, Graph, URIRef

from cds.app.commit_gate import ChangePlan
from cds.core.namespaces import PROV
from cds.core.workspace import Project
from cds.mcp import provenance

# ------------------------------------------------------------------------ P3-1: stamp()


def test_stamp_builds_a_prov_graph() -> None:
    subjects = [URIRef("https://x/goal/a"), URIRef("https://x/goal/b")]
    g = provenance.stamp(subjects, user="https://x/agent/z", session="cds-session-abc",
                         model="claude-sonnet-5",
                         activity_iri="https://x/activity/commit-deadbeef")
    activity = URIRef("https://x/activity/commit-deadbeef")
    assert (activity, RDF.type, PROV.Activity) in g
    for s in subjects:
        assert (s, PROV.wasGeneratedBy, activity) in g
    # attribution: user and model are agents associated with the activity
    agents = set(g.objects(activity, PROV.wasAssociatedWith))
    assert URIRef("https://x/agent/z") in agents
    assert any("claude-sonnet-5" in str(a) for a in agents)


def test_stamp_is_deterministic() -> None:
    subjects = [URIRef("https://x/goal/a")]
    kw = dict(user="https://x/agent/z", session="s1", model="m",
              activity_iri="https://x/activity/commit-cafe")
    a = provenance.stamp(subjects, **kw)
    b = provenance.stamp(subjects, **kw)
    assert set(a) == set(b)


# ------------------------------------------------------------------- P3-2: the audit log


def test_audit_append_only_replay(tmp_path: Path) -> None:
    log = provenance.AuditLog(tmp_path / "audit.jsonl")
    log.append({"tool": "cds_new", "outcome": "ok"})
    log.append({"tool": "cds_verify", "outcome": "ok"})
    log.append({"tool": "cds_commit", "outcome": "refused"})
    events = provenance.AuditLog(tmp_path / "audit.jsonl").replay()  # fresh handle
    assert [e["event"]["tool"] for e in events] == ["cds_new", "cds_verify", "cds_commit"]
    assert [e["seq"] for e in events] == [0, 1, 2]
    assert provenance.AuditLog(tmp_path / "audit.jsonl").verify_chain() is True


def test_audit_tamper_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = provenance.AuditLog(path)
    for tool in ("cds_new", "cds_edit", "cds_commit"):
        log.append({"tool": tool, "outcome": "ok"})
    lines = path.read_text(encoding="utf-8").splitlines()
    doctored = json.loads(lines[1])
    doctored["event"]["tool"] = "cds_discard"  # rewrite history
    lines[1] = json.dumps(doctored, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert provenance.AuditLog(path).verify_chain() is False


def test_audit_never_rewrites_prior_lines(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = provenance.AuditLog(path)
    log.append({"tool": "cds_new", "outcome": "ok"})
    first = path.read_text(encoding="utf-8").splitlines()[0]
    log.append({"tool": "cds_edit", "outcome": "ok"})
    assert path.read_text(encoding="utf-8").splitlines()[0] == first


# ------------------------------------- P3-3: the gate stamps; every subject attributable


def _committed_world(
    tmp_path: Path,
) -> tuple[Project, Project, tuple[ChangePlan, ChangePlan]]:
    from cds.app import commit_gate
    from cds.core.authoring import create_record, create_synthesis, retract_record, upsert_record
    from cds.core.init import init_project
    from cds.core.model.instances import Statement, Synthesis
    from cds.core.workspace import load_project
    from cds.mcp import staging

    root = tmp_path / "canonical"
    init_project(root, name="canon")
    canonical = load_project(start=root)
    create_synthesis(canonical, Synthesis(slug="cd", title="CD"))
    create_record(canonical, Statement(slug="keep", kind="goal", label="Keep",
                                       description="Original.", synthesis="cd"))
    session = staging.new_session_project(canonical.base_iri, root=tmp_path / "session")
    create_record(session, Statement(slug="fresh", kind="goal", label="Fresh",
                                     description="New.", synthesis="cd"))
    upsert_record(session, Statement(slug="keep", kind="goal", label="Keep v2",
                                     description="Revised.", synthesis="cd"))
    create_record(session, Statement(slug="gone", kind="goal", label="Gone",
                                     description="Then retracted.", synthesis="cd"))
    plan1 = commit_gate.commit(session, canonical,
                               approver_roles=frozenset({"cds-reviewer"}),
                               approver="https://cds.example/agent/z")
    retract_record(session, "goal", "gone", reason="cut")
    plan2 = commit_gate.commit(session, canonical,
                               approver_roles=frozenset({"cds-reviewer"}),
                               approver="https://cds.example/agent/z")
    return canonical, session, (plan1, plan2)


def test_commit_writes_provenance_file(tmp_path: Path) -> None:
    canonical, _session, (plan1, _plan2) = _committed_world(tmp_path)
    prov_dir = canonical.root / "concept-definition" / "provenance"
    files = sorted(prov_dir.glob("*.ttl"))
    assert files, "commit must write a provenance graph"
    assert any(plan1.content_hash[:12] in f.name for f in files)


def test_every_committed_subject_has_provenance(tmp_path: Path) -> None:
    """REQ-K4.1 — every subject the gate wrote traces to an attributed activity."""
    from cds.core.authoring import project_graph
    from cds.core.namespaces import CDS

    canonical, _session, _plans = _committed_world(tmp_path)
    prov_graph = Graph()
    prov_dir = canonical.root / "concept-definition" / "provenance"
    for ttl in prov_dir.glob("*.ttl"):
        prov_graph.parse(ttl, format="turtle")
    canon = project_graph(canonical)
    committed = {s for s in canon.subjects(RDF.type, CDS.Instance)}
    assert committed
    for s in committed:
        assert (s, PROV.wasGeneratedBy, None) in prov_graph \
            or (s, PROV.wasInvalidatedBy, None) in prov_graph, f"{s} unattributed"
    # each activity names its approver
    for activity in prov_graph.subjects(RDF.type, PROV.Activity):
        assert (activity, PROV.wasAssociatedWith,
                URIRef("https://cds.example/agent/z")) in prov_graph
    # retraction is invalidation, revision is revision
    base = canonical.base_iri
    assert (URIRef(f"{base}goal/gone"), PROV.wasInvalidatedBy, None) in prov_graph


def test_commit_appends_audit_events(tmp_path: Path) -> None:
    canonical, _session, (plan1, plan2) = _committed_world(tmp_path)
    audit = provenance.AuditLog(
        canonical.root / "concept-definition" / "audit.jsonl")
    events = audit.replay()
    kinds = [e["event"]["action"] for e in events]
    assert kinds.count("commit") == 2
    hashes = [e["event"]["content_hash"] for e in events]
    assert plan1.content_hash in hashes and plan2.content_hash in hashes
    assert audit.verify_chain() is True


def test_provenance_files_are_append_only(tmp_path: Path) -> None:
    from cds.app import commit_gate

    canonical, session, _plans = _committed_world(tmp_path)
    prov_dir = canonical.root / "concept-definition" / "provenance"
    before = {f.name: f.read_bytes() for f in prov_dir.glob("*.ttl")}
    assert len(before) == 2  # one file per commit, never rewritten
    # a no-op commit adds no file and rewrites none
    commit_gate.commit(session, canonical,
                       approver_roles=frozenset({"cds-reviewer"}),
                       approver="https://cds.example/agent/z")
    after = {f.name: f.read_bytes() for f in prov_dir.glob("*.ttl")}
    assert before == after
