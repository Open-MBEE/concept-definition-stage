"""The top-level lifecycle model base class + its IP-status flag.

A system is modeled through its whole life cycle, which necessarily starts with Concept
Definition. The abstract base carries an ``ip_status`` flag: the **operator** (not the tool)
sets it to ``NC`` when the use case complies with CC-BY-NC-SA, which permits the View to render
restricted canon (e.g. SEBoK definitions); reports rendered with the flag on are CC-BY-NC-SA.
"""

from __future__ import annotations

from rdflib import RDF, RDFS, Literal, URIRef

from cds.core.controlled import controlled_concept
from cds.core.model.lifecycle import IpStatus, LifecycleModel, lifecycle_to_graph
from cds.core.namespaces import CDS

_ID = "https://w3id.org/cds/scheme/concept-definition"


def test_ip_status_defaults_to_open() -> None:
    m = LifecycleModel(id=_ID, label="Concept Definition", stage="concept-definition")
    assert m.ip_status is IpStatus.OPEN


def test_operator_can_set_ip_status_nc() -> None:
    m = LifecycleModel(
        id=_ID, label="Concept Definition", stage="concept-definition", ip_status=IpStatus.NC
    )
    assert m.ip_status is IpStatus.NC


def test_lifecycle_to_graph_emits_class_label_and_ip_status_concept() -> None:
    m = LifecycleModel(
        id=_ID, label="Concept Definition", stage="concept-definition", ip_status=IpStatus.NC
    )
    g = lifecycle_to_graph(m)
    s = URIRef(_ID)
    assert (s, RDF.type, CDS.LifecycleModel) in g
    assert (s, RDFS.label, Literal("Concept Definition")) in g
    # ip status is a grounded SKOS concept, not a bare literal
    assert (s, CDS.ipStatus, controlled_concept(IpStatus.NC)) in g
