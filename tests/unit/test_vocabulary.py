"""Slice 5 — the cds-core vocabulary: class/property declarations + a code<->vocab drift guard.

`cds-core.ttl` is a *generated, committed* artifact: Python (this module + the emitters) is the
single source of truth, the Turtle is the build output. Two guards keep them honest — a determinism
check (regeneration is byte-identical to the committed file) and a drift check (every `cds:` term
the emitters actually produce is declared in the core vocabulary).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, URIRef

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
from cds.core.asot.rdf import to_graph
from cds.core.controlled import controlled_vocab_graph
from cds.core.licenses import GTWR_LICENSE, CodeLicense, TextLicense, custom_license_graph
from cds.core.model.lifecycle import LifecycleModel, lifecycle_to_graph
from cds.core.model.term import Term, term_to_graph
from cds.core.namespaces import CDS, PROV, SKOS
from cds.core.serialize import canonical_turtle
from cds.core.verify import Waiver, waiver_to_graph
from cds.core.vocabulary import (
    CORE_PREFIXES,
    CORE_TTL_PATH,
    core_vocab_graph,
    required_terms,
)

_T = datetime(2026, 6, 27, tzinfo=UTC)
_SCHEME = URIRef("https://w3id.org/cds/scheme/concept-definition")


def test_core_declares_the_used_as_types_classes_with_their_parents() -> None:
    g = core_vocab_graph()
    assert (CDS.Authority, RDFS.subClassOf, PROV.Agent) in g
    assert (CDS.Source, RDFS.subClassOf, PROV.Entity) in g
    assert (CDS.Term, RDFS.subClassOf, SKOS.Concept) in g
    assert (CDS.RetrievalActivity, RDFS.subClassOf, PROV.Activity) in g


def test_core_includes_the_controlled_vocab_schemes() -> None:
    g = core_vocab_graph()
    assert (CDS["AuthorityKind"], RDF.type, SKOS.ConceptScheme) in g


def test_cds_core_ttl_is_the_committed_generation() -> None:
    # the committed artifact must equal a fresh deterministic generation (no hand-edits, no drift)
    generated = canonical_turtle(core_vocab_graph(), prefixes=CORE_PREFIXES)
    assert Path(CORE_TTL_PATH).read_text() == generated


def _emitted_cds_terms() -> set[URIRef]:
    """Every cds: predicate / rdf:type-object the emitters actually produce."""
    auth = Authority(id="https://w3id.org/cds/auth/a", kind=AuthorityKind.STANDARD, label="A")
    verified = Source(
        id="https://w3id.org/cds/src/v",
        from_authority=auth.id,
        locator="L",
        source_type=SourceType.PDF,
        tier=CaptureTier.SNAPSHOT,
        content_hash="sha256:a",
        snapshot="a.pdf",
        license="CC-BY-4.0",
        retrieved_at=_T,
        retrieval_status=RetrievalStatus.VERIFIED,
        verifications=[Verification(method=VerificationMethod.CHECKSUM, verified_at=_T, note="n")],
    )
    pending = Source(
        id="https://w3id.org/cds/src/p",
        from_authority=auth.id,
        locator="L2",
        source_type=SourceType.WEB_PAGE,
        tier=CaptureTier.REFERENCE,
        retrieval_status=RetrievalStatus.PENDING,
        retrieval_issue="https://example.org/issues/1",
    )
    term = Term(
        slug="t",
        pref_label="T",
        alt_labels=["t"],
        definition="D",
        grounding=[],
        cites=["https://w3id.org/cds/src/v"],
        broader=[],
        sysml_construct="https://www.omg.org/spec/SysML/#PartDefinition",
        nrm_note="note",
    )
    lifecycle = LifecycleModel(
        id="https://w3id.org/cds/self",
        label="cds",
        stage="concept-definition",
        code_license=CodeLicense.APACHE_2_0,
        text_license=TextLicense.CC_BY_NC_SA,
    )
    waiver = Waiver(
        id="https://w3id.org/cds/waiver/1",
        rule="SourceLicense",
        reason="r",
        focus="https://w3id.org/cds/src/p",
        by="https://w3id.org/cds/auth/operator",
        waived_on=date(2026, 6, 27),
    )

    g = to_graph(authorities=[auth], sources=[verified, pending])
    g += term_to_graph(term, scheme=_SCHEME)
    g += lifecycle_to_graph(lifecycle)
    g += custom_license_graph(GTWR_LICENSE)
    g += waiver_to_graph(waiver)
    g += controlled_vocab_graph()

    prefix = str(CDS)
    used: set[URIRef] = set()
    for _s, p, o in g:
        if isinstance(p, URIRef) and str(p).startswith(prefix):
            used.add(p)
        if p == RDF.type and isinstance(o, URIRef) and str(o).startswith(prefix):
            used.add(o)
    return used


def test_no_emitted_cds_term_is_undeclared_in_core() -> None:
    # availability: nothing the emitters produce may be undeclared in the core vocabulary
    declared = {s for s in core_vocab_graph().subjects() if isinstance(s, URIRef)}
    missing = _emitted_cds_terms() - declared
    assert missing == set(), f"cds: terms used by emitters but undeclared in core: {missing}"


def test_required_terms_are_actually_emitted_by_the_framework() -> None:
    # compliance: the necessary terms are not dead — a maximal model exercises every one of them.
    # (Distinct from availability: AVAILABLE terms may legitimately be absent from a given model.)
    missing = required_terms() - _emitted_cds_terms()
    assert missing == set(), f"cds:Required terms never emitted by any emitter: {missing}"


def test_every_property_declares_a_domain_and_data_props_a_range() -> None:
    g = core_vocab_graph()
    object_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    data_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))
    for p in object_props | data_props:
        assert (p, RDFS.domain, None) in g, f"{p} has no rdfs:domain"
    for p in data_props:
        assert (p, RDFS.range, None) in g, f"{p} has no rdfs:range"
    # a spot check of the discipline
    assert (CDS.cites, RDFS.domain, CDS.Term) in g
    assert (CDS.cites, RDFS.range, CDS.Source) in g
    assert (CDS.locator, RDFS.range, XSD.string) in g


def test_every_class_and_property_carries_a_framework_role() -> None:
    g = core_vocab_graph()
    typed = (
        set(g.subjects(RDF.type, OWL.Class))
        | set(g.subjects(RDF.type, OWL.ObjectProperty))
        | set(g.subjects(RDF.type, OWL.DatatypeProperty))
    )
    for t in typed:
        assert (t, CDS.frameworkRole, None) in g, f"{t} has no cds:frameworkRole"
    # the role itself is a typed SKOS distinction, not a bare literal
    assert (CDS.Required, RDF.type, SKOS.Concept) in g
