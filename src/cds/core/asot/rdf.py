"""Emit ASoT models as RDF (PROV-O grounded).

Authorities are ``prov:Agent``; sources and the synthesis are ``prov:Entity``; the synthesis
``prov:wasDerivedFrom`` its cited sources. The *deterministic* Turtle serialization of this
graph is handled separately (the canonical sorted-Turtle writer); here we only build triples.
"""

from __future__ import annotations

from collections.abc import Iterable

from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.asot.models import Authority, Source, Synthesis
from cds.core.namespaces import CDS, PROV


def to_graph(
    *,
    authorities: Iterable[Authority] | None = None,
    sources: Iterable[Source] | None = None,
    synthesis: Synthesis | None = None,
) -> Graph:
    """Build an in-memory graph from ASoT models."""
    g = Graph()
    g.bind("cds", CDS)
    g.bind("prov", PROV)

    for a in authorities or []:
        s = URIRef(a.id)
        g.add((s, RDF.type, PROV.Agent))
        g.add((s, RDFS.label, Literal(a.label)))
        g.add((s, CDS.authorityKind, Literal(str(a.kind))))

    for src in sources or []:
        s = URIRef(src.id)
        g.add((s, RDF.type, PROV.Entity))
        g.add((s, CDS.fromAuthority, URIRef(src.from_authority)))
        g.add((s, CDS.locator, Literal(src.locator)))
        g.add((s, CDS.sourceType, Literal(str(src.source_type))))
        g.add((s, CDS.captureTier, Literal(str(src.tier))))
        g.add((s, CDS.retrievalStatus, Literal(str(src.retrieval_status))))
        if src.content_hash is not None:
            g.add((s, CDS.contentHash, Literal(src.content_hash)))
        if src.retrieved_at is not None:
            g.add((s, CDS.retrievedAt, Literal(src.retrieved_at)))
        if src.verified_at is not None:
            g.add((s, CDS.verifiedAt, Literal(src.verified_at)))
        if src.snapshot is not None:
            g.add((s, CDS.snapshot, Literal(src.snapshot)))

    if synthesis is not None:
        s = URIRef(synthesis.id)
        g.add((s, RDF.type, PROV.Entity))
        for derived in synthesis.derived_from:
            g.add((s, PROV.wasDerivedFrom, URIRef(derived)))
        if synthesis.generated_at is not None:
            g.add((s, PROV.generatedAtTime, Literal(synthesis.generated_at)))

    return g
