"""SKOS reference-vocabulary Term: YAML source -> model -> deterministic SKOS+PROV RDF."""

from __future__ import annotations

from rdflib import RDF, Literal, URIRef

from cds.core.model.term import (
    GroundingRelation,
    Term,
    load_term,
    term_iri,
    term_to_graph,
)
from cds.core.namespaces import CDS, SKOS
from cds.core.serialize import canonical_turtle

# A synthetic term (not real SEBoK NC text) — exercises the mechanics only.
_YAML = """
slug: system-of-interest
pref_label: System-of-Interest
alt_labels: [SoI]
grounding:
  - relation: exact-match
    target: https://sebokwiki.org/wiki/System-of-Interest_(glossary)
cites: [https://w3id.org/cds/src/sebok-soi]
sysml_construct: https://www.omg.org/spec/SysML/#PartDefinition
"""

_SCHEME = URIRef("https://w3id.org/cds/scheme/concept-definition")
_PREFIXES = {"cds": str(CDS), "skos": str(SKOS), "rdf": str(RDF)}
_SEBOK_SOI = URIRef("https://sebokwiki.org/wiki/System-of-Interest_(glossary)")


def test_load_term_from_yaml() -> None:
    t = load_term(_YAML)
    assert isinstance(t, Term)
    assert t.slug == "system-of-interest"
    assert t.pref_label == "System-of-Interest"
    assert t.alt_labels == ["SoI"]
    assert t.grounding[0].relation is GroundingRelation.EXACT_MATCH


def test_term_to_graph_emits_a_grounded_skos_concept() -> None:
    t = load_term(_YAML)
    g = term_to_graph(t, scheme=_SCHEME)
    s = term_iri(t.slug)
    assert (s, RDF.type, SKOS.Concept) in g
    assert (s, SKOS.inScheme, _SCHEME) in g
    assert (s, SKOS.prefLabel, Literal("System-of-Interest")) in g
    assert (s, SKOS.altLabel, Literal("SoI")) in g
    # grounding -> skos:exactMatch the existing SEBoK concept (no bare term)
    assert (s, SKOS.exactMatch, _SEBOK_SOI) in g
    # cites -> the boundary object; sysml structural anchor
    assert (s, CDS.cites, URIRef("https://w3id.org/cds/src/sebok-soi")) in g
    assert (s, CDS.sysmlConstruct, URIRef("https://www.omg.org/spec/SysML/#PartDefinition")) in g


def test_term_serialization_is_byte_deterministic() -> None:
    out1 = canonical_turtle(term_to_graph(load_term(_YAML), scheme=_SCHEME), prefixes=_PREFIXES)
    out2 = canonical_turtle(term_to_graph(load_term(_YAML), scheme=_SCHEME), prefixes=_PREFIXES)
    assert out1 == out2
