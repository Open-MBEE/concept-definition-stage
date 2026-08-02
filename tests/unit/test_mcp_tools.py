"""P1 acceptance — the whitelisted tools drive a full authoring session (K1).

Spec §10 P1 gate: "tools drive a full authoring session". Every tool is a thin wrapper over
unchanged cds.core functions and takes the session staging ``Project`` as its first argument;
write tools produce candidates only (K2 posture — ``cds_commit`` refuses until P2).
"""
from pathlib import Path
from typing import Any

import pytest

from cds.core.workspace import Project
from cds.mcp import tools


@pytest.fixture()
def staging(tmp_path: Path) -> Project:
    proj = Project(root=tmp_path / "session", base_iri="https://cds.example/p1/")
    proj.instances_dir.mkdir(parents=True)
    return proj


def _run(name: str, *args: object, **kw: object) -> Any:
    return tools.TOOLS[name].fn(*args, **kw)


def test_read_tools(staging: Project) -> None:
    assert _run("cds_explain", staging, "need")  # non-empty guidance lines
    assert _run("cds_list", staging, "need") == []


def test_authoring_session(staging: Project) -> None:
    _run("cds_synthesis", staging, slug="m1", title="Mapping One")
    _run("cds_new", staging, kind="stakeholder", slug="ops", label="Operator",
         description="Runs the system day to day.", synthesis="m1")
    _run("cds_new", staging, kind="need", slug="uptime", label="Uptime",
         description="The operator needs the system to stay available.",
         synthesis="m1", for_stakeholder=["ops"])
    assert [s for s, _ in _run("cds_list", staging, "need")] == ["uptime"]
    assert _run("cds_show", staging, "need", "uptime") is not None
    _run("cds_edit", staging, kind="need", slug="uptime", label="Uptime",
         description="The operator needs 99.9% availability.",
         synthesis="m1", for_stakeholder=["ops"])
    result = _run("cds_verify", staging)
    assert hasattr(result, "conforms")  # a VerifyResult, not a pyshacl artifact
    brief = _run("cds_compile", staging)
    assert isinstance(brief, str) and "Uptime" in brief


def test_writes_stay_inside_staging(staging: Project, tmp_path: Path) -> None:
    _run("cds_synthesis", staging, slug="m1", title="Mapping One")
    _run("cds_new", staging, kind="goal", slug="g1", label="Goal One",
         description="A goal.", synthesis="m1")
    written = {p for p in tmp_path.rglob("*") if p.is_file()}
    assert written, "expected candidate files in staging"
    assert all(staging.root in p.parents for p in written)


def test_ledger_tools(staging: Project) -> None:
    _run("cds_queue_add", staging, slug="sebok-need", question="Secure SEBoK 'need' verbatim")
    _run("cds_queue_set", staging, slug="sebok-need", status="provided")
    _run("cds_park_add", staging, slug="later", label="Later idea")
    _run("cds_tension_add", staging, slug="t1", label="Scope tension")
    _run("cds_tension_resolve", staging, slug="t1")


def test_commit_refused_in_p1(staging: Project) -> None:
    with pytest.raises(PermissionError) as exc:
        _run("cds_commit", staging)
    msg = str(exc.value)
    # F-7: refusal speaks to the user, not the roadmap — safety, then the next step
    assert "safely in the session" in msg and "reviewer" in msg


def test_list_unknown_kind_teaches_the_kinds(staging: Project) -> None:
    with pytest.raises(ValueError) as exc:
        _run("cds_list", staging, "synthesis")
    assert "need" in str(exc.value)  # F-6: the error lists valid kinds, not a raw KeyError


def test_explain_unknown_name_suggests(staging: Project) -> None:
    lines = _run("cds_explain", staging, "getting-started")
    assert lines is not None  # F-11: never a bare null
    joined = "\n".join(lines)
    assert "need" in joined and "stakeholder" in joined  # an index to try


def test_waive_unknown_rule_refused(staging: Project) -> None:
    with pytest.raises(ValueError) as exc:  # F-3: no dead waivers in an append-only ledger
        _run("cds_waive", staging, waiver_id="https://x/w", rule="NoSuchRule", reason="typo")
    assert "NoSuchRule" in str(exc.value)


def test_waive_t1_class_rule_refused_even_without_live_finding(staging: Project) -> None:
    # instanceHasLabel is a sh:Violation property shape — T1-class, never waivable (F-3),
    # even when no live finding currently matches it.
    with pytest.raises(PermissionError):
        _run("cds_waive", staging, waiver_id="https://x/w", rule="instanceHasLabel",
             reason="just testing")


def test_discard_removes_staged_candidate_and_reports_referrers(staging: Project) -> None:
    _run("cds_synthesis", staging, slug="m1", title="M")
    _run("cds_new", staging, kind="stakeholder", slug="ops", label="Ops",
         description="Operator.", synthesis="m1")
    _run("cds_new", staging, kind="need", slug="n", label="N",
         description="Ops needs uptime.", synthesis="m1", for_stakeholder=["ops"])
    result = _run("cds_discard", staging, kind="stakeholder", slug="ops")
    assert result["discarded"] == "ops"
    assert any(r.endswith("/need/n") for r in result["referrers"])  # warned, not silent
    assert _run("cds_list", staging, "stakeholder") == []


