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
    with pytest.raises(PermissionError):
        _run("cds_commit", staging)


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
