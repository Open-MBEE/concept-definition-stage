"""M1 — authoring accumulates deterministic RDF into the user's repo, and it verifies clean."""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF

from cds.core.authoring import create_record, create_synthesis, project_graph
from cds.core.init import init_project
from cds.core.model.instances import Need, Statement, Synthesis
from cds.core.namespaces import CDS
from cds.core.verify import verify
from cds.core.workspace import Project, load_project


def _project(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    return load_project(start=tmp_path)


def _author_full_mapping(project: Project) -> None:
    create_synthesis(project, Synthesis(slug="cd", title="Concept Definition"))
    create_record(project, Statement(
        slug="m", kind="mission", label="Reach a human",
        description="Get a person to a verified human.", synthesis="cd"))
    create_record(project, Statement(
        slug="reach", kind="goal", label="Reach",
        description="Connect to a verified human.", synthesis="cd"))
    create_record(project, Statement(
        slug="seeker", kind="stakeholder", label="Seeker",
        description="The person trying to reach a human.", synthesis="cd"))
    create_record(project, Need(
        slug="n1", kind="need", label="Reach without skill",
        description="The seeker needs the system to connect them to a human.",
        synthesis="cd", for_stakeholder=["seeker"], serves_goal=["reach"]))


def test_records_land_in_per_kind_files(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _author_full_mapping(project)
    inst = project.instances_dir
    assert (inst / "synthesis.ttl").is_file()
    assert (inst / "mission.ttl").is_file()
    assert (inst / "need.ttl").is_file()
    # writes stay inside the user's project
    assert inst.is_relative_to(tmp_path)


def test_project_graph_merges_all_instances(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _author_full_mapping(project)
    g = project_graph(project)
    assert len(list(g.subjects(CDS.inSynthesis, None))) == 4  # mission, goal, stakeholder, need
    assert (None, RDF.type, CDS.Synthesis) in g  # the mapping container is present


def test_authored_mapping_verifies_clean(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _author_full_mapping(project)
    result = verify(project_graph(project))
    assert result.passed, [f.message for f in result.violations]


def test_accumulation_is_order_independent_and_byte_stable(tmp_path: Path) -> None:
    a = _project(tmp_path / "a")
    create_synthesis(a, Synthesis(slug="cd", title="CD"))
    create_record(a, Statement(slug="x", kind="need", label="X", description="dx", synthesis="cd"))
    create_record(a, Statement(slug="y", kind="need", label="Y", description="dy", synthesis="cd"))
    need_a = (a.instances_dir / "need.ttl").read_text()

    b = _project(tmp_path / "b")
    create_synthesis(b, Synthesis(slug="cd", title="CD"))
    create_record(b, Statement(slug="y", kind="need", label="Y", description="dy", synthesis="cd"))
    create_record(b, Statement(slug="x", kind="need", label="X", description="dx", synthesis="cd"))
    need_b = (b.instances_dir / "need.ttl").read_text()

    assert need_a == need_b  # order-independent, byte-identical
    assert "X" in need_a and "Y" in need_a  # both accumulated into one file
