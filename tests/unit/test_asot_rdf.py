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
from cds.core.namespaces import CDS, PROV

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
    assert (s, CDS.authorityKind, Literal("curated-canon")) in g


def test_source_is_a_prov_entity_bound_to_its_authority() -> None:
    g = to_graph(sources=[_SRC])
    s = URIRef(_SRC.id)
    assert (s, RDF.type, PROV.Entity) in g
    assert (s, CDS.fromAuthority, URIRef(_AUTH.id)) in g
    assert (s, CDS.contentHash, Literal("sha256:abc")) in g
    # retrievedAt is a typed xsd:dateTime
    assert (s, CDS.retrievedAt, Literal(_T)) in g


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
