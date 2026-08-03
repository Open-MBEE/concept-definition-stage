"""The facilitation surface: same K1 whitelist as MCP, correct-by-construction posture.

The facilitator service *creates* conforming models (constrained authoring: Pydantic gate,
candidates only, graded strictness — advisory verification while composing, the commit gate
blocks). The P4 AICC/LLM sidecar is a UX affordance over this same API.
"""
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from cds.core.workspace import Project  # noqa: E402
from cds.facilitator.server import build_app  # noqa: E402
from cds.mcp import server  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    proj = Project(root=tmp_path / "session", base_iri="https://cds.example/p1/")
    proj.instances_dir.mkdir(parents=True)
    return TestClient(build_app(proj))


def test_tool_routes_equal_whitelist(client: TestClient) -> None:
    from typing import Any, cast

    tool_routes = {r.path.removeprefix("/tools/") for r in cast(Any, client.app).routes
                   if getattr(r, "path", "").startswith("/tools/")}
    assert tool_routes == set(server.WHITELIST)


def test_facilitated_authoring_session(client: TestClient) -> None:
    assert client.post("/tools/cds_synthesis",
                       json={"slug": "m1", "title": "Mapping One"}).status_code == 200
    r = client.post("/tools/cds_new", json={
        "kind": "stakeholder", "slug": "ops", "label": "Operator",
        "description": "Runs the system.", "synthesis": "m1"})
    assert r.status_code == 200
    verify = client.post("/tools/cds_verify", json={})
    assert verify.status_code == 200
    assert "conforms" in verify.json()  # advisory while composing — never blocks authoring


def test_malformed_args_422_pydantic_gate(client: TestClient) -> None:
    assert client.post("/tools/cds_new", json={"kind": "need"}).status_code == 422


def test_deep_validation_maps_to_422(client: TestClient) -> None:
    # Passes the route model but fails the core Pydantic guardrail (bad slug).
    r = client.post("/tools/cds_new", json={
        "kind": "need", "slug": "NOT A SLUG!!", "label": "X",
        "description": "d", "synthesis": "m1"})
    assert r.status_code == 422


def test_commit_refused_403(client: TestClient) -> None:
    assert client.post("/tools/cds_commit", json={}).status_code == 403


def test_conflict_and_absence_status_codes(client: TestClient) -> None:
    # LARP#2 nit: 409 for exists-conflicts, 404 for absences (not blanket 422)
    body = {"kind": "goal", "slug": "g", "label": "G", "description": "A goal.",
            "synthesis": "m1"}
    client.post("/tools/cds_synthesis", json={"slug": "m1", "title": "M"})
    assert client.post("/tools/cds_new", json=body).status_code == 200
    assert client.post("/tools/cds_new", json=body).status_code == 409  # exists
    absent = dict(body, slug="ghost")
    assert client.post("/tools/cds_edit", json=absent).status_code == 404  # missing
    assert client.post("/tools/cds_discard",
                       json={"kind": "goal", "slug": "nope"}).status_code == 404
    assert client.post("/tools/cds_retract",
                       json={"kind": "goal", "slug": "g"}).status_code == 200
    assert client.post("/tools/cds_retract",
                       json={"kind": "goal", "slug": "g"}).status_code == 409  # already


def test_openapi_fields_carry_descriptions(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    ref = spec["paths"]["/tools/cds_new"]["post"]["requestBody"]["content"][
        "application/json"]["schema"]["$ref"]
    props = spec["components"]["schemas"][ref.rsplit("/", 1)[-1]]["properties"]
    for field in ("kind", "slug", "characterizes", "held_by", "stance", "for_stakeholder"):
        assert props[field].get("description"), f"{field} lacks a description"


def test_manifest_route(client: TestClient) -> None:
    assert client.get("/manifest").json()["tools"] == sorted(server.WHITELIST)


def test_openapi_declares_kind_specific_fields(client: TestClient) -> None:
    # F-1: the contract must not lie by omission — link fields are discoverable.
    spec = client.get("/openapi.json").json()
    body = spec["paths"]["/tools/cds_new"]["post"]["requestBody"]
    schema_ref = body["content"]["application/json"]["schema"]["$ref"]
    props = spec["components"]["schemas"][schema_ref.rsplit("/", 1)[-1]]["properties"]
    for field in ("for_stakeholder", "serves_goal", "refines", "addresses",
                  "segment", "interest", "influence", "cites", "supersedes"):
        assert field in props, f"{field} missing from cds_new schema"


def test_every_tool_call_is_audited(client: TestClient, tmp_path: Path) -> None:
    """REQ-K4.2 at the registry: tool calls land in the session's hash-chained audit
    regardless of transport (auditor finding K-5), refusals included."""
    from cds.mcp.provenance import AuditLog

    client.post("/tools/cds_synthesis", json={"slug": "m1", "title": "M"})
    client.post("/tools/cds_commit", json={})  # refused — refusals are audited too
    audit = AuditLog(tmp_path / "session" / "audit.jsonl")
    events = audit.replay()
    tools_called = [(e["event"]["tool"], e["event"]["status"]) for e in events]
    assert ("cds_synthesis", "ok") in tools_called
    assert ("cds_commit", "PermissionError") in tools_called
    assert all("ts" in e for e in events)  # wall-clock is a fact of the event (K-4)
    assert audit.verify_chain() is True


def test_committed_openapi_is_current() -> None:
    from cds.facilitator.export_openapi import openapi_json

    committed = Path(__file__).parents[2] / "docs" / "services" / "openapi-facilitator.json"
    assert committed.read_text(encoding="utf-8") == openapi_json()  # determinism gate
