"""M2 — parking-lot + retrieval queue."""

from __future__ import annotations

from pathlib import Path

from cds.core.authoring import (
    create_parked,
    create_queue_item,
    list_parked,
    list_queue,
    project_graph,
    set_queue_status,
)
from cds.core.init import init_project
from cds.core.model.notes import ParkedItem, RetrievalItem, RetrievalStatus
from cds.core.verify import verify
from cds.core.workspace import Project, load_project


def _project(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    return load_project(start=tmp_path)


def test_park_and_list(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_parked(project, ParkedItem(slug="scammer", label="Is this a scammer?",
                                      description="Inbound screening sibling.", note="v0.2"))
    assert list_parked(project) == [("scammer", "Is this a scammer?")]
    assert (project.instances_dir / "parked.ttl").is_file()


def test_queue_add_advance_and_list(tmp_path: Path) -> None:
    project = _project(tmp_path)
    q = "Recording vs listening line?"
    create_queue_item(project, RetrievalItem(slug="wiretap", question=q))
    assert list_queue(project) == [("wiretap", "pending", q)]

    set_queue_status(project, "wiretap", RetrievalStatus.VERIFIED, locator="https://example/law")
    assert list_queue(project) == [("wiretap", "verified", "Recording vs listening line?")]


def test_set_status_unknown_item_raises(tmp_path: Path) -> None:
    project = _project(tmp_path)
    try:
        set_queue_status(project, "nope", RetrievalStatus.PROVIDED)
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected KeyError for unknown queue item")


def test_side_ledgers_verify_clean(tmp_path: Path) -> None:
    project = _project(tmp_path)
    create_parked(project, ParkedItem(slug="p", label="Parked"))
    create_queue_item(project, RetrievalItem(slug="q", question="Open?"))
    result = verify(project_graph(project))
    assert result.passed, [f.message for f in result.violations]
