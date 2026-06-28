"""Slice 5 — usage-driven MIREOT extracts + the per-source parsimony budget.

Reference is cheap (one anchor triple, always allowed); *materializing* an external term's local
description is a separate, budgeted step done only for invoked IRIs we actually hold a source for.
Slices are minimal (label + one definition + optional DIRECT parent) — never the supertype closure.

The real external sources (the SysML v2 OWL cache, PROV-O, SKOS) arrive with slice 7; here the
engine runs against a small fixture source, and with no source an invoked IRI stays reference-only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import RDFS, Graph, Literal, URIRef

from cds.core.model.term import Term, term_to_graph
from cds.core.namespaces import SKOS
from cds.core.parsimony import build_extracts, invoked_external_iris, mireot_slice

_SYSML_NS = "https://www.omg.org/spec/SysML/#"

_SCHEME = URIRef("https://w3id.org/cds/scheme/concept-definition")
_EXT = "https://ext.example/onto#"
_THING = URIRef(f"{_EXT}Thing")
_PARENT = URIRef(f"{_EXT}Parent")
_GRANDPARENT = URIRef(f"{_EXT}Grandparent")
_SYSML = "https://www.omg.org/spec/SysML/#PartDefinition"


def _source() -> Graph:
    g = Graph()
    g.add((_THING, SKOS.prefLabel, Literal("Thing")))
    g.add((_THING, SKOS.definition, Literal("A thing.")))
    g.add((_THING, RDFS.subClassOf, _PARENT))
    g.add((_THING, URIRef(f"{_EXT}colour"), Literal("blue")))  # an extra triple — NOT sliced
    g.add((_PARENT, SKOS.prefLabel, Literal("Parent")))  # parent's own triples — NOT sliced
    g.add((_PARENT, RDFS.subClassOf, _GRANDPARENT))  # the closure — must NOT be dragged in
    return g


def _term_graph() -> Graph:
    # a term anchored to one external concept + one SysML construct; broader is internal
    term = Term(
        slug="t",
        pref_label="T",
        grounding=[{"relation": "exact-match", "target": str(_THING)}],  # type: ignore[list-item]
        cites=["https://w3id.org/cds/src/x"],
        broader=["other"],
        sysml_construct=_SYSML,
    )
    return term_to_graph(term, scheme=_SCHEME)


def test_invoked_external_iris_collects_anchors_and_skips_internal() -> None:
    invoked = invoked_external_iris(_term_graph())
    assert _THING in invoked
    assert URIRef(_SYSML) in invoked
    # broader -> an internal cds term, and cites -> an internal source, are not external anchors
    assert all(not str(i).startswith("https://w3id.org/cds") for i in invoked)


def test_mireot_slice_is_minimal_with_no_supertype_closure() -> None:
    s0 = mireot_slice(_THING, _source(), depth=0)
    assert (_THING, SKOS.prefLabel, Literal("Thing")) in s0
    assert (_THING, SKOS.definition, Literal("A thing.")) in s0
    assert (_THING, RDFS.subClassOf, _PARENT) not in s0  # depth 0 = reference-only parent
    assert (_THING, URIRef(f"{_EXT}colour"), Literal("blue")) not in s0  # no stray triples

    s1 = mireot_slice(_THING, _source(), depth=1)
    assert (_THING, RDFS.subClassOf, _PARENT) in s1  # the DIRECT parent only
    assert (_PARENT, RDFS.subClassOf, _GRANDPARENT) not in s1  # never the closure
    assert (_PARENT, SKOS.prefLabel, Literal("Parent")) not in s1


def test_build_extracts_materializes_invoked_and_reports_referenced_only() -> None:
    extracts, report = build_extracts(
        _term_graph(), sources={_EXT: _source()}, budgets={_EXT: 10}
    )
    assert (_THING, SKOS.prefLabel, Literal("Thing")) in extracts  # the held one is materialized
    assert str(_THING) in report.materialized_iris
    assert _SYSML in report.referenced_only  # no SysML cache here -> reference-only
    assert report.triples_per_source[_EXT] > 0
    assert report.within_budget


def test_parsimony_budget_overflow_is_flagged() -> None:
    _extracts, report = build_extracts(
        _term_graph(), sources={_EXT: _source()}, budgets={_EXT: 1}  # too tight for the slice
    )
    assert _EXT in report.over_budget
    assert not report.within_budget


@pytest.mark.xfail(reason="real SysML v2 OWL cache is populated in slice 7", strict=False)
def test_sysml_construct_materializes_from_the_real_cache() -> None:
    # EXPECTED FAILURE until slice 7: the cache dir exists but is empty, so the invoked SysML
    # construct stays reference-only. Populating ontology/cache/sysml-v2/ flips this green.
    cache_dir = Path(__file__).resolve().parents[2] / "ontology" / "cache" / "sysml-v2"
    source = Graph()
    for ttl in sorted(cache_dir.glob("*.ttl")):
        source.parse(ttl)
    _extracts, report = build_extracts(
        _term_graph(), sources={_SYSML_NS: source}, budgets={_SYSML_NS: 50}
    )
    assert _SYSML in report.materialized_iris
