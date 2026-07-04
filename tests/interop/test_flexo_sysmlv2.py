"""Live OpenMBEE Flexo SysML v2 service integration tests (roadmap T9).

Auto-skips unless `FLEXO_SYSMLV2_URL` / `FLEXO_SYSMLV2_TOKEN` are set (see `.env.example`) AND the
Open-MBEE `sysmlv2-python-client` is installed (`uv sync --extra interop`). To run:

    uv run --env-file .env pytest tests/interop/test_flexo_sysmlv2.py

Tests cover three T9 milestones:
  1. Connectivity — service reachable, projects list returned
  2. Corpus — live project contains Usage-level elements (PartUsage / RequirementUsage)
  3. Bridge — Definition→Usage bridge: a live PartUsage routes through its owning PartDefinition
               to the cds:system-of-interest concept via the equivalence axioms
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from rdflib import OWL, RDF, URIRef

from cds.core.namespaces import CDS_TERM, OMG_SYSML
from cds.stages.concept_definition.build import build_concept_definition_graph

# ---------------------------------------------------------------------------
# shared SPARQL patterns (mirrored from test_sysml_join.py)
# ---------------------------------------------------------------------------

_JOIN = """
PREFIX cds: <https://w3id.org/cds#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?term ?model WHERE {
    ?term  cds:sysmlConstruct ?local .
    ?local owl:equivalentClass ?omg .
    ?model a ?omg .
}
"""

# 2-hop bridge: usage --[omg-sysml:type]--> definition --[rdf:type]--> PartDefinition metaclass
_BRIDGE_JOIN = """
PREFIX cds: <https://w3id.org/cds#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX omg: <https://www.omg.org/spec/SysML/20240801/SysML#>
SELECT ?term ?usage WHERE {
    ?term  cds:sysmlConstruct ?local .
    ?local owl:equivalentClass ?omg .
    ?def   a ?omg .
    ?usage omg:type ?def .
}
"""


def _join_pairs(result: Any) -> set[tuple[str, str]]:
    return {(str(row[0]), str(row[1])) for row in result}


# ---------------------------------------------------------------------------
# credential / client helpers
# ---------------------------------------------------------------------------


def _creds() -> tuple[str | None, str | None]:
    return os.environ.get("FLEXO_SYSMLV2_URL"), os.environ.get("FLEXO_SYSMLV2_TOKEN")


def _make_client(sysmlv2_client: Any) -> Any:
    url, token = _creds()
    assert url and token
    bearer = token if token.startswith("Bearer") else f"Bearer {token}"
    return sysmlv2_client.SysMLV2Client(base_url=url, bearer_token=bearer)


def _first_project_with_elements(
    client: Any,
) -> tuple[str, str, list[dict[str, Any]]]:
    """Return (project_id, commit_id, elements) for the first project with committed elements."""
    for proj in client.get_projects():
        pid = proj.get("@id") or proj.get("elementId", "")
        commits = client.list_commits(pid)
        if not commits:
            continue
        cid = commits[0].get("@id") or commits[0].get("elementId", "")
        try:
            elems = client.list_elements(pid, commit_id=cid)
        except Exception:
            continue
        if elems:
            return pid, cid, elems
    pytest.skip("No Starforge project with committed elements found")


# ---------------------------------------------------------------------------
# T9 milestone 1: connectivity
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not all(_creds()), reason="FLEXO_SYSMLV2_* not set (see .env.example)")
def test_flexo_sysmlv2_service_is_reachable() -> None:
    sysmlv2_client = pytest.importorskip(
        "sysmlv2_client", reason="install the Open-MBEE sysmlv2-python-client (roadmap T9)"
    )
    client = _make_client(sysmlv2_client)
    projects = client.get_projects()
    assert isinstance(projects, list)


# ---------------------------------------------------------------------------
# T9 milestone 2: corpus — live project contains Usage-level elements
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not all(_creds()), reason="FLEXO_SYSMLV2_* not set (see .env.example)")
def test_t9_corpus_contains_usage_elements() -> None:
    """A live Starforge project has PartUsage / RequirementUsage elements."""
    sysmlv2_client = pytest.importorskip(
        "sysmlv2_client", reason="install the Open-MBEE sysmlv2-python-client (roadmap T9)"
    )
    client = _make_client(sysmlv2_client)
    _pid, _cid, elements = _first_project_with_elements(client)

    usage_types = {"PartUsage", "RequirementUsage", "UseCaseUsage", "AttributeUsage"}
    usages = [e for e in elements if e.get("@type", "") in usage_types]
    assert usages, (
        f"Expected at least one Usage-level element in the live project; "
        f"found types: {sorted({e.get('@type','?') for e in elements})}"
    )


# ---------------------------------------------------------------------------
# T9 milestone 3: Definition→Usage bridge via live owning-definition link
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not all(_creds()), reason="FLEXO_SYSMLV2_* not set (see .env.example)")
def test_t9_definition_usage_bridge_via_live_typing() -> None:
    """Prove the 3-hop bridge: PartUsage → owning PartDefinition → cds:system-of-interest.

    Mirrors the offline gap from test_sysml_join but closes it with live Starforge data.

    Two legs:
      leg 1: def_iri rdf:type PartDefinition  →  joins cds:system-of-interest directly
      leg 2: usage_iri omg:type def_iri        →  joins via the 2-hop _BRIDGE_JOIN query
    """
    sysmlv2_client = pytest.importorskip(
        "sysmlv2_client", reason="install the Open-MBEE sysmlv2-python-client (roadmap T9)"
    )
    client = _make_client(sysmlv2_client)
    pid, cid, elements = _first_project_with_elements(client)

    # find a PartUsage that declares its owning definition
    part_usages = [
        e
        for e in elements
        if e.get("@type") == "PartUsage" and e.get("owningDefinition")
    ]
    if not part_usages:
        pytest.skip("No PartUsage with owningDefinition found in live project")

    usage_elem = part_usages[0]
    usage_id: str = usage_elem["@id"]
    def_id: str = usage_elem["owningDefinition"]["@id"]

    # fetch the owning definition and confirm it is a PartDefinition
    def_elem = client.get_element(pid, def_id, cid)
    assert def_elem.get("@type") == "PartDefinition", (
        f"Expected owningDefinition to be a PartDefinition; got {def_elem.get('@type')}"
    )

    # construct stable IRIs for the live elements
    def_iri = URIRef(f"urn:sysmlv2:{def_id}")
    usage_iri = URIRef(f"urn:sysmlv2:{usage_id}")

    g = build_concept_definition_graph()

    # --- leg 1: definition-level element joins cds directly (same path as the offline test) ---
    g.add((def_iri, RDF.type, OMG_SYSML.PartDefinition))
    # also add the OMG stub so the equivalence axiom resolves (mirrors sysml_anchor_graph())
    g.add((OMG_SYSML.PartDefinition, RDF.type, OWL.Class))
    direct_results = _join_pairs(g.query(_JOIN))
    assert (str(CDS_TERM["system-of-interest"]), str(def_iri)) in direct_results, (
        "cds:system-of-interest should join the live PartDefinition element via owl:equivalentClass"
    )

    # --- gap confirmation: usage alone does not join (mirrors offline test) ---
    g.add((usage_iri, RDF.type, OMG_SYSML.PartUsage))
    usage_models = {model for _term, model in _join_pairs(g.query(_JOIN))}
    assert str(usage_iri) not in usage_models, (
        "PartUsage should not directly match the PartDefinition anchor (Definition-vs-Usage gap)"
    )

    # --- leg 2: add the typing link and prove the 2-hop bridge resolves ---
    g.add((usage_iri, OMG_SYSML.type, def_iri))
    bridge_results = _join_pairs(g.query(_BRIDGE_JOIN))
    assert (str(CDS_TERM["system-of-interest"]), str(usage_iri)) in bridge_results, (
        "cds:system-of-interest should be reachable from the live PartUsage via the 2-hop bridge "
        "(usage --[omg:type]--> def --[rdf:type]--> PartDefinition)"
    )
