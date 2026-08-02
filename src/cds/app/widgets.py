"""The app tier's widget UI (T3) — forms and panels over the SAME constrained session.

Every interaction goes through the K1 registry (``cds.mcp.tools``) exactly like the HTTP
and MCP transports — the UI adds no affordance the boundary lacks, and deliberately offers
**no code surface** (REQ-K3.1, guarded by ``tests/app/test_no_code_widget``). Advisory
verification runs OFF the UI thread (REQ-N7.1) so authoring never blocks on SHACL.

ipywidgets is imported lazily so the module (and autodoc) loads on a lean install; the
factories are headless-testable — they build widget trees without a display.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cds.core.workspace import Project
from cds.mcp import tools as mcp_tools

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cds-verify")


def _w() -> Any:
    import ipywidgets  # type: ignore[import-not-found,import-untyped]  # app extra; lazy

    return ipywidgets


def build_synthesis(project: Project, *, slug: str, title: str) -> str:
    """Convenience used by the app's first-run flow and tests."""
    return str(mcp_tools.TOOLS["cds_synthesis"].fn(project, slug=slug, title=title))


def bootstrap_session() -> Project:
    """The deployed app's entry: bind IDENTITY-derived roles into the session (K2/N2).

    The spawner (deploy/jupyterhub_config.py) injects ``CDS_ROLES`` (from the user's OIDC
    realm roles), ``CDS_APPROVER`` (the user's agent IRI) and optionally ``CDS_CANONICAL``
    (the analysis repo mount). Roles come from the identity provider — never from the UI.
    Locally, with none of these set, you get an unbound scratch session.
    """
    import json
    import os

    from cds.core.workspace import load_project
    from cds.mcp import staging

    canonical_path = os.environ.get("CDS_CANONICAL")
    canonical = load_project(explicit=Path(canonical_path)) if canonical_path else None
    mcp_tools.SESSION.canonical = canonical
    mcp_tools.SESSION.roles = frozenset(json.loads(os.environ.get("CDS_ROLES", "[]")))
    mcp_tools.SESSION.approver = os.environ.get("CDS_APPROVER")
    base = canonical.base_iri if canonical is not None else "https://cds.example/app/"
    return staging.new_session_project(base)


def staged_count(project: Project) -> int:
    """How many records this session holds that no reviewer has committed."""
    from rdflib import RDF

    from cds.core.authoring import project_graph
    from cds.core.namespaces import CDS

    g = project_graph(project)
    staged = set(g.subjects(RDF.type, CDS.Instance))
    staged |= set(g.subjects(RDF.type, CDS.Synthesis))
    return len(staged)


class RecordForm:
    """Author one record — kind-aware fields, Pydantic-gated on submit (candidates only).

    D5/S4 (live-QA 2026-08-02): establishing a record's IDENTITY (kind, slug, mapping
    placement) and revising its CONTENT (label, statement, links) are different acts.
    Create mode types the identity; Revise mode PICKS an existing record, locks its
    placement, prefills its content, and submits an edit — a slug is never a text box
    on an existing record.
    """

    def __init__(self, project: Project,
                 on_staged: Callable[[], None] | None = None) -> None:
        from cds.core.model.instances import AUTHORABLE_KINDS

        w = _w()
        self.project = project
        self.on_staged = on_staged
        wide = w.Layout(width="95%")
        self.mode = w.ToggleButtons(options=["Create new", "Revise existing"],
                                    description="Mode")
        self.kind = w.Dropdown(options=list(AUTHORABLE_KINDS), description="Kind")
        self.slug = w.Text(description="Slug", placeholder="kebab-case-id")
        self.existing = w.Dropdown(options=(), description="Record",
                                   layout=w.Layout(width="95%", display="none"))
        self.synthesis = w.Text(description="Mapping", placeholder="synthesis slug")
        self.label = w.Text(description="Label", placeholder="Short name", layout=wide)
        self.description = w.Textarea(
            description="Statement",
            placeholder="The content statement. For a need, use need-form "
                        "('the <stakeholder> needs …', never 'shall')",
            layout=w.Layout(width="95%", height="120px"))
        self.extra = w.Text(
            description="Links",
            placeholder="optional k=v pairs, e.g. for_stakeholder=ops serves_goal=g1",
            layout=wide)
        self.status = w.HTML(value="")
        self.button = w.Button(description="Stage candidate", button_style="primary")
        self.button.on_click(lambda _b: self.submit())
        self.mode.observe(lambda _c: self._apply_mode(), names="value")
        self.kind.observe(lambda _c: self._refresh_existing(), names="value")
        self.existing.observe(lambda _c: self._prefill(), names="value")
        identity = w.VBox([self.kind, self.slug, self.existing, self.synthesis])
        content = w.VBox([self.label, self.description, self.extra])
        self.widget = w.VBox([self.mode, w.HTML("<b>Identity</b> (authored once)"),
                              identity, w.HTML("<b>Content</b> (freely revisable)"),
                              content, self.button, self.status])
        self.widget._cds_form = self  # headless-test handle

    @property
    def revising(self) -> bool:
        return bool(self.mode.value == "Revise existing")

    def _apply_mode(self) -> None:
        revising = self.revising
        self.slug.layout.display = "none" if revising else ""
        self.existing.layout.display = "" if revising else "none"
        self.synthesis.disabled = revising  # placement is identity: locked once created
        if revising:
            self._refresh_existing()

    def _refresh_existing(self) -> None:
        if not self.revising:
            return
        listed: Any = mcp_tools.TOOLS["cds_list"].fn(self.project, self.kind.value)
        self.existing.options = tuple(slug for slug, _label in listed)
        self._prefill()

    def _prefill(self) -> None:
        """Load the picked record's content so a revision starts from what is there."""
        if not self.revising or not self.existing.value:
            return
        from rdflib import RDFS

        from cds.core.model.instances import record_iri
        from cds.core.namespaces import CDS, DCTERMS

        g = mcp_tools._staging_graph(self.project)
        s = record_iri(self.project.base_iri, self.kind.value, str(self.existing.value))
        self.label.value = str(g.value(s, RDFS.label) or "")
        self.description.value = str(g.value(s, DCTERMS.description) or "")
        mapping = g.value(s, CDS.inSynthesis)
        self.synthesis.value = str(mapping).rsplit("/", 1)[-1] if mapping else ""

    def _extra_fields(self) -> dict[str, object]:
        fields: dict[str, object] = {}
        for pair in (self.extra.value or "").split():
            key, sep, value = pair.partition("=")
            if sep:
                fields[key] = value.split(",") if "," in value else value
        return fields

    def submit(self) -> None:
        revising = self.revising
        slug = str(self.existing.value) if revising else self.slug.value
        tool = "cds_edit" if revising else "cds_new"
        try:
            iri = mcp_tools.TOOLS[tool].fn(
                self.project, kind=self.kind.value, slug=slug,
                label=self.label.value, description=self.description.value,
                synthesis=self.synthesis.value, **self._extra_fields())
        except Exception as exc:
            self.status.value = f"<b>refused:</b> {exc}"
            return
        verb = "revised" if revising else "staged"
        self.status.value = f"{verb} <code>{slug}</code> → {iri}"
        if self.on_staged is not None:
            self.on_staged()


