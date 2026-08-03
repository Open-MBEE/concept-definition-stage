"""ADR-9 R7 (X2-lite) — the `position` record kind: stakeholder stances on shared objects.

cds's perspectives are stakeholders taking positions on the frame (mission, objectives,
constraints, needs). Divergence is recorded honestly: two conflicting positions are a
FINDING (DivergingPositions, T3), never a violation. Typed `cds:Position` (minted tool
structure, not canon); authored through the existing whitelisted tools, so scratch/append
modes apply for free.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cds.core.authoring import project_graph
from cds.core.compile import compile_brief
from cds.core.init import init_project
from cds.core.verify import VerifyResult, verify
from cds.core.workspace import Project, load_project
from cds.mcp import tools


@pytest.fixture()
def staging(tmp_path: Path) -> Project:
    init_project(tmp_path, name="demo")
    project = load_project(start=tmp_path)
    _run("cds_synthesis", project, slug="cd", title="Drone pilot")
    _run("cds_new", project, kind="stakeholder", slug="council", label="City council",
         description="Funds and oversees the pilot.", synthesis="cd")
    _run("cds_new", project, kind="stakeholder", slug="residents", label="Residents",
         description="Live under the flight paths.", synthesis="cd")
    _run("cds_new", project, kind="objective", slug="coverage", label="City-wide coverage",
         description="Serve every district by year two.", synthesis="cd")
    return project


def _run(name: str, *args: object, **kw: object) -> Any:
    return tools.TOOLS[name].fn(*args, **kw)


def _pos(project: Project, slug: str, held_by: str, stance: str, statement: str) -> object:
    return _run("cds_new", project, kind="position", slug=slug, label=f"{held_by} on coverage",
                description=statement, synthesis="cd", characterizes="objective/coverage",
                held_by=held_by, stance=stance)


def test_positions_author_through_existing_tools(staging: Project) -> None:
    iri = _pos(staging, "council-coverage", "council", "prioritizes",
               "Coverage is the pilot's headline objective.")
    assert str(iri).endswith("/position/council-coverage")
    listed = _run("cds_list", staging, "position")
    assert [s for s, _ in listed] == ["council-coverage"]


def test_diverging_positions_are_a_finding_never_a_violation(staging: Project) -> None:
    _pos(staging, "council-coverage", "council", "supports",
         "Coverage justifies the budget.")
    _pos(staging, "residents-coverage", "residents", "opposes",
         "Blanket coverage means constant overflight noise.")
    result: VerifyResult = verify(project_graph(staging), check_conflicts=True)
    assert result.conforms is True  # honest divergence is VALID
    diverging = [f for f in result.findings if f.rule == "DivergingPositions"]
    assert diverging and diverging[0].tier == "T3"
    assert "council" in diverging[0].message and "residents" in diverging[0].message


def test_converging_positions_not_flagged(staging: Project) -> None:
    _pos(staging, "council-coverage", "council", "supports", "Coverage matters.")
    _pos(staging, "residents-coverage", "residents", "supports", "Coverage helps us too.")
    result: VerifyResult = verify(project_graph(staging), check_conflicts=True)
    assert not [f for f in result.findings if f.rule == "DivergingPositions"]


def test_position_requires_stance_holder_target(staging: Project) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):  # pydantic gate: stance is a closed vocabulary
        _pos(staging, "bad", "council", "vibes", "Nope.")
    with pytest.raises(ValidationError):  # characterizes must be kind/slug
        _run("cds_new", staging, kind="position", slug="bad2", label="X",
             description="Y", synthesis="cd", characterizes="not a ref",
             held_by="council", stance="supports")


def test_dangling_characterizes_flagged(staging: Project) -> None:
    _run("cds_new", staging, kind="position", slug="ghosted", label="On nothing",
         description="Points at a missing objective.", synthesis="cd",
         characterizes="objective/ghost", held_by="council", stance="supports")
    result: VerifyResult = verify(project_graph(staging), check_conflicts=True)
    assert any(f.rule == "DanglingReference" and "objective/ghost" in f.message
               for f in result.findings)


def test_brief_convergence_divergence_section(staging: Project) -> None:
    _pos(staging, "council-coverage", "council", "supports", "Coverage justifies the budget.")
    _pos(staging, "residents-coverage", "residents", "opposes", "Too much overflight noise.")
    brief = compile_brief(project_graph(staging), base=staging.base_iri)
    assert "Convergence & divergence" in brief
    assert "City-wide coverage" in brief
    assert "diverge" in brief
    assert "council" in brief and "residents" in brief
    again = compile_brief(project_graph(staging), base=staging.base_iri)
    assert brief == again  # deterministic


def test_positions_inherit_lifecycle_modes(staging: Project) -> None:
    _pos(staging, "council-coverage", "council", "supports", "Coverage matters.")
    result = _run("cds_retract", staging, kind="position", slug="council-coverage",
                  reason="council revised its stance")
    assert result["retracted"].endswith("/position/council-coverage")
    brief = compile_brief(project_graph(staging), base=staging.base_iri)
    assert "council on coverage" not in brief  # retracted → out of the current view
