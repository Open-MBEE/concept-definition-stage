"""ASoT models -> RDF (PROV-O) emission."""

from __future__ import annotations

from datetime import UTC, datetime

from rdflib import RDF, RDFS, Literal, URIRef

from cds.core.asot.models import (
    Authority,
    AuthorityKind,
    CaptureTier,
    Source,
    SourceType,
    Synthesis,
)
from cds.core.asot.rdf import to_graph
from cds.core.controlled import controlled_concept, controlled_vocab_graph
from cds.core.namespaces import CDS, PROV, SKOS

_T = datetime(2026, 6, 27, 17, 22, tzinfo=UTC)

_AUTH = Authority(
    id="https://w3id.org/cds/auth/sebok", kind=AuthorityKind.CURATED_CANON, label="SEBoK"
)
_SRC = Source(
    id="https://w3id.org/cds/src/sebok-soi",
    from_authority=_AUTH.id,
    locator="https://sebokwiki.org/wiki/System-of-Interest_(glossary)",
    source_type=SourceType.WEB_PAGE,
    tier=CaptureTier.REFERENCE,
    content_hash="sha256:abc",
    retrieved_at=_T,
)


def test_authority_is_a_prov_agent_with_label() -> None:
    g = to_graph(authorities=[_AUTH])
    s = URIRef(_AUTH.id)
    assert (s, RDF.type, PROV.Agent) in g
    assert (s, RDFS.label, Literal("SEBoK")) in g
    # control vocab is grounded as a SKOS concept, not a bare Literal
    assert (s, CDS.authorityKind, controlled_concept(AuthorityKind.CURATED_CANON)) in g


def test_source_is_a_prov_entity_bound_to_its_authority() -> None:
    g = to_graph(sources=[_SRC])
    s = URIRef(_SRC.id)
    assert (s, RDF.type, PROV.Entity) in g
    assert (s, CDS.fromAuthority, URIRef(_AUTH.id)) in g
    assert (s, CDS.contentHash, Literal("sha256:abc")) in g
    # retrievedAt is a typed xsd:dateTime
    assert (s, CDS.retrievedAt, Literal(_T)) in g
    # sourceType is a grounded SKOS concept too
    assert (s, CDS.sourceType, controlled_concept(SourceType.WEB_PAGE)) in g


def test_controlled_vocab_defines_concepts_in_named_schemes() -> None:
    g = controlled_vocab_graph()
    concept = controlled_concept(AuthorityKind.CURATED_CANON)
    assert (concept, RDF.type, SKOS.Concept) in g
    assert (concept, SKOS.prefLabel, Literal("curated-canon")) in g
    assert (concept, SKOS.inScheme, CDS["AuthorityKind"]) in g
    assert (CDS["AuthorityKind"], RDF.type, SKOS.ConceptScheme) in g


def test_synthesis_was_derived_from_each_source() -> None:
    syn = Synthesis(
        id="https://w3id.org/cds/scheme/concept-definition",
        derived_from=[_SRC.id],
        generated_at=_T,
    )
    g = to_graph(synthesis=syn)
    s = URIRef(syn.id)
    assert (s, RDF.type, PROV.Entity) in g
    assert (s, PROV.wasDerivedFrom, URIRef(_SRC.id)) in g
