"""Canonical, byte-deterministic Turtle serialization.

Our graphs have no blank nodes (every node is a minted IRI), so a fully-sorted writer is a
sufficient canonical form — same triples in, byte-identical Turtle out, regardless of
insertion order.
"""

from __future__ import annotations

from typing import Any

from rdflib import RDF, Graph, Literal, URIRef

from cds.core.namespaces import CDS, SKOS
from cds.core.serialize import canonical_turtle

_PREFIXES = {"cds": str(CDS), "skos": str(SKOS), "rdf": str(RDF)}

_TRIPLES: list[tuple[Any, Any, Any]] = [
    (URIRef("https://w3id.org/cds/term/b"), RDF.type, SKOS.Concept),
    (URIRef("https://w3id.org/cds/term/a"), RDF.type, SKOS.Concept),
    (URIRef("https://w3id.org/cds/term/a"), SKOS.prefLabel, Literal("Alpha")),
    (URIRef("https://w3id.org/cds/term/a"), SKOS.altLabel, Literal("A")),
]


def _graph(triples: list[tuple[Any, Any, Any]]) -> Graph:
    g = Graph()
    for t in triples:
        g.add(t)
    return g


def test_canonical_turtle_is_independent_of_insertion_order() -> None:
    out1 = canonical_turtle(_graph(_TRIPLES), prefixes=_PREFIXES)
    out2 = canonical_turtle(_graph(list(reversed(_TRIPLES))), prefixes=_PREFIXES)
    assert out1 == out2


def test_canonical_turtle_is_stable_across_calls() -> None:
    g = _graph(_TRIPLES)
    assert canonical_turtle(g, prefixes=_PREFIXES) == canonical_turtle(g, prefixes=_PREFIXES)


def test_canonical_turtle_sorts_subjects_and_uses_a_for_rdf_type() -> None:
    out = canonical_turtle(_graph(_TRIPLES), prefixes=_PREFIXES)
    assert out.startswith("@prefix")
    assert out.index("term/a") < out.index("term/b")  # subjects sorted
    assert "    a skos:Concept" in out  # rdf:type rendered as `a`, prefixed objects
