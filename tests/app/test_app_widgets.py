"""P5 — the app tier: widget UI over the session, with NO code surface (K3) and
off-thread advisory verify (N7). Headless: skips cleanly without ipywidgets."""

from __future__ import annotations

from pathlib import Path

import pytest

ipywidgets = pytest.importorskip("ipywidgets")

from cds.app import widgets  # noqa: E402
from cds.core.workspace import Project  # noqa: E402
from cds.mcp import staging  # noqa: E402


@pytest.fixture()
def session(tmp_path: Path) -> Project:
    return staging.new_session_project("https://cds.example/p5/", root=tmp_path / "s")


def _walk(widget: object) -> list[object]:
    out = [widget]
    for child in getattr(widget, "children", ()) or ():
        out.extend(_walk(child))
    return out


def test_app_builds_headless(session: Project) -> None:
    app = widgets.build_app(session)
    assert app is not None
    assert len(_walk(app)) > 5  # a real composite, not a stub


def test_no_code_widget(session: Project) -> None:
    """REQ-K3.1 — the UI exposes no code/terminal affordance. Free-text exists only for
    *content* fields; nothing is executed, and no widget offers code semantics."""
    tree = _walk(widgets.build_app(session))
    forbidden = tuple(
        cls for cls in (getattr(ipywidgets, "Terminal", None),) if cls is not None
    )
    assert not [w for w in tree if isinstance(w, forbidden)] if forbidden else True
    for w in tree:
        desc = (getattr(w, "description", "") or "").lower()
        placeholder = (getattr(w, "placeholder", "") or "").lower()
        for needle in ("code", "python", "shell", "command"):
            assert needle not in desc, f"code-suggestive widget: {desc!r}"
            assert needle not in placeholder, f"code-suggestive widget: {placeholder!r}"


def test_record_form_writes_candidates(session: Project) -> None:
    from cds.core.authoring import project_graph

    form = widgets.RecordForm(session)
    form.kind.value = "goal"
    form.slug.value = "g1"
    form.label.value = "A goal"
    form.description.value = "Something worth doing."
    form.synthesis.value = "m1"
    widgets.build_synthesis(session, slug="m1", title="M")  # container first
    form.submit()
    assert "g1" in form.status.value  # user feedback
    assert len(project_graph(session)) > 0


def test_verify_panel_runs_off_thread(session: Project) -> None:
    """REQ-N7.1 — advisory verify runs off the calling thread and reports findings."""
    import threading

    widgets.build_synthesis(session, slug="m1", title="M")
    panel = widgets.VerifyPanel(session)
    main_thread = threading.current_thread().name
    done = panel.refresh()  # returns a Future
    result = done.result(timeout=30)
    assert result.thread_name != main_thread  # ran off-thread
    assert "conforms" in panel.status.value.lower() or "T" in panel.status.value


def test_commit_button_is_role_gated(session: Project) -> None:
    panel = widgets.CommitPanel(session)
    panel.commit()
    # no canonical/role bound in this session → the refusal reaches the user, not a stack
    assert "reviewer" in panel.status.value.lower() \
        or "canonical" in panel.status.value.lower()


def test_notebook_is_thin() -> None:
    """The .ipynb is a shell: substance stays in cds .py modules (spec §12 drift risk)."""
    import json

    nb_path = Path(widgets.__file__).parent / "notebook" / "concept_definition_app.ipynb"
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) <= 2
    source = "".join("".join(c["source"]) for c in code_cells)
    assert "build_app" in source and len(source) < 500


# ------------------------------------------- D5/S4 (live-QA 2026-08-02): identity vs content


def _staged_goal(session: Project, form: widgets.RecordForm) -> None:
    widgets.build_synthesis(session, slug="m1", title="M")
    form.kind.value = "goal"
    form.slug.value = "g1"
    form.label.value = "A goal"
    form.description.value = "Something worth doing."
    form.synthesis.value = "m1"
    form.submit()


def test_form_has_create_and_revise_modes(session: Project) -> None:
    form = widgets.RecordForm(session)
    assert list(form.mode.options) == ["Create new", "Revise existing"]
    assert form.mode.value == "Create new"
    assert not form.slug.disabled and not form.synthesis.disabled


def test_revise_mode_locks_identity(session: Project) -> None:
    """Identity (slug, mapping placement) is authored once; revising content must not
    invite rewriting it. In revise mode the record is picked, not typed, and the
    placement is locked."""
    form = widgets.RecordForm(session)
    _staged_goal(session, form)
    form.mode.value = "Revise existing"
    assert form.synthesis.disabled  # placement locked
    assert "g1" in tuple(form.existing.options)  # pick, don't type
    assert not form.label.disabled and not form.description.disabled  # content free


def test_revise_submits_an_edit_not_a_create(session: Project) -> None:
    from rdflib import RDFS

    from cds.core.authoring import project_graph
    from cds.core.model.instances import record_iri

    form = widgets.RecordForm(session)
    _staged_goal(session, form)
    form.mode.value = "Revise existing"
    form.existing.value = "g1"
    form.label.value = "A sharper goal"
    form.submit()
    assert "g1" in form.status.value
    g = project_graph(session)
    labels = [str(o) for o in g.objects(record_iri(session.base_iri, "goal", "g1"),
                                        RDFS.label)]
    assert labels == ["A sharper goal"]


def test_revise_prefills_content_from_the_record(session: Project) -> None:
    form = widgets.RecordForm(session)
    _staged_goal(session, form)
    form.label.value = ""
    form.description.value = ""
    form.mode.value = "Revise existing"
    form.existing.value = "g1"
    assert form.label.value == "A goal"
    assert "worth doing" in form.description.value
    assert form.synthesis.value == "m1"


def test_statement_field_is_roomy(session: Project) -> None:
    form = widgets.RecordForm(session)
    height = form.description.layout.height
    assert height is not None and int(height.rstrip("px")) >= 100


def test_actions_follow_the_flow(session: Project) -> None:
    """Compose, stage, verify, compile, commit: the buttons appear in that order."""
    tree = _walk(widgets.build_app(session))
    buttons = [w.description for w in tree if isinstance(w, ipywidgets.Button)]
    stage = buttons.index("Stage candidate")
    verify = buttons.index("Verify (advisory)")
    compile_ = buttons.index("Compile brief")
    commit = buttons.index("Commit to record")
    assert stage < verify < compile_ < commit


def test_staged_count_banner_updates(session: Project) -> None:
    """Live-QA Step-2: staging is not durable; the app says how much uncommitted work
    the session holds instead of implying persistence."""
    app = widgets.build_app(session)
    banner = next(w for w in _walk(app)
                  if isinstance(w, ipywidgets.HTML) and "staged" in w.value)
    assert "0" in banner.value
    form = next(w for w in _walk(app) if isinstance(w, ipywidgets.VBox) and
                getattr(w, "_cds_form", None) is not None)._cds_form
    _staged_goal(session, form)
    assert "2" in banner.value  # the mapping + the goal
