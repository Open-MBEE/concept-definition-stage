"""The self-model fixture — cds modeling its own Concept Definition (the primary dogfood).

Per the plan's DoD, cds applies its own model to itself: its sponsor (a `cds:Authority`) and its
mission (a grounded `cds:Term` from a verified source). It exercises the full
construction order — authority registered, source secured + verified, verbatim attached, concept
cited + grounded + admitted to a scheme, renderable — on real (non-toy) content.

The mission text is cds's own authored content (not third-party canon), held as a `NOTES`/reference
boundary object and verified by checksum, so the hallucination guard still binds structurally. The
mission concept has no SEBoK glossary entry, so it grounds by `relatedMatch` to Concept Definition,
carrying its own first-class `cds:Waiver` — so the fixture is self-contained and verifies clean.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.asot.hashing import content_hash
from cds.core.asot.models import (
    Authority,
    AuthorityKind,
    CaptureTier,
    RetrievalStatus,
    Source,
    SourceType,
    Verification,
    VerificationMethod,
)
from cds.core.asot.rdf import to_graph as asot_to_graph
from cds.core.licenses import CodeLicense
from cds.core.model.term import Term, term_iri, term_to_graph
from cds.core.namespaces import CDS, DCTERMS, PROV, SKOS
from cds.core.verify import Waiver, waiver_to_graph

_AUTHORED_AT = datetime(2026, 6, 28, tzinfo=UTC)

# cds's own mission statement (authored content — the self-model's verbatim, from the plan/README).
CDS_MISSION = (
    "cds standardizes the System Concept Definition stage by committing SEBoK and INCOSE canon to "
    "version-controlled RDF — INCOSE/SE-compatible and SysML v2-traceable, audited and canonically "
    "sourced, and procedurally sound through structural (SHACL) checks."
)

SELF_SCHEME = URIRef("https://w3id.org/cds/self/scheme")

DSG_SPONSOR = Authority(
    id="https://w3id.org/cds/self/auth/dsg",
    kind=AuthorityKind.SPONSOR,
    label="DSG (cds sponsor)",
)

MISSION_SOURCE = Source(
    id="https://w3id.org/cds/self/src/mission",
    from_authority=DSG_SPONSOR.id,
    locator="https://github.com/Open-MBEE/cds — README + design plan",
    source_type=SourceType.NOTES,
    tier=CaptureTier.REFERENCE,
    content_hash=content_hash(CDS_MISSION),
    license=CodeLicense.APACHE_2_0,  # cds's own content
    retrieved_at=_AUTHORED_AT,
    retrieval_status=RetrievalStatus.VERIFIED,
    verifications=[
        Verification(
            method=VerificationMethod.CHECKSUM,
            verified_at=_AUTHORED_AT,
            note="self-authored cds mission statement; checksum over the committed text",
        )
    ],
)

_CD_GLOSSARY = "https://sebokwiki.org/wiki/Concept_Definition_(glossary)"
_MISSION_TERM = Term(
    slug="cds-mission",
    pref_label="cds mission",
    definition=CDS_MISSION,
    grounding=[{"relation": "related-match", "target": _CD_GLOSSARY}],  # type: ignore[list-item]
    cites=[MISSION_SOURCE.id],
)

_SELF_WAIVER = Waiver(
    id="https://w3id.org/cds/self/waiver/0001",
    rule="TermRelatedOnlyShape",
    focus=str(term_iri("cds-mission")),
    reason="cds's own mission has no SEBoK glossary concept; relatedMatch to Concept Definition.",
    by=DSG_SPONSOR.id,
)


def self_model_graph() -> Graph:
    """Assemble the self-model graph: sponsor + verified source + scheme + grounded mission term."""
    g = asot_to_graph(authorities=[DSG_SPONSOR], sources=[MISSION_SOURCE])
    g.add((SELF_SCHEME, RDF.type, SKOS.ConceptScheme))
    g.add((SELF_SCHEME, RDFS.label, Literal("cds self-model")))
    g.add((SELF_SCHEME, DCTERMS.title, Literal("cds modeling its own Concept Definition")))
    g.add((SELF_SCHEME, PROV.wasDerivedFrom, URIRef(MISSION_SOURCE.id)))
    g += term_to_graph(_MISSION_TERM, scheme=SELF_SCHEME)
    g += waiver_to_graph(_SELF_WAIVER)  # the self-model carries its own waiver (first-class)
    _ = CDS  # namespace kept bound for downstream consumers
    return g
