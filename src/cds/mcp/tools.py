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
from cds.core.authoring import list_records, project_graph, show_record
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
