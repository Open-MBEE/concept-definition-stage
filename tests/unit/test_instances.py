"""M1 — instance models + deterministic serialization."""

from __future__ import annotations

import pytest
from rdflib import RDF, RDFS, Literal

from cds.core.model.instances import (
    Need,
    Statement,
    Synthesis,
    model_for_kind,
    record_iri,
    record_to_graph,
    synthesis_to_graph,
)
from cds.core.namespaces import CDS, CDS_TERM, DCTERMS

BASE = "https://cds.example/demo/"


def test_record_is_typed_by_vocabulary_term_plus_marker() -> None:
    rec = Statement(slug="m1", kind="mission", label="Reach a human",
                    description="Get a person to a verified human.", synthesis="cd")
    g = record_to_graph(rec, base=BASE)
    s = record_iri(BASE, "mission", "m1")
    assert (s, RDF.type, CDS.Instance) in g
    assert (s, RDF.type, CDS_TERM["mission"]) in g
    assert (s, RDFS.label, Literal("Reach a human")) in g
    assert (s, DCTERMS.description, Literal("Get a person to a verified human.")) in g
    assert any(g.objects(s, CDS.inSynthesis))


def test_need_emits_stakeholder_and_goal_links() -> None:
    need = Need(slug="n1", kind="need", label="Reach a human", description="…",
                synthesis="cd", for_stakeholder=["seeker", "caregiver"], serves_goal=["reach"])
    g = record_to_graph(need, base=BASE)
    s = record_iri(BASE, "need", "n1")
    assert (s, CDS.forStakeholder, record_iri(BASE, "stakeholder", "seeker")) in g
    assert (s, CDS.forStakeholder, record_iri(BASE, "stakeholder", "caregiver")) in g
    assert (s, CDS.servesGoal, record_iri(BASE, "goal", "reach")) in g


def test_synthesis_graph() -> None:
    g = synthesis_to_graph(Synthesis(slug="cd", title="Concept Definition"), base=BASE)
    s = record_iri(BASE, "synthesis", "cd")  # same IRI scheme
    assert (s, RDF.type, CDS.Synthesis) in g
    assert (s, RDFS.label, Literal("Concept Definition")) in g


def test_unknown_kind_rejected() -> None:
    with pytest.raises(ValueError):
        Statement(slug="x", kind="bogus", label="a", description="b", synthesis="cd")
    with pytest.raises(ValueError):
        model_for_kind("bogus")


def test_model_for_kind_picks_subclasses() -> None:
    from cds.core.model.instances import Goal, Need, Objective, Stakeholder

    assert model_for_kind("need") is Need
    assert model_for_kind("goal") is Goal
    assert model_for_kind("objective") is Objective
    assert model_for_kind("stakeholder") is Stakeholder
    assert model_for_kind("mission") is Statement
