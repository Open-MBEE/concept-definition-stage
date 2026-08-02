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
