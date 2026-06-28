"""Slice 4 — tri-severity SHACL verify, construction-order preconditions, waivers.

The graphs here are built from the ASoT + term emitters (well-formed cases) or hand-assembled
(deliberately broken cases). All canon text is SYNTHETIC — never real SEBoK/INCOSE text.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rdflib import RDF, Graph, Literal, URIRef
from typer.testing import CliRunner

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
from cds.core.cli import app
from cds.core.model.term import Term, term_iri, term_to_graph
from cds.core.namespaces import CDS, PROV
from cds.core.verify import Severity, Waiver, verify

_T = datetime(2026, 6, 27, tzinfo=UTC)
_SCHEME = URIRef("https://w3id.org/cds/scheme/concept-definition")

_AUTH = Authority(
    id="https://w3id.org/cds/auth/sebok", kind=AuthorityKind.CURATED_CANON, label="SEBoK"
)


def _verified_source(sid: str = "https://w3id.org/cds/src/x") -> Source:
    return Source(
        id=sid,
        from_authority=_AUTH.id,
        locator="INCOSE-TP-2010-006-04",
        source_type=SourceType.PDF,
        tier=CaptureTier.SNAPSHOT,
        content_hash="sha256:abc",
        snapshot="abc.pdf",
        license="CC-BY-NC-SA-4.0",
        retrieved_at=_T,
        retrieval_status=RetrievalStatus.VERIFIED,
        verifications=[Verification(method=VerificationMethod.CHECKSUM, verified_at=_T)],
    )


def _pending_source(sid: str = "https://w3id.org/cds/src/p") -> Source:
    return Source(
        id=sid,
        from_authority=_AUTH.id,
        locator="https://example.org/page",
        source_type=SourceType.WEB_PAGE,
        tier=CaptureTier.REFERENCE,
        license="CC-BY-NC-SA-4.0",
        retrieval_status=RetrievalStatus.PENDING,
    )


def _term(**over: object) -> Term:
    base: dict[str, object] = {
        "slug": "stakeholder",
        "pref_label": "Stakeholder",
        "grounding": [{"relation": "exact-match", "target": "https://example.org/Stakeholder"}],
        "cites": ["https://w3id.org/cds/src/x"],
    }
    base.update(over)
    return Term.model_validate(base)


def _well_formed_graph() -> Graph:
    g = to_graph(authorities=[_AUTH], sources=[_verified_source()])
    g += term_to_graph(_term(definition="SYNTHETIC verified definition."), scheme=_SCHEME)
    return g


# --- the engine targets the right classes (slice-4 typing refinement) -----------------------


def test_emitters_type_boundary_objects_and_terms_for_shacl_targeting() -> None:
    g = _well_formed_graph()
    assert (URIRef(_AUTH.id), RDF.type, CDS.Authority) in g
    assert (URIRef("https://w3id.org/cds/src/x"), RDF.type, CDS.Source) in g
    assert (term_iri("stakeholder"), RDF.type, CDS.Term) in g
    # the prov typing is preserved (cds:Authority/Source are subclasses)
    assert (URIRef(_AUTH.id), RDF.type, PROV.Agent) in g


def test_well_formed_graph_passes_with_no_violations() -> None:
    result = verify(_well_formed_graph())
    assert result.passed
    assert result.violations == ()


# --- T1 boundary-object + construction-order preconditions ----------------------------------


def test_source_attributed_to_unregistered_authority_is_t1() -> None:
    # construction order: an authority must be registered (typed) before a source binds to it
    g = Graph()
    s = URIRef("https://w3id.org/cds/src/orphan")
    g.add((s, RDF.type, CDS.Source))
    g.add((s, PROV.wasAttributedTo, URIRef("https://w3id.org/cds/auth/ghost")))  # untyped
    g.add((s, CDS.locator, Literal("x")))
    g.add((s, CDS.sourceType, CDS["SourceType/pdf"]))
    g.add((s, CDS.captureTier, CDS["CaptureTier/reference"]))
    g.add((s, CDS.license, CDS["license/x"]))
    result = verify(g)
    assert not result.passed
    assert any(f.severity is Severity.VIOLATION for f in result.violations)


def test_defined_term_citing_an_unverified_source_is_t1_hallucination_guard() -> None:
    # the headline slice-4 check: a term's verbatim must trace to a VERIFIED source
    g = to_graph(authorities=[_AUTH], sources=[_pending_source("https://w3id.org/cds/src/p")])
    g += term_to_graph(
        _term(definition="SYNTHETIC text", cites=["https://w3id.org/cds/src/p"]),
        scheme=_SCHEME,
    )
    result = verify(g)
    assert not result.passed
    assert any("hallucination guard" in f.message.lower() for f in result.violations)


def test_term_without_grounding_is_t1() -> None:
    g = to_graph(authorities=[_AUTH], sources=[_verified_source()])
    g += term_to_graph(_term(grounding=[]), scheme=_SCHEME)
    result = verify(g)
    assert not result.passed
    assert any(f.shape_name == "TermGroundedShape" for f in result.violations)


def test_term_without_citation_is_t1() -> None:
    g = to_graph(authorities=[_AUTH], sources=[_verified_source()])
    g += term_to_graph(_term(cites=[]), scheme=_SCHEME)
    result = verify(g)
    assert not result.passed


# --- T2 / T3 (do not fail the build) --------------------------------------------------------


def test_source_without_license_is_a_t2_warning_not_a_violation() -> None:
    # licenses are tracked, not enforced — absence is auditability noise, not a violation
    src = _verified_source()
    g = to_graph(authorities=[_AUTH], sources=[src])
    g.remove((URIRef(src.id), CDS.license, None))
    g += term_to_graph(_term(definition="SYNTHETIC verified definition."), scheme=_SCHEME)
    result = verify(g)
    assert result.passed  # still passes — only a warning
    assert any(f.severity is Severity.WARNING for f in result.warnings)


def test_related_match_only_grounding_is_a_t2_warning() -> None:
    g = to_graph(authorities=[_AUTH], sources=[_verified_source()])
    related = [{"relation": "related-match", "target": "https://example.org/Vague"}]
    g += term_to_graph(
        _term(grounding=related, definition="SYNTHETIC verified definition."), scheme=_SCHEME
    )
    result = verify(g)
    assert result.passed
    assert any(f.shape_name == "TermRelatedOnlyShape" for f in result.warnings)


# --- waivers (append-only; T1 never waivable) -----------------------------------------------


def test_waiver_suppresses_a_warning() -> None:
    src = _verified_source()
    g = to_graph(authorities=[_AUTH], sources=[src])
    g.remove((URIRef(src.id), CDS.license, None))
    g += term_to_graph(_term(definition="SYNTHETIC verified definition."), scheme=_SCHEME)
    waiver = Waiver(message="tracked cds:license", reason="referenced asset, license TBD")
    result = verify(g, waivers=[waiver])
    assert result.passed
    assert result.warnings == ()


def test_a_violation_is_never_waivable_even_when_targeted() -> None:
    g = to_graph(authorities=[_AUTH], sources=[_verified_source()])
    g += term_to_graph(_term(grounding=[]), scheme=_SCHEME)  # T1 missing grounding
    waiver = Waiver(shape="TermGroundedShape", reason="trying (and failing) to waive a T1")
    result = verify(g, waivers=[waiver])
    assert not result.passed  # the T1 survives the waiver
    assert any(f.shape_name == "TermGroundedShape" for f in result.violations)


def test_blanket_waiver_is_rejected() -> None:
    import pytest

    with pytest.raises(ValueError, match="select"):
        Waiver(reason="no selector — should be rejected")


# --- CLI wiring -----------------------------------------------------------------------------


def test_cds_verify_passes_on_the_seed_graph() -> None:
    result = CliRunner().invoke(app, ["verify"])
    assert result.exit_code == 0


def test_cds_verify_exits_nonzero_on_a_broken_graph(tmp_path: object) -> None:
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    broken = tmp_path / "broken.ttl"
    g = Graph()
    s = URIRef("https://w3id.org/cds/src/orphan")
    g.add((s, RDF.type, CDS.Source))
    g.add((s, CDS.locator, Literal("x")))  # missing authority, sourceType, captureTier
    broken.write_text(g.serialize(format="turtle"))
    result = CliRunner().invoke(app, ["verify", str(broken)])
    assert result.exit_code == 1
