"""The self-model dogfood (plan DoD): cds models its own Concept Definition; build/verify/render."""

from __future__ import annotations

from rdflib import RDF, URIRef

from cds.core.model.term import term_iri
from cds.core.namespaces import CDS, PROV, SKOS
from cds.core.render.typst import typst_document
from cds.core.render.view import scheme_view
from cds.core.verify import verify
from cds.fixtures.self_model import MISSION_SOURCE, SELF_SCHEME, self_model_graph


def test_self_model_verifies_clean() -> None:
    # the full construction order on cds's own mission; the self-waiver (carried in the graph)
    # suppresses the related-only warning, so it is T1-clean AND warning-clean
    result = verify(self_model_graph())
    assert result.passed
    assert result.warnings == ()


def test_self_model_exercises_authority_source_and_grounded_term() -> None:
    g = self_model_graph()
    assert (URIRef(MISSION_SOURCE.id), RDF.type, CDS.Source) in g  # verified boundary object
    assert (SELF_SCHEME, PROV.wasDerivedFrom, URIRef(MISSION_SOURCE.id)) in g  # provenance-tracked
    mission = term_iri("cds-mission")
    assert (mission, RDF.type, CDS.Term) in g
    assert (mission, SKOS.definition, None) in g  # verbatim attached
    assert (mission, CDS.cites, URIRef(MISSION_SOURCE.id)) in g  # cites the verified source


def test_self_model_renders() -> None:
    view = scheme_view(self_model_graph(), title="cds self-model", text_license="CC-BY-NC-SA-4.0")
    source = typst_document(view)
    assert "cds mission" in source
    assert "cds standardizes the System Concept Definition stage" in source  # verbatim rendered
