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
    tool_routes = {r.path.removeprefix("/tools/") for r in client.app.routes
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


def test_manifest_route(client: TestClient) -> None:
    assert client.get("/manifest").json()["tools"] == sorted(server.WHITELIST)


def test_committed_openapi_is_current() -> None:
    from cds.facilitator.export_openapi import openapi_json

    committed = Path(__file__).parents[2] / "docs" / "services" / "openapi-facilitator.json"
    assert committed.read_text(encoding="utf-8") == openapi_json()  # determinism gate
