"""ASoT models -> RDF (PROV-O) emission."""

from __future__ import annotations

from datetime import UTC, datetime

from rdflib import RDF, RDFS, Literal, URIRef

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
from cds.core.asot.rdf import (
    retrieval_activity_iri,
    to_graph,
    verification_activity_iri,
)
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


def test_source_entity_carries_only_entity_attributes() -> None:
    g = to_graph(sources=[_SRC])
    s = URIRef(_SRC.id)
    # entity = what the source IS
    assert (s, RDF.type, PROV.Entity) in g
    assert (s, PROV.wasAttributedTo, URIRef(_AUTH.id)) in g
    assert (s, CDS.contentHash, Literal("sha256:abc")) in g
    assert (s, CDS.sourceType, controlled_concept(SourceType.WEB_PAGE)) in g
    # activity attributes do NOT live on the entity
    assert (s, CDS.retrievedAt, Literal(_T)) not in g
    assert s not in {x for (x, p, _o) in g if p == PROV.endedAtTime}


def test_retrieval_is_a_distinct_activity_with_the_act_attributes() -> None:
    g = to_graph(sources=[_SRC])
    s = URIRef(_SRC.id)
    act = retrieval_activity_iri(_SRC)
    # union: the source entity wasGeneratedBy the retrieval activity
    assert (s, PROV.wasGeneratedBy, act) in g
    assert (act, RDF.type, PROV.Activity) in g
    assert (act, RDF.type, CDS.RetrievalActivity) in g
    # the act = when/what-state, distinct from the entity's content attributes
    assert (act, PROV.endedAtTime, Literal(_T)) in g
    assert (act, CDS.retrievalStatus, controlled_concept(_SRC.retrieval_status)) in g


_VSRC = Source(
    id="https://w3id.org/cds/src/gtwr",
    from_authority=_AUTH.id,
    locator="INCOSE-TP-2010-006-04",
    source_type=SourceType.PDF,
    tier=CaptureTier.SNAPSHOT,
    content_hash="sha256:deadbeef",
    snapshot="deadbeef.pdf",
    retrieved_at=_T,
    retrieval_status=RetrievalStatus.VERIFIED,
    verifications=[
        Verification(method=VerificationMethod.CHECKSUM, verified_at=_T, note="sha256 match")
    ],
)


def test_verification_is_a_separate_activity_recording_method_and_note() -> None:
    g = to_graph(sources=[_VSRC])
    s = URIRef(_VSRC.id)
    vact = verification_activity_iri(_VSRC, 0)
    assert (vact, RDF.type, PROV.Activity) in g
    assert (vact, RDF.type, CDS.VerificationActivity) in g
    assert (vact, PROV.used, s) in g  # the verification used (checked) the source
    assert (vact, PROV.endedAtTime, Literal(_T)) in g
    assert (vact, CDS.verificationMethod, controlled_concept(VerificationMethod.CHECKSUM)) in g
    assert (vact, CDS.verificationNote, Literal("sha256 match")) in g
    # the retrieval activity is distinct and does not carry verification attributes
    ract = retrieval_activity_iri(_VSRC)
    assert ract != vact
    assert (ract, CDS.verificationMethod, controlled_concept(VerificationMethod.CHECKSUM)) not in g


def test_controlled_vocab_defines_concepts_in_named_schemes() -> None:
    g = controlled_vocab_graph()
    concept = controlled_concept(AuthorityKind.CURATED_CANON)
    assert (concept, RDF.type, SKOS.Concept) in g
    assert (concept, SKOS.prefLabel, Literal("curated-canon")) in g
    assert (concept, SKOS.inScheme, CDS["AuthorityKind"]) in g
    assert (CDS["AuthorityKind"], RDF.type, SKOS.ConceptScheme) in g


