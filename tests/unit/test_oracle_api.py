"""The conformance oracle: model instance in → verdict + granular findings out.

Verification only ("build it right" — machine); fitness-for-purpose stays with the human
gate. Stateless: the oracle holds no store and mounts no authoring tool.
"""
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from cds.oracle.app import build_app  # noqa: E402

NEED_WITH_SHALL = """\
@prefix cds: <https://w3id.org/cds#> .
@prefix cdsterm: <https://w3id.org/cds/term/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
<https://cds.example/p1/need/n1> a cds:Instance, cdsterm:need ;
    dcterms:description "The system shall stay available." .
"""


@pytest.fixture()
def client() -> TestClient:
    return TestClient(build_app())


def test_surface_is_exactly_three_routes(client: TestClient) -> None:
    from typing import Any, cast

    paths = {getattr(r, "path", None) for r in cast(Any, client.app).routes}
    tool_paths = {p for p in paths if p and not p.startswith(("/openapi", "/docs", "/redoc"))}
    assert tool_paths == {"/verify", "/rules", "/healthz"}


def test_empty_instance_conforms(client: TestClient) -> None:
    r = client.post("/verify", json={"turtle": ""})
    assert r.status_code == 200
    body = r.json()
    assert body["conforms"] is True and body["findings"] == []


def test_granular_findings_for_remediation(client: TestClient) -> None:
    r = client.post("/verify", json={"turtle": NEED_WITH_SHALL, "check_conflicts": True})
    assert r.status_code == 200
    body = r.json()
    rules = {f["rule"] for f in body["findings"]}
    assert "NeedFormShall" in rules  # named rule + focus + message = actionable remediation
    shall = next(f for f in body["findings"] if f["rule"] == "NeedFormShall")
    assert shall["focus"].endswith("/need/n1")
    assert shall["tier"] == "T2"
    assert shall["message"]


def test_bad_turtle_is_400_with_reason(client: TestClient) -> None:
    r = client.post("/verify", json={"turtle": "@prefix broken"})
    assert r.status_code == 400
    assert r.json()["detail"]


def test_rules_carry_tier_and_message(client: TestClient) -> None:
    # LARP#2 G-8: /rules is the remediation cross-reference — names alone don't cut it.
    rules = client.get("/rules").json()["rules"]
    assert rules == sorted(rules, key=lambda r: r["rule"])
    assert len(rules) >= 20
    by_name = {r["rule"]: r for r in rules}
    assert by_name["NeedFormShall"]["tier"] == "T2"
    assert by_name["instanceHasLabel"]["tier"] == "T1"
    assert by_name["instanceHasLabel"]["message"]  # sh:message surfaces
    assert all(r["tier"] in {"T1", "T2", "T3"} for r in rules)
    assert "DivergingPositions" in by_name  # conflict checks included


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_committed_openapi_is_current() -> None:
    from cds.oracle.export_openapi import openapi_json

    committed = Path(__file__).parents[2] / "docs" / "services" / "openapi-oracle.json"
    assert committed.read_text(encoding="utf-8") == openapi_json()  # determinism gate
