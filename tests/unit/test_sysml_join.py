"""Offline check that the SysML v2 anchor actually *lands* — the payoff of the equivalence axioms.

The cheap, Flexo-free precondition for roadmap T9. Answers two things T9 needs: the join resolves
via an explicit ``owl:equivalentClass`` path (no OWL reasoning), and the Definition-vs-Usage gap —
a cds anchor on ``*Definition`` does not directly meet a model's ``*Usage`` element.
"""

from __future__ import annotations

from typing import Any

from rdflib import RDF, URIRef

from cds.core.namespaces import OMG_SYSML
from cds.stages.concept_definition.build import build_concept_definition_graph

# cds-term -> local sysml construct -> (equivalentClass) -> omg class <- a model element's type
_JOIN = """
PREFIX cds: <https://w3id.org/cds#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?term ?model WHERE {
    ?term  cds:sysmlConstruct ?local .
    ?local owl:equivalentClass ?omg .
    ?model a ?omg .
}
"""


def _joins(rows: Any) -> set[tuple[str, str]]:
    return {(str(row[0]), str(row[1])) for row in rows}


def test_cds_anchor_joins_a_definition_level_sysml_element() -> None:
    g = build_concept_definition_graph()
    model = URIRef("https://model.example/ADCS-Requirements")  # a DEFINITION-level element
    g.add((model, RDF.type, OMG_SYSML.RequirementDefinition))
    # System Requirement (anchored to RequirementDefinition) joins via the alias — no OWL-RL needed
    assert ("https://w3id.org/cds/term/system-requirement", str(model)) in _joins(g.query(_JOIN))


def test_usage_level_element_does_not_directly_join_the_definition_anchor() -> None:
    # the Definition-vs-Usage gap T9 must bridge: a RequirementUsage (instance-level) does not meet
    # a cds anchor on RequirementDefinition without the SysML v2 typing link
    g = build_concept_definition_graph()
    usage = URIRef("https://model.example/REQ-001")
    g.add((usage, RDF.type, OMG_SYSML.RequirementUsage))
    assert str(usage) not in {model for _term, model in _joins(g.query(_JOIN))}
