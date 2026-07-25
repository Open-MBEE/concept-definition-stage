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
from cds.stages.concept_definition.seed import GTWR_SOURCE, SEBOK_SOURCE


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


def test_every_term_materializes_verbatim_traced_to_a_verified_source() -> None:
    # the hallucination guard end-to-end: each defined term cites a verified boundary object
    # (SEBoK for the glossary terms, GtWR for the need/requirement terms)
    g = build_concept_definition_graph()
    verified = {URIRef(SEBOK_SOURCE.id), URIRef(GTWR_SOURCE.id)}
    terms = set(g.subjects(RDF.type, CDS.Term))
    defined = {t for t in terms if (t, SKOS.definition, None) in g}
    assert len(defined) == len(load_terms())  # every seeded term materializes a verbatim definition
    for term in defined:
        assert set(g.objects(term, CDS.cites)) & verified, f"{term} not cited to a verified source"


def test_definitions_keep_sebok_s_upstream_attribution() -> None:
    # provenance that reinforces we leverage SEBoK's CURATION of already-public content, not
    # proprietary appropriation: every seeded definition records SEBoK's own source attribution.
    from rdflib import Literal

    g = build_concept_definition_graph()
    assert (term_iri("opportunity"), CDS.definitionSource, Literal("Dictionary.com 2012")) in g
    assert (term_iri("system-of-interest"), CDS.definitionSource, Literal("ISO/IEC/IEEE 2015")) in g
    # GtWR-native terms (need/requirement) have no upstream attribution — GtWR IS the source
    assert (term_iri("need"), CDS.definitionSource, None) not in g


def test_scheme_is_a_provenance_tracked_conceptscheme() -> None:
    g = build_concept_definition_graph()
    assert (SCHEME, RDF.type, SKOS.ConceptScheme) in g
    assert (SCHEME, PROV.wasDerivedFrom, URIRef(SEBOK_SOURCE.id)) in g


def test_need_and_requirement_are_gtwr_terms_grounded_to_sebok() -> None:
    g = build_concept_definition_graph()
    gtwr = URIRef(GTWR_SOURCE.id)
    for slug, sebok_concept in (
        ("need", "https://sebokwiki.org/wiki/Need_(glossary)"),
        ("requirement", "https://sebokwiki.org/wiki/Requirement_(glossary)"),
    ):
        assert (term_iri(slug), CDS.cites, gtwr) in g  # sourced from GtWR
        assert (term_iri(slug), SKOS.closeMatch, URIRef(sebok_concept)) in g  # grounded, not bare


def test_concept_addresses_problem_threat_opportunity() -> None:
    g = build_concept_definition_graph()
    for target in ("problem", "threat", "opportunity"):
        assert (term_iri("solution"), CDS.addresses, term_iri(target)) in g


def test_gtwr_c1_c15_companion_vocab_is_cited_but_not_terms() -> None:
    from cds.stages.concept_definition.build import CHARACTERISTICS_SCHEME

    g = build_concept_definition_graph()
    chars = set(g.subjects(SKOS.inScheme, CHARACTERISTICS_SCHEME))
    assert len(chars) == 15  # C1-C15
    c1 = URIRef("https://w3id.org/cds/characteristic/C1")
    assert (c1, SKOS.prefLabel, None) in g
    assert (c1, CDS.cites, URIRef(GTWR_SOURCE.id)) in g
    # they are a companion vocab, NOT cds:Terms (so the term-grounding rule does not apply)
    assert (c1, RDF.type, CDS.Term) not in g
    assert (CHARACTERISTICS_SCHEME, PROV.wasDerivedFrom, URIRef(GTWR_SOURCE.id)) in g


def test_business_mission_analysis_concepts_are_grounded_and_sourced() -> None:
    g = build_concept_definition_graph()
    sebok = URIRef(SEBOK_SOURCE.id)
    for slug in ("goal", "objective", "solution-class"):
        assert (term_iri(slug), CDS.cites, sebok) in g  # verbatim verified against the held PDF
        assert (term_iri(slug), SKOS.relatedMatch, None) in g  # grounded (related-only, waived)


def test_related_only_warnings_are_waived_by_first_class_rdf_waivers() -> None:
    from rdflib import Graph

    from cds.core.verify import verify, waivers_from_graph
    from cds.core.workspace import waivers_path

    waivers_ttl = waivers_path()
    waiver_graph = Graph()
    waiver_graph.parse(waivers_ttl, format="turtle")
    result = verify(build_concept_definition_graph(), waivers=waivers_from_graph(waiver_graph))
    assert not any(f.rule == "TermRelatedOnlyShape" for f in result.warnings)


def test_no_restricted_sebok_canon_leaks_under_a_permissive_license() -> None:
    # the redistribution control, as an ALL-TERMS property: under a non-SEBoK-compatible license, NO
    # restricted SEBoK verbatim appears anywhere in the rendered output (not just one spot-check)
    from cds.core.render.typst import typst_document
    from cds.core.render.view import scheme_view

    g = build_concept_definition_graph()
    permissive = typst_document(scheme_view(g, title="x", text_license="CC-BY-4.0"))
    sebok = URIRef(SEBOK_SOURCE.id)
    sebok_terms = [t for t in g.subjects(CDS.cites, sebok) if (t, SKOS.definition, None) in g]
    assert len(sebok_terms) >= 25  # the glossary + in-prose SEBoK-sourced terms
    for term in sebok_terms:
        definition = str(g.value(term, SKOS.definition))
        assert definition not in permissive, f"restricted SEBoK verbatim leaked for {term}"


def test_provenance_integrity_every_citation_resolves_to_a_verified_source() -> None:
    # the faithful-capture audit the sponsor relies on: every cited source is a registered, verified
    # boundary object attributed to a registered authority
    g = build_concept_definition_graph()
    sources = set(g.subjects(RDF.type, CDS.Source))
    authorities = set(g.subjects(RDF.type, CDS.Authority))
    verified = CDS["RetrievalStatus/verified"]
    cited = {o for _s, _p, o in g.triples((None, CDS.cites, None))}
    assert cited, "no citations found"
    for source in cited:
        assert source in sources, f"cites an unregistered source: {source}"
        assert g.value(source, PROV.wasAttributedTo) in authorities, f"{source}: bad authority"
        retrieval = URIRef(f"{source}/retrieval")
        assert (retrieval, CDS.retrievalStatus, verified) in g, f"{source}: not verified"


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
