"""U1/U2 (live-QA 2026-08-02 @ bb2d4a7): user-facing text reads plainly.

Two rules for every string a user of the services, CLI, web app, or verify output
actually sees:

- no internal coordination labels (K1, K2, "correct-by-construction", operator flag
  names on end-user surfaces) — those belong in the architecture docs;
- no em-dashes ("no need to make people feel like they are talking to an LLM").

Source comments, docstrings, and the architecture docs are free to keep both.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cds.core.workspace import Project

EM_DASH = "—"
JARGON = ("K1", "K2", "K3", "K4", "K5", "correct-by-construction")

SHAPES_DIR = Path(__file__).parents[2] / "src" / "cds" / "ontology" / "shapes"


def _assert_plain(text: str, where: str) -> None:
    assert EM_DASH not in text, f"em-dash in {where}: {text!r}"
    for token in JARGON:
        assert token not in text, f"internal label {token} in {where}: {text!r}"


@pytest.fixture()
def staging(tmp_path: Path) -> Project:
    proj = Project(root=tmp_path / "s", base_iri="https://cds.example/u/")
    proj.instances_dir.mkdir(parents=True)
    return proj


def test_tool_descriptions_read_plainly() -> None:
    from cds.mcp import tools

    for spec in tools.TOOLS.values():
        _assert_plain(spec.description, f"tool {spec.name} description")


def test_shared_service_text_reads_plainly() -> None:
    from cds.core import usertext

    for name in dir(usertext):
        value = getattr(usertext, name)
        if name.isupper() and isinstance(value, str):
            _assert_plain(value, f"usertext.{name}")


def test_shacl_messages_read_plainly() -> None:
    for shapes_file in sorted(SHAPES_DIR.glob("*.ttl")):
        for line in shapes_file.read_text(encoding="utf-8").splitlines():
            if "sh:message" in line:
                _assert_plain(line, f"{shapes_file.name} sh:message")


def test_finding_messages_read_plainly(staging: Project) -> None:
    from cds.mcp import tools

    run = tools.TOOLS
    run["cds_synthesis"].fn(staging, slug="m1", title="Mapping One")
    run["cds_new"].fn(staging, kind="stakeholder", slug="a", label="A",
                      description="First stakeholder.", synthesis="m1")
    run["cds_new"].fn(staging, kind="stakeholder", slug="b", label="B",
                      description="Second stakeholder.", synthesis="m1")
    run["cds_new"].fn(staging, kind="objective", slug="o", label="O",
                      description="The contested objective.", synthesis="m1")
    run["cds_new"].fn(staging, kind="position", slug="pa", label="A on O",
                      description="A prioritizes it.", synthesis="m1",
                      characterizes="objective/o", held_by="a", stance="prioritizes")
    run["cds_new"].fn(staging, kind="position", slug="pb", label="B on O",
                      description="B opposes it.", synthesis="m1",
                      characterizes="objective/o", held_by="b", stance="opposes")
    run["cds_new"].fn(staging, kind="need", slug="n", label="N",
                      description="The system shall never say shall.", synthesis="m1",
                      for_stakeholder=["ghost"],
                      cites=["https://cds.example/u/src/missing"])
    result = run["cds_verify"].fn(staging)
    assert result.findings  # the fixture must actually exercise the message builders
    for f in result.findings:
        _assert_plain(f.message, f"finding {f.rule}")


def test_compiled_brief_reads_plainly(staging: Project) -> None:
    from cds.mcp import tools

    run = tools.TOOLS
    run["cds_synthesis"].fn(staging, slug="m1", title="Mapping One")
    run["cds_new"].fn(staging, kind="goal", slug="old", label="Old goal",
                      description="Replaced later.", synthesis="m1")
    run["cds_new"].fn(staging, kind="goal", slug="new", label="New goal",
                      description="The replacement.", synthesis="m1",
                      supersedes=["old"])
    brief = run["cds_compile"].fn(staging, include_history=True)
    _assert_plain(brief, "compiled brief")


def test_record_echo_reads_plainly(staging: Project) -> None:
    from cds.mcp import tools

    run = tools.TOOLS
    run["cds_synthesis"].fn(staging, slug="m1", title="Mapping One")
    run["cds_new"].fn(staging, kind="goal", slug="g", label="Fast",
                      description="Fast delivery.", synthesis="m1")
    lines = run["cds_show"].fn(staging, "goal", "g")
    assert lines
    for line in lines:
        _assert_plain(line, "cds_show line")


def test_explain_reads_plainly() -> None:
    from cds.core import explain as explain_mod
    from cds.core.model.instances import AUTHORABLE_KINDS

    for line in explain_mod.glossary():
        _assert_plain(line, "glossary")
    for term in (*AUTHORABLE_KINDS, "retract", "supersede", "discard", "verify"):
        for line in explain_mod.explain(term) or []:
            _assert_plain(line, f"explain {term}")


def test_explain_changes_is_a_chooser() -> None:
    """U3 (live-QA 2026-08-02): 'is there a good reason to have two modes and if so
    let's make it really obvious when each is appropriate.' One topic answers
    'which kind of change is this?' for every mode."""
    from cds.core import explain as explain_mod

    lines = explain_mod.explain("changes")
    assert lines is not None
    text = "\n".join(lines)
    for verb in ("edit", "supersede", "retract", "rm"):
        assert verb in text, f"chooser must cover {verb}"
    for line in lines:
        _assert_plain(line, "explain changes")


def test_collision_hint_points_at_the_chooser(staging: Project) -> None:
    from cds.core.authoring import RecordExistsError
    from cds.mcp import tools as mcp_tools

    run = mcp_tools.TOOLS
    run["cds_synthesis"].fn(staging, slug="m1", title="Mapping One")
    run["cds_new"].fn(staging, kind="goal", slug="g", label="Fast",
                      description="Fast delivery.", synthesis="m1")
    with pytest.raises(RecordExistsError) as exc:
        run["cds_new"].fn(staging, kind="goal", slug="g", label="Other",
                          description="Different.", synthesis="m1")
    assert "changes" in str(exc.value)  # the hint teaches where the chooser lives
