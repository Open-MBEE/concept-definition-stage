"""Slice 6 — the Concept Definition seed scheme: build + conformance + determinism.

The scheme is built from YAML term sources carrying verbatim SEBoK v2.14 glossary definitions
(materialized in committed M — the hallucination guard). Conformance is the slice-4 gate run on the
built graph; the load-bearing terms (problem/threat/opportunity) must be grounded, not bare.
"""

from __future__ import annotations

from rdflib import RDF, URIRef
from typer.testing import CliRunner

from cds.core.asot.models import CaptureTier, RetrievalStatus
from cds.core.cli import app
from cds.core.model.term import term_iri
from cds.core.namespaces import CDS, PROV, SKOS
from cds.core.serialize import canonical_turtle
from cds.core.verify import verify
from cds.stages.concept_definition import build as build_mod
from cds.stages.concept_definition.build import (
    SCHEME,
    build_concept_definition_graph,
    load_terms,
)
from cds.stages.concept_definition.seed import SEBOK_SOURCE


def test_seed_terms_load_including_the_load_bearing_trio() -> None:
    slugs = {t.slug for t in load_terms()}
    assert {"system-of-interest", "engineered-system", "stakeholder"} <= slugs
    assert {"problem", "threat", "opportunity"} <= slugs  # load-bearing terms


def test_built_scheme_conforms() -> None:
    result = verify(build_concept_definition_graph())
    assert result.passed, [f.message for f in result.violations]


def test_load_bearing_terms_are_grounded_not_bare() -> None:
    g = build_concept_definition_graph()
    for slug in ("problem", "threat", "opportunity"):
        assert (term_iri(slug), SKOS.exactMatch, None) in g, f"{slug} is bare"


def test_every_term_materializes_verbatim_traced_to_the_verified_sebok_source() -> None:
    # the hallucination guard end-to-end: each defined term cites the verified SEBoK boundary object
    g = build_concept_definition_graph()
    sebok = URIRef(SEBOK_SOURCE.id)
    defined = set(g.subjects(SKOS.definition, None))
    assert len(defined) == len(load_terms())  # every seeded term materializes a verbatim definition
    for term in defined:
        assert (term, CDS.cites, sebok) in g  # cited to the verified boundary object


def test_scheme_is_a_provenance_tracked_conceptscheme() -> None:
    g = build_concept_definition_graph()
    assert (SCHEME, RDF.type, SKOS.ConceptScheme) in g
    assert (SCHEME, PROV.wasDerivedFrom, URIRef(SEBOK_SOURCE.id)) in g


def test_sebok_source_is_a_verified_reference_tier_boundary_object() -> None:
    # public BY-NC-SA canon: hash + locator, verified, NOT vendored (no snapshot)
    assert SEBOK_SOURCE.tier is CaptureTier.REFERENCE
    assert SEBOK_SOURCE.snapshot is None
    assert SEBOK_SOURCE.retrieval_status is RetrievalStatus.VERIFIED
    assert SEBOK_SOURCE.content_hash is not None


def test_concept_definition_ttl_is_the_committed_generation() -> None:
    g = build_concept_definition_graph()
    generated = canonical_turtle(g, prefixes=build_mod._PREFIXES)
    assert build_mod.OUTPUT_TTL.read_text() == generated


def test_committed_scheme_reparses_and_conforms() -> None:
    # the serialized artifact must round-trip (regression: glossary URLs with "(glossary)") and,
    # reparsed from disk, still pass the gate
    from rdflib import Graph

    reparsed = Graph()
    reparsed.parse(build_mod.OUTPUT_TTL, format="turtle")
    assert verify(reparsed).passed


def test_cds_build_runs_and_conforms() -> None:
    result = CliRunner().invoke(app, ["build"])
    assert result.exit_code == 0
