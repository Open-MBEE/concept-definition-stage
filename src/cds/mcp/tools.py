"""Typed wrappers over cds.core (authoring/verify/explain/compile) — the K1 tool boundary.

Each tool maps to one real cds function and produces CANDIDATES only (never canonical state):
every write goes through ``cds.core.authoring`` into the session staging ``Project`` passed as
the tool's first argument. ``cds_commit`` — the sole path to canonical state — refuses until the
K2 commit gate lands (P2).

This module is the **transport-neutral registry** (see docs/architecture/factoring.md): it is
mounted by both the MCP server (``cds.mcp.server``) and the REST service (``cds.service.app``)
and must never import a transport SDK (``mcp``, ``fastapi``) — that rule is enforced by
``tests/unit/test_factoring.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rdflib import Graph

from cds.core import compile as compile_mod
from cds.core import explain as explain_mod
from cds.core.authoring import (
    create_parked,
    create_queue_item,
    create_record,
    create_synthesis,
    create_tension,
    list_records,
    project_graph,
    set_queue_status,
    set_tension_status,
    show_record,
)
from cds.core.model.instances import Synthesis, model_for_kind
from cds.core.model.notes import (
    ParkedItem,
    RetrievalItem,
    RetrievalStatus,
    Tension,
    TensionStatus,
)
from cds.core.verify import VerifyResult, verify
from cds.core.workspace import Project


@dataclass(frozen=True)
class ToolSpec:
    """One whitelisted tool: its name, callable, human description, and write/read effect."""

    name: str
    fn: Callable[..., object]
    description: str
    writes: bool


TOOLS: dict[str, ToolSpec] = {}


def _tool(
    name: str, description: str, *, writes: bool = False
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    def register(fn: Callable[..., object]) -> Callable[..., object]:
        TOOLS[name] = ToolSpec(name=name, fn=fn, description=description, writes=writes)
        return fn

    return register


def registered() -> tuple[str, ...]:
    """The names this registry actually holds — the served manifest derives from this."""
    return tuple(TOOLS)


def _staging_graph(project: Project) -> Graph:
    return project_graph(project)


# ---------------------------------------------------------------------------- read / preview


@_tool("cds_explain", "Explain a cds concept or record kind (read-only guidance).")
def cds_explain(project: Project, name: str) -> list[str] | None:
    return explain_mod.explain(name)


@_tool("cds_list", "List records of a kind in the session staging project (slug, label).")
def cds_list(project: Project, kind: str) -> list[tuple[str, str]]:
    return list_records(project, kind)


@_tool("cds_show", "Show one staged record by kind and slug.")
def cds_show(project: Project, kind: str, slug: str) -> list[str] | None:
    return show_record(project, kind, slug)


@_tool("cds_verify", "Verify the staging graph — tri-severity findings; preview only.")
def cds_verify(project: Project, check_conflicts: bool = True) -> VerifyResult:
    return verify(_staging_graph(project), check_conflicts=check_conflicts)


@_tool("cds_compile", "Compile the staging graph to a Markdown brief; preview only.")
def cds_compile(project: Project) -> str:
    return compile_mod.compile_brief(_staging_graph(project), base=project.base_iri)


# ------------------------------------------------------------------- candidate writes (staging)


def _upsert(project: Project, kind: str, slug: str, label: str, description: str,
            synthesis: str, fields: dict[str, object]) -> str:
    """Pydantic (``model_for_kind``) is the structural guardrail — bad args raise an error."""
    payload: dict[str, object] = {"slug": slug, "kind": kind, "label": label,
                                  "description": description, "synthesis": synthesis, **fields}
    rec = model_for_kind(kind).model_validate(payload)
    return str(create_record(project, rec))


@_tool("cds_synthesis", "Create/update the Synthesis (candidate into staging).", writes=True)
def cds_synthesis(project: Project, slug: str, title: str, description: str = "") -> str:
    return str(create_synthesis(project, Synthesis(slug=slug, title=title,
                                                   description=description)))


@_tool("cds_new", "Create a record of a kind (candidate into staging).", writes=True)
def cds_new(project: Project, kind: str, slug: str, label: str, description: str,
            synthesis: str, **fields: object) -> str:
    return _upsert(project, kind, slug, label, description, synthesis, fields)


@_tool("cds_edit", "Upsert an existing record (candidate; merges into staging).", writes=True)
def cds_edit(project: Project, kind: str, slug: str, label: str, description: str,
             synthesis: str, **fields: object) -> str:
    # Same core call as cds_new (create_record upserts); a distinct tool name because *edit*
    # is a distinct intent — it is what facilitator prompts and the audit log key on.
    return _upsert(project, kind, slug, label, description, synthesis, fields)


# --------------------------------------------------------------------------- session ledgers


@_tool("cds_queue_add", "File a retrieval item — the mandated dead-end on unsecured canon.",
       writes=True)
def cds_queue_add(project: Project, slug: str, question: str, description: str = "") -> str:
    return str(create_queue_item(project, RetrievalItem(slug=slug, question=question,
                                                        description=description)))


@_tool("cds_queue_set", "Advance a retrieval item's status (pending/provided/verified).",
       writes=True)
def cds_queue_set(project: Project, slug: str, status: str,
                  locator: str | None = None) -> None:
    set_queue_status(project, slug, RetrievalStatus(status), locator=locator)


@_tool("cds_park_add", "Park an out-of-scope idea (kept, not dropped).", writes=True)
def cds_park_add(project: Project, slug: str, label: str, description: str = "",
                 note: str = "") -> str:
    return str(create_parked(project, ParkedItem(slug=slug, label=label,
                                                 description=description, note=note)))


@_tool("cds_tension_add", "Record a named tension between records (surfaced, not hidden).",
       writes=True)
def cds_tension_add(project: Project, slug: str, label: str, description: str = "",
                    between: list[str] | None = None) -> str:
    return str(create_tension(project, Tension(slug=slug, label=label, description=description,
                                               between=between or [])))


@_tool("cds_tension_resolve", "Mark a tension resolved.", writes=True)
def cds_tension_resolve(project: Project, slug: str) -> None:
    set_tension_status(project, slug, TensionStatus.RESOLVED)
