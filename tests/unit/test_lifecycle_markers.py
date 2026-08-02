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


# --------------------------------------------------- R3: the current view in conflicts + brief


def _two_goals(project: Project, same_desc: bool = True) -> tuple[URIRef, URIRef]:
    from cds.core.authoring import create_record as _create
    from cds.core.model.instances import Statement, record_iri

    _create(project, Statement(slug="g1", kind="goal", label="Old goal",
                               description="Deliver packages fast.", synthesis="cd"))
    _create(project, Statement(slug="g2", kind="goal", label="New goal",
                               description="Deliver packages fast." if same_desc
                               else "Deliver packages safely.", synthesis="cd"))
    return (record_iri(project.base_iri, "goal", "g1"),
            record_iri(project.base_iri, "goal", "g2"))


def test_superseded_pair_is_not_a_duplicate(tmp_path: Path) -> None:
    from cds.core.authoring import mark_superseded

    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    _g1, g2 = _two_goals(project)
    # control: both current → duplicate flagged
    assert "DuplicateStatement" in _rules(verify(project_graph(project), check_conflicts=True))
    mark_superseded(project, "goal", "g1", by=g2)
    result = verify(project_graph(project), check_conflicts=True)
    assert "DuplicateStatement" not in _rules(result)


def test_link_to_noncurrent_target_is_not_dangling(tmp_path: Path) -> None:
    from cds.core.authoring import mark_superseded, retract_record

    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    _g1, g2 = _two_goals(project, same_desc=False)
    mark_superseded(project, "goal", "g1", by=g2)
    retract_record(project, "goal", "g1", reason="rolled into g2")
    # the supersedes/supersededBy links point at a non-current record: NOT dangling,
    # and NOT a ReferenceToRetracted (lifecycle links are exempt)
    result = verify(project_graph(project), check_conflicts=True)
    assert "DanglingReference" not in _rules(result)
    assert "ReferenceToRetracted" not in _rules(result)


def test_reference_to_retracted_is_flagged_t2(tmp_path: Path) -> None:
    from cds.core.authoring import retract_record
    from cds.core.model.instances import Need as _Need

    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Stakeholder(slug="ops", kind="stakeholder", label="Ops",
                                       description="Operator.", synthesis="cd"))
    create_record(project, _Need(slug="n", kind="need", label="N",
                                 description="The ops needs the system to run.",
                                 synthesis="cd", for_stakeholder=["ops"]))
    retract_record(project, "stakeholder", "ops", reason="left the program")
    result = verify(project_graph(project), check_conflicts=True)
    hits = [f for f in result.findings if f.rule == "ReferenceToRetracted"]
    assert hits and hits[0].tier == "T2"
    assert result.conforms is True


def test_unresolved_citation_flagged(tmp_path: Path) -> None:
    """LARP#3 H-5: a record citing a project-local /src/ IRI that resolves to nothing
    must not commit silently — it is flagged T2 for the retrieval workflow."""
    from cds.core.authoring import create_record as _create
    from cds.core.model.instances import Statement as _Statement

    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    _create(project, _Statement(slug="risky", kind="driver", label="Risky",
                                description="Leans on a phantom source.", synthesis="cd",
                                cites=["https://cds.example/demo/src/phantom"]))
    result = verify(project_graph(project), check_conflicts=True)
    hits = [f for f in result.findings if f.rule == "UnresolvedCitation"]
    assert hits and hits[0].tier == "T2"
    assert result.conforms is True  # flags, never blocks authoring


def test_brief_renders_current_view_only(tmp_path: Path) -> None:
    from cds.core.authoring import mark_superseded, retract_record
    from cds.core.compile import compile_brief

    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    _g1, g2 = _two_goals(project, same_desc=False)
    mark_superseded(project, "goal", "g1", by=g2)
    retract_record(project, "goal", "g1", reason="rolled into g2")
    brief = compile_brief(project_graph(project), base=project.base_iri)
    assert "New goal" in brief
    assert "Old goal" not in brief
    assert "Superseded & retracted" not in brief  # appendix OFF by default (owner decision)


def test_compile_scopes_to_a_synthesis(tmp_path: Path) -> None:
    """LARP#2 G-5: no cross-synthesis bleed when a synthesis is named."""
    from cds.core.authoring import create_record
    from cds.core.compile import compile_brief
    from cds.core.model.instances import Statement

    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="alpha", title="Alpha"))
    create_synthesis(project, Synthesis(slug="beta", title="Beta"))
    create_record(project, Statement(slug="a-goal", kind="goal", label="Alpha goal",
                                     description="In alpha.", synthesis="alpha"))
    create_record(project, Statement(slug="b-goal", kind="goal", label="Beta goal",
                                     description="In beta.", synthesis="beta"))
    scoped = compile_brief(project_graph(project), base=project.base_iri, synthesis="alpha")
    assert "Alpha goal" in scoped and "Beta goal" not in scoped
    assert scoped.startswith("# Alpha")
    everything = compile_brief(project_graph(project), base=project.base_iri)
    assert "Alpha goal" in everything and "Beta goal" in everything  # default unchanged


def test_show_surfaces_lifecycle_state(tmp_path: Path) -> None:
    """LARP#2 G-6: append-only must be inspectable, not taken on faith."""
    from cds.core.authoring import (
        create_record,
        mark_superseded,
        retract_record,
        show_record,
    )
    from cds.core.model.instances import Statement, record_iri

    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    create_record(project, Statement(slug="old", kind="goal", label="Old",
                                     description="Was replaced.", synthesis="cd"))
    create_record(project, Statement(slug="new", kind="goal", label="New",
                                     description="Replacement.", synthesis="cd"))
    mark_superseded(project, "goal", "old", by=record_iri(project.base_iri, "goal", "new"))
    retract_record(project, "goal", "old", reason="rolled into new")
    lines = "\n".join(show_record(project, "goal", "old") or [])
    assert "retracted" in lines and "rolled into new" in lines
    assert "supersededBy" in lines and "new" in lines
    current = "\n".join(show_record(project, "goal", "new") or [])
    assert "retracted" not in current


def test_brief_history_appendix_behind_flag(tmp_path: Path) -> None:
    from cds.core.authoring import mark_superseded, retract_record
    from cds.core.compile import compile_brief

    project = _project(tmp_path)
    create_synthesis(project, Synthesis(slug="cd", title="CD"))
    _g1, g2 = _two_goals(project, same_desc=False)
    mark_superseded(project, "goal", "g1", by=g2)
    retract_record(project, "goal", "g1", reason="rolled into g2")
    brief = compile_brief(project_graph(project), base=project.base_iri, include_history=True)
    assert "Superseded & retracted" in brief
    assert "Old goal" in brief and "rolled into g2" in brief
    # deterministic: two runs byte-identical
    again = compile_brief(project_graph(project), base=project.base_iri, include_history=True)
    assert brief == again
