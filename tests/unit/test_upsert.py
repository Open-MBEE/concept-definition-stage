"""Regression tests for the correction-safety fixes found in simulated user testing.

Sessions S1/S2 showed re-authoring a slug *appended* (contradictory multi-valued records) with no
edit/rm and no read-back, and verify didn't catch the doubling. These lock in the fixes.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF, RDFS, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS

from cds.core.authoring import (
    create_parked,
    create_queue_item,
    create_record,
    create_synthesis,
    edit_record,
    list_records,
    project_graph,
    remove_record,
    show_record,
)
from cds.core.init import init_project
from cds.core.model.instances import Statement, Synthesis, record_iri
from cds.core.model.notes import ParkedItem, RetrievalItem, parked_iri, queue_iri
from cds.core.namespaces import CDS, CDS_TERM
from cds.core.verify import verify
from cds.core.workspace import Project, load_project


def _p(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    return load_project(start=tmp_path)


def test_reauthor_replaces_not_appends(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="g", kind="goal", label="V1",
                                     description="first", synthesis="cd"))
    edit_record(project, Statement(slug="g", kind="goal", label="V2",
                                   description="second", synthesis="cd"))
    g = project_graph(project)
    s = record_iri(project.base_iri, "goal", "g")
    assert list(g.objects(s, RDFS.label)) == [Literal("V2")]  # single, latest wins
    assert list(g.objects(s, DCTERMS.description)) == [Literal("second")]


def test_reauthored_record_verifies_clean(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="g", kind="goal", label="A",
                                     description="x", synthesis="cd"))
    edit_record(project, Statement(slug="g", kind="goal", label="B",
                                   description="y", synthesis="cd"))
    assert verify(project_graph(project)).passed


def test_park_and_queue_upsert(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_parked(project, ParkedItem(slug="p", label="One"))
    create_parked(project, ParkedItem(slug="p", label="Two"))
    create_queue_item(project, RetrievalItem(slug="q", question="Q1"))
    create_queue_item(project, RetrievalItem(slug="q", question="Q2"))
    g = project_graph(project)
    assert list(g.objects(parked_iri(project.base_iri, "p"), RDFS.label)) == [Literal("Two")]
    assert list(g.objects(queue_iri(project.base_iri, "q"), RDFS.label)) == [Literal("Q2")]


def test_rm_and_readback(tmp_path: Path) -> None:
    project = _p(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="reach", kind="goal", label="Reach",
                                     description="connect", synthesis="cd"))
    assert list_records(project, "goal") == [("reach", "Reach")]
    lines = show_record(project, "goal", "reach")
    assert lines is not None and any("Reach" in ln for ln in lines)

    assert remove_record(project, "goal", "reach") is True
    assert list_records(project, "goal") == []
    assert remove_record(project, "goal", "reach") is False  # already gone


def test_verify_catches_doubled_label(tmp_path: Path) -> None:
    # defense-in-depth: a doubled-value record (e.g. from a hand-edit) fails the gate
    g = Graph()
    s = URIRef("https://cds.example/demo/goal/a")
    g.add((s, RDF.type, CDS.Instance))
    g.add((s, RDF.type, CDS_TERM["goal"]))
    g.add((s, RDFS.label, Literal("A")))
    g.add((s, RDFS.label, Literal("B")))  # two labels — must be caught
    g.add((s, DCTERMS.description, Literal("d")))
    g.add((s, CDS.inSynthesis, URIRef("https://cds.example/demo/synthesis/cd")))
    assert not verify(g).passed
