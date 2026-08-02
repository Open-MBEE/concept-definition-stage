"""ADR-9 R1 — lifecycle-marker vocabulary + shapes (supersede/retract, append-only record).

Markers are claim-level (they attach to ``cds:Instance`` records, which are reified
statements), well-formedness is SHACL-guarded (one shape guards the invariant), and dangling
``cds:supersededBy`` is caught by the existing cross-reference pass.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import OWL, RDF, XSD, Graph, Literal, URIRef

from cds.core.authoring import create_record, create_synthesis, project_graph
from cds.core.init import init_project
from cds.core.model.instances import Need, Stakeholder, Synthesis
from cds.core.namespaces import CDS
from cds.core.verify import VerifyResult, verify
from cds.core.vocabulary import core_vocab_graph
from cds.core.workspace import Project, load_project


def _project(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    return load_project(start=tmp_path)


def _seeded(project: Project) -> Graph:
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Stakeholder(slug="seeker", kind="stakeholder", label="Seeker",
                                       description="Person seeking help.", synthesis="cd"))
    create_record(project, Need(slug="n", kind="need", label="Reach",
                                description="The seeker needs to reach a human.",
                                synthesis="cd", for_stakeholder=["seeker"]))
    return project_graph(project)


def _rules(result: VerifyResult) -> set[str]:
    return {f.rule for f in result.findings}


def test_vocabulary_declares_lifecycle_terms() -> None:
    g = core_vocab_graph()
    for term in ("supersedes", "supersededBy", "retracted", "retractionReason"):
        assert (CDS[term], RDF.type, RDF.Property) in g, f"cds:{term} undeclared"
    assert (CDS.Instance, RDF.type, OWL.Class) in g
    assert (CDS.supersededBy, OWL.inverseOf, CDS.supersedes) in g


def test_retracted_marker_verifies_clean(tmp_path: Path) -> None:
    graph = _seeded(_project(tmp_path))
    need = URIRef("https://cds.example/demo/need/n")
    graph.add((need, CDS.retracted, Literal(True)))
    graph.add((need, CDS.retractionReason, Literal("consolidated elsewhere")))
    assert verify(graph).conforms is True


def test_double_retracted_marker_is_t1(tmp_path: Path) -> None:
    graph = _seeded(_project(tmp_path))
    need = URIRef("https://cds.example/demo/need/n")
    graph.add((need, CDS.retracted, Literal(True)))
    graph.add((need, CDS.retracted, Literal(False)))
    assert verify(graph).conforms is False


def test_retracted_wrong_datatype_is_t1(tmp_path: Path) -> None:
    graph = _seeded(_project(tmp_path))
    need = URIRef("https://cds.example/demo/need/n")
    graph.add((need, CDS.retracted, Literal("yes", datatype=XSD.string)))
    assert verify(graph).conforms is False


def test_no_confound_baseline_is_clean(tmp_path: Path) -> None:
    result = verify(_seeded(_project(tmp_path)), check_conflicts=True)
    assert "DanglingReference" not in _rules(result)


def test_dangling_supersededby_is_flagged(tmp_path: Path) -> None:
    graph = _seeded(_project(tmp_path))
    need = URIRef("https://cds.example/demo/need/n")
    graph.add((need, CDS.supersededBy,
               URIRef("https://cds.example/demo/need/ghost")))
    result = verify(graph, check_conflicts=True)
    dangling = [f for f in result.findings if f.rule == "DanglingReference"]
    assert any("need/ghost" in f.message for f in dangling)
    assert result.conforms is True  # cross-ref findings flag, never fail the gate
