"""Slice 7 — SysML v2 structural anchoring by equivalence axioms (no vendored OWL cache)."""

from __future__ import annotations

from rdflib import OWL, RDF, Graph, URIRef

from cds.core.anchors.sysml import invoked_constructs, sysml_anchor_graph
from cds.core.model.term import Term, term_iri, term_to_graph
from cds.core.namespaces import CDS, OMG_SYSML, SYSML
from cds.stages.concept_definition.build import build_concept_definition_graph

_SCHEME = URIRef("https://w3id.org/cds/scheme/concept-definition")


def _anchored_term() -> Graph:
    return term_to_graph(
        Term(
            slug="x",
            pref_label="X",
            grounding=[{"relation": "exact-match", "target": "https://e/X"}],  # type: ignore[list-item]
            cites=["https://w3id.org/cds/src/sebok-v2-14"],
            sysml_construct=str(SYSML.PartDefinition),
        ),
        scheme=_SCHEME,
    )


def test_invoked_constructs_are_collected_from_sysml_construct_edges() -> None:
    assert SYSML.PartDefinition in invoked_constructs(_anchored_term())


def test_anchor_emits_equivalence_axiom_and_an_omg_stub() -> None:
    g = sysml_anchor_graph(_anchored_term())
    assert (SYSML.PartDefinition, RDF.type, OWL.Class) in g
    assert (SYSML.PartDefinition, OWL.equivalentClass, OMG_SYSML.PartDefinition) in g
    assert (OMG_SYSML.PartDefinition, RDF.type, OWL.Class) in g  # OMG-side stub, not dangling


def test_anchor_is_parsimonious_only_invoked_constructs() -> None:
    g = sysml_anchor_graph(_anchored_term())
    # RequirementDefinition is not invoked by this term -> not materialized
    assert (SYSML.RequirementDefinition, RDF.type, OWL.Class) not in g


def test_built_scheme_anchors_the_expected_terms() -> None:
    g = build_concept_definition_graph()
    assert (term_iri("system-of-interest"), CDS.sysmlConstruct, SYSML.PartDefinition) in g
    assert (term_iri("capability"), CDS.sysmlConstruct, SYSML.UseCaseDefinition) in g
    # the equivalence axioms travel with the built scheme
    assert (SYSML.RequirementDefinition, OWL.equivalentClass, OMG_SYSML.RequirementDefinition) in g
    # terms with no SysML construct stay canon-only (no anchor edge)
    assert (term_iri("problem"), CDS.sysmlConstruct, None) not in g
