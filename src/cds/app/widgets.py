"""The app tier's widget UI (T3) — forms and panels over the SAME constrained session.

Every interaction goes through the K1 registry (``cds.mcp.tools``) exactly like the HTTP
and MCP transports — the UI adds no affordance the boundary lacks, and deliberately offers
**no code surface** (REQ-K3.1, guarded by ``tests/app/test_no_code_widget``). Advisory
verification runs OFF the UI thread (REQ-N7.1) so authoring never blocks on SHACL.

ipywidgets is imported lazily so the module (and autodoc) loads on a lean install; the
factories are headless-testable — they build widget trees without a display.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from cds.core.workspace import Project
from cds.mcp import tools as mcp_tools

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cds-verify")


def _w() -> Any:
    import ipywidgets  # type: ignore[import-not-found]  # app extra; lazy by design

    return ipywidgets


def build_synthesis(project: Project, *, slug: str, title: str) -> str:
    """Convenience used by the app's first-run flow and tests."""
    return str(mcp_tools.TOOLS["cds_synthesis"].fn(project, slug=slug, title=title))


class RecordForm:
    """Author one record — kind-aware fields, Pydantic-gated on submit (candidates only)."""

    def __init__(self, project: Project) -> None:
        from cds.core.model.instances import AUTHORABLE_KINDS

        w = _w()
        self.project = project
        self.kind = w.Dropdown(options=list(AUTHORABLE_KINDS), description="Kind")
        self.slug = w.Text(description="Slug", placeholder="kebab-case-id")
        self.label = w.Text(description="Label", placeholder="Short name")
        self.description = w.Textarea(
            description="Statement",
            placeholder="The content statement — for a need, use need-form "
                        "('the <stakeholder> needs …', never 'shall')")
        self.synthesis = w.Text(description="Mapping", placeholder="synthesis slug")
        self.extra = w.Text(
            description="Links",
            placeholder="optional k=v pairs, e.g. for_stakeholder=ops serves_goal=g1")
        self.status = w.HTML(value="")
        self.button = w.Button(description="Stage candidate", button_style="primary")
        self.button.on_click(lambda _b: self.submit())
        self.widget = w.VBox([self.kind, self.slug, self.label, self.description,
                              self.synthesis, self.extra, self.button, self.status])

    def _extra_fields(self) -> dict[str, object]:
        fields: dict[str, object] = {}
        for pair in (self.extra.value or "").split():
            key, sep, value = pair.partition("=")
            if sep:
                fields[key] = value.split(",") if "," in value else value
        return fields

    def submit(self) -> None:
        try:
            iri = mcp_tools.TOOLS["cds_new"].fn(
                self.project, kind=self.kind.value, slug=self.slug.value,
                label=self.label.value, description=self.description.value,
                synthesis=self.synthesis.value, **self._extra_fields())
        except Exception as exc:
            self.status.value = f"<b>refused:</b> {exc}"
            return
        self.status.value = f"staged <code>{self.slug.value}</code> → {iri}"


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
        self.status.value = (f"{verdict} — {len(result.findings)} finding(s); "
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
        self.status.value = (f"committed <code>{plan['content_hash'][:12]}</code> — "
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
    """The whole app: author → verify (advisory) → preview → commit (human)."""
    w = _w()
    form = RecordForm(project)
    verify_panel = VerifyPanel(project)
    brief = BriefPanel(project)
    commit_panel = CommitPanel(project)
    header = w.HTML(
        "<h2>Concept Definition</h2>"
        "<p>Candidates stage in your session; nothing reaches the durable record "
        "until a reviewer commits. Verification is advisory while you compose.</p>")
    return w.VBox([
        header,
        w.HBox([form.widget, w.VBox([verify_panel.widget, brief.widget,
                                     commit_panel.widget])]),
    ])