def test_discard_covers_ledgers(staging: Project) -> None:
    _run("cds_park_add", staging, slug="later", label="Later")
    _run("cds_queue_add", staging, slug="q1", question="Find canon")
    _run("cds_tension_add", staging, slug="t1", label="T")
    for kind, slug in (("parked", "later"), ("queue", "q1"), ("tension", "t1")):
        assert _run("cds_discard", staging, kind=kind, slug=slug)["discarded"] == slug


def test_discard_absent_raises(staging: Project) -> None:
    with pytest.raises(KeyError):
        _run("cds_discard", staging, kind="goal", slug="ghost")


def test_retract_tool_appends_marker(staging: Project) -> None:
    from rdflib import Literal

    from cds.core.authoring import project_graph
    from cds.core.namespaces import CDS

    _run("cds_synthesis", staging, slug="m1", title="M")
    _run("cds_new", staging, kind="goal", slug="g", label="G",
         description="A goal.", synthesis="m1")
    before = (staging.instances_dir / "goal.ttl").read_text(encoding="utf-8")
    result = _run("cds_retract", staging, kind="goal", slug="g", reason="scope cut")
    assert result["retracted"].endswith("/goal/g")
    after = (staging.instances_dir / "goal.ttl").read_text(encoding="utf-8")
    for line in before.splitlines():
        assert line in after  # append-only: content preserved
    g = project_graph(staging)
    assert (None, CDS.retracted, Literal(True)) in g


def test_tool_modes_form_the_deontic_table(staging: Project) -> None:
    modes = {name: spec.mode.value for name, spec in tools.TOOLS.items()}
    assert modes["cds_explain"] == "read" and modes["cds_verify"] == "read"
    assert modes["cds_new"] == "scratch" and modes["cds_discard"] == "scratch"
    assert modes["cds_retract"] == "append" and modes["cds_waive"] == "append"
    assert modes["cds_commit"] == "commit"
    assert all(spec.mode is not None for spec in tools.TOOLS.values())
    # back-compat: writes == (mode != read)
    assert not tools.TOOLS["cds_list"].writes and tools.TOOLS["cds_new"].writes


def test_waive_appends_and_t1_guard(staging: Project) -> None:
    # The guard: a waiver selecting a live T1 finding must be refused (T1 is never waivable).
    from cds.core.verify import Finding, Severity

    t1 = Finding(Severity.VIOLATION, "SomeShape", "https://x/", "boom")
    with pytest.raises(PermissionError):
        tools.refuse_if_waives_t1([t1], rule="SomeShape", focus=None)

    # Waiving with no matching T1 succeeds and is append-only (both waivers survive).
    _run("cds_waive", staging, waiver_id="https://cds.example/p1/waiver/w1",
         rule="NeedServesNoGoal", reason="tracked in backlog")
    _run("cds_waive", staging, waiver_id="https://cds.example/p1/waiver/w2",
         rule="SynthesisWithoutNeeds", reason="early session")
    text = (staging.instances_dir / "waivers.ttl").read_text(encoding="utf-8")
    assert "w1" in text and "w2" in text


# --------------------------------------------------------- B1 (live-QA 2026-08-02 @ bb2d4a7)


def test_no_var_keyword_params_in_registry() -> None:
    """B1: a ``**kwargs`` parameter collapses to one opaque object under the MCP SDK's
    schema derivation, silently dropping every link field. Tools declare explicit params."""
    import inspect

    for spec in tools.TOOLS.values():
        for param in inspect.signature(spec.fn).parameters.values():
            assert param.kind is not inspect.Parameter.VAR_KEYWORD, (
                f"{spec.name} declares **{param.name}; the MCP transport cannot serve it"
            )


def test_record_field_union_is_explicit_on_write_tools() -> None:
    """B1 drift guard: every authorable-kind model field must be an explicit parameter of
    cds_new/cds_edit, so a new record field can never silently vanish on a transport."""
    import inspect

    from cds.core.model.instances import AUTHORABLE_KINDS, model_for_kind

    handled = {"slug", "kind", "label", "description", "synthesis"}
    union: set[str] = set()
    for kind in AUTHORABLE_KINDS:
        union |= set(model_for_kind(kind).model_fields) - handled
    for name in ("cds_new", "cds_edit"):
        params = set(inspect.signature(tools.TOOLS[name].fn).parameters)
        missing = union - params
        assert not missing, f"{name} is missing explicit fields: {sorted(missing)}"


def test_new_link_fields_reach_the_record(staging: Project) -> None:
    """B1 round-trip: link args land as triples (the QA run's orphan-need repro)."""
    _run("cds_synthesis", staging, slug="m1", title="Mapping One")
    _run("cds_new", staging, kind="stakeholder", slug="ops", label="Operator",
         description="Runs the system day to day.", synthesis="m1")
    _run("cds_new", staging, kind="need", slug="uptime", label="Uptime",
         description="The operator needs the system to stay available.",
         synthesis="m1", for_stakeholder=["ops"])
    result = _run("cds_verify", staging)
    rules = {f.rule for f in result.findings}
    assert "NeedWithoutStakeholder" not in rules
