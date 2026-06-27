"""Emit ASoT models as RDF (PROV-O grounded).

The provenance is structured so **Activity attributes and Entity attributes are distinct**:

* a ``Source`` is a ``prov:Entity`` carrying only *what it is* — locator, type, tier, content
  hash, snapshot — and ``prov:wasAttributedTo`` its authority;
* the *act* of retrieving/verifying it is a distinct ``prov:Activity`` carrying *when/what
  state* — ``prov:endedAtTime`` (retrieved), verified-at, retrieval status;
* the union is ``source prov:wasGeneratedBy <retrieval-activity>``.

``cds:Synthesis`` is **reserved** for the concept-definition artifact (the integrated set of
needs) and is introduced in v0.2; the v0.1 vocabulary is a provenance-tracked concept scheme,
not a synthesis. The deterministic Turtle serialization of this graph is handled separately.
"""

from __future__ import annotations

from collections.abc import Iterable

from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.asot.models import Authority, Source
from cds.core.licenses import license_iri
from cds.core.namespaces import CDS, PROV


def retrieval_activity_iri(source: Source) -> URIRef:
    """The IRI of the retrieval (capture) activity that generated a source record."""
    return URIRef(f"{source.id}/retrieval")


def verification_activity_iri(source: Source, index: int) -> URIRef:
    """The IRI of the ``index``-th verification activity over a source.

    Verifications are separate acts from the retrieval: an older retrieval can be re-verified
    (a new verification activity) without re-capturing.
    """
    return URIRef(f"{source.id}/verification/{index}")


def to_graph(
    *,
    authorities: Iterable[Authority] | None = None,
    sources: Iterable[Source] | None = None,
) -> Graph:
    """Build an in-memory graph from ASoT models.

    Control-vocab values are emitted as grounded SKOS concept IRIs (see ``controlled``).
    """
    from cds.core.controlled import controlled_concept  # local: avoids an import cycle

    g = Graph()
    g.bind("cds", CDS)
    g.bind("prov", PROV)

    for a in authorities or []:
        s = URIRef(a.id)
        g.add((s, RDF.type, PROV.Agent))
        g.add((s, RDFS.label, Literal(a.label)))
        g.add((s, CDS.authorityKind, controlled_concept(a.kind)))

    for src in sources or []:
        s = URIRef(src.id)
        # --- entity: what the source IS ---
        g.add((s, RDF.type, PROV.Entity))
        g.add((s, PROV.wasAttributedTo, URIRef(src.from_authority)))
        g.add((s, CDS.locator, Literal(src.locator)))
        g.add((s, CDS.sourceType, controlled_concept(src.source_type)))
        g.add((s, CDS.captureTier, controlled_concept(src.tier)))
        if src.content_hash is not None:
            g.add((s, CDS.contentHash, Literal(src.content_hash)))
        if src.snapshot is not None:
            g.add((s, CDS.snapshot, Literal(src.snapshot)))
        if src.license is not None:
            g.add((s, CDS.license, license_iri(src.license)))

        # --- activity: the ACT of retrieving (capturing) it ---
        act = retrieval_activity_iri(src)
        g.add((s, PROV.wasGeneratedBy, act))
        g.add((act, RDF.type, PROV.Activity))
        g.add((act, RDF.type, CDS.RetrievalActivity))
        g.add((act, CDS.retrievalStatus, controlled_concept(src.retrieval_status)))
        if src.retrieved_at is not None:
            g.add((act, PROV.endedAtTime, Literal(src.retrieved_at)))
        if src.retrieval_issue is not None:
            g.add((act, CDS.retrievalIssue, Literal(src.retrieval_issue)))

        # --- activities: each verification is its own act, recording method + note ---
        for index, ver in enumerate(src.verifications):
            vact = verification_activity_iri(src, index)
            g.add((vact, RDF.type, PROV.Activity))
            g.add((vact, RDF.type, CDS.VerificationActivity))
            g.add((vact, PROV.used, s))
            g.add((s, CDS.wasVerifiedBy, vact))
            g.add((vact, PROV.endedAtTime, Literal(ver.verified_at)))
            g.add((vact, CDS.verificationMethod, controlled_concept(ver.method)))
            if ver.note is not None:
                g.add((vact, CDS.verificationNote, Literal(ver.note)))
            if ver.by is not None:
                g.add((vact, PROV.wasAssociatedWith, URIRef(ver.by)))

    return g