@dataclass(frozen=True)
class VerifyOutcome:
    conforms: bool
    findings: int
    thread_name: str


class VerifyPanel:
    """Advisory verification — tri-severity findings, computed OFF the UI thread (N7)."""

    _TIER_COLOR = {"T1": "#c0392b", "T2": "#b9770e", "T3": "#2471a3"}

    def __init__(self, project: Project) -> None:
        w = _w()
        self.project = project
        self.status = w.HTML(value="(not yet verified)")
        self.findings = w.HTML(value="")
        self.button = w.Button(description="Verify (advisory)")
        self.button.on_click(lambda _b: self.refresh())
        self.widget = w.VBox([self.button, self.status, self.findings])

    def refresh(self) -> Future[VerifyOutcome]:
        return _EXECUTOR.submit(self._run)

    def _run(self) -> VerifyOutcome:
        import threading

        result: Any = mcp_tools.TOOLS["cds_verify"].fn(self.project)
        rows = "".join(
            f'<div style="color:{self._TIER_COLOR[f.tier]}">[{f.tier}] '
            f"{f.rule}: {f.message}</div>"
            for f in result.findings
        )
        self.findings.value = rows or "<i>no findings</i>"
        verdict = "conforms" if result.conforms else "does NOT conform"
        self.status.value = (f"{verdict}: {len(result.findings)} finding(s); "
                             "advisory while composing, the commit gate decides")
        return VerifyOutcome(conforms=result.conforms, findings=len(result.findings),
                             thread_name=threading.current_thread().name)


class CommitPanel:
    """The human edge: review the change plan and commit (role-gated, K2)."""

    def __init__(self, project: Project) -> None:
        w = _w()
        self.project = project
        self.status = w.HTML(value="")
        self.button = w.Button(description="Commit to record", button_style="danger")
        self.button.on_click(lambda _b: self.commit())
        self.widget = w.VBox([self.button, self.status])

    def commit(self) -> None:
        try:
            plan: Any = mcp_tools.TOOLS["cds_commit"].fn(self.project)
        except Exception as exc:
            self.status.value = f"<b>not committed:</b> {exc}"
            return
        self.status.value = (f"committed <code>{plan['content_hash'][:12]}</code>: "
                             f"+{len(plan['adds'])} ~{len(plan['revisions'])} "
                             f"^{len(plan['supersessions'])} -{len(plan['retractions'])}"
                             + (f"; held: {len(plan['held'])}" if plan["held"] else ""))


class BriefPanel:
    """The compiled brief, current view, refreshed on demand."""

    def __init__(self, project: Project) -> None:
        w = _w()
        self.project = project
        self.output = w.HTML(value="<i>(compile to preview the brief)</i>")
        self.button = w.Button(description="Compile brief")
        self.button.on_click(lambda _b: self.refresh())
        self.widget = w.VBox([self.button, self.output])

    def refresh(self) -> None:
        md: Any = mcp_tools.TOOLS["cds_compile"].fn(self.project)
        self.output.value = f"<pre>{md}</pre>"


def build_app(project: Project) -> Any:
    """The whole app: compose → stage → verify (advisory) → compile → commit (human)."""
    from cds.core.usertext import STAGED_COUNT_NOTE

    w = _w()
    banner = w.HTML()

    def refresh_banner() -> None:
        n = staged_count(project)
        banner.value = (f"<b>{n} staged, uncommitted.</b> "
                        f"<small>{STAGED_COUNT_NOTE}</small>")

    form = RecordForm(project, on_staged=refresh_banner)
    verify_panel = VerifyPanel(project)
    brief = BriefPanel(project)
    commit_panel = CommitPanel(project)
    refresh_banner()
    header = w.HTML(
        "<h2>Concept Definition</h2>"
        "<p>Candidates stage in your session; nothing reaches the durable record "
        "until a reviewer commits. Verification is advisory while you compose.</p>")
    # the right column follows the flow: verify, then compile, then (last, red) commit
    return w.VBox([
        header, banner,
        w.HBox([form.widget, w.VBox([verify_panel.widget, brief.widget,
                                     commit_panel.widget])]),
    ])
