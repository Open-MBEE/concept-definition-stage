"""`cds-mcp` server entrypoint — the K1 tool boundary as an MCP/stdio transport.

The ``mcp`` SDK is imported lazily inside :func:`build_server`/:func:`main` so that
``pip install cds`` (and this module's import, autodoc, and the manifest tests) need no MCP
dependency. The served manifest is drift-guarded: :func:`list_tools` refuses any mismatch
with :data:`WHITELIST` before a server is ever built.
"""
from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # lazy SDK — type-only import
    from cds.core.workspace import Project

WHITELIST: tuple[str, ...] = (
    "cds_explain", "cds_list", "cds_show",
    "cds_verify", "cds_compile",
    "cds_synthesis", "cds_new", "cds_edit",
    "cds_discard", "cds_retract",
    "cds_queue_add", "cds_queue_set", "cds_park_add",
    "cds_tension_add", "cds_tension_resolve",
    "cds_waive", "cds_commit",
)
FORBIDDEN: frozenset[str] = frozenset(
    {"run_python", "exec", "eval", "read_file", "write_file", "shell", "http_get"}
)


def list_tools() -> list[str]:
    """Names the running server actually serves — MUST equal WHITELIST (K1).

    This is also the manifest-drift guard: both transports (``cds-mcp`` and the facilitator's
    ``cds-serve``) call it before serving and refuse to start on any mismatch.
    """
    from cds.mcp import tools

    served = sorted(tools.registered())
    if served != sorted(WHITELIST):
        raise RuntimeError(f"manifest drift: served {served} != whitelist {sorted(WHITELIST)}")
    if not FORBIDDEN.isdisjoint(served):
        raise RuntimeError("forbidden tool present in manifest (K1/K3)")
    return served


def _bind_project(fn: Any, project: Project, tool_name: str) -> Any:
    """Close over ``project`` and re-sign the wrapper so the SDK derives the arg schema
    from the tool's remaining (client-facing) parameters. Every call is appended to the
    session's hash-chained audit log (K4.2), refusals included."""
    from cds.mcp.provenance import AuditLog

    audit = AuditLog(project.root / "audit.jsonl")
    sig = inspect.signature(fn)
    params = [p for name, p in sig.parameters.items() if name != "project"]

    def bound(*args: Any, **kwargs: Any) -> Any:
        try:
            result = fn(project, *args, **kwargs)
        except Exception as exc:
            audit.append({"action": "tool", "tool": tool_name,
                          "status": type(exc).__name__})
            raise
        audit.append({"action": "tool", "tool": tool_name, "status": "ok"})
        return result

    bound.__signature__ = sig.replace(parameters=params)  # type: ignore[attr-defined]
    bound.__doc__ = fn.__doc__
    bound.__name__ = getattr(fn, "__name__", "tool")
    return bound


def build_server(project: Project) -> Any:
    """Build the MCP server over the transport-neutral registry (lazy SDK import).

    Supports both SDK generations behind ``mcp>=1.0``: ``MCPServer`` (mcp 2.x) and its
    predecessor ``FastMCP`` (mcp 1.x) share the ``add_tool``/``list_tools``/``run`` surface.
    """
    try:
        from mcp.server.mcpserver import MCPServer  # mcp >= 2.0
    except ImportError:  # pragma: no cover — mcp 1.x fallback
        from mcp.server.fastmcp import (  # type: ignore[no-redef,import-not-found]
            FastMCP as MCPServer,
        )

    from cds.mcp import tools

    list_tools()  # manifest drift guard — refuse to build a non-whitelist server
    srv = MCPServer("cds")
    for spec in tools.TOOLS.values():
        srv.add_tool(_bind_project(spec.fn, project, spec.name), name=spec.name,
                     description=spec.description)
    return srv


def main() -> None:
    import argparse
    from pathlib import Path

    from cds.core.workspace import load_project

    ap = argparse.ArgumentParser(
        prog="cds-mcp",
        description="cds MCP tool server — serves exactly the K1 whitelist; "
                    "writes are candidates into the session staging project.",
    )
    ap.add_argument("--project", type=Path, default=None,
                    help="Explicit staging root (default: fresh session when --canonical "
                         "is given, else CDS_PROJECT / cwd discovery).")
    ap.add_argument("--canonical", type=Path, default=None,
                    help="Canonical record root — enables the overlay read model and the "
                         "commit gate (K2).")
    ap.add_argument("--role", action="append", default=None,
                    help="Grant a role to this session (repeatable), e.g. cds-reviewer.")
    ap.add_argument("--approver", default=None,
                    help="Approver IRI recorded on committed change plans.")
    args = ap.parse_args()
    from cds.mcp import staging, tools

    canon = load_project(explicit=args.canonical) if args.canonical is not None else None
    tools.SESSION.canonical = canon
    tools.SESSION.roles = frozenset(args.role or ())
    tools.SESSION.approver = args.approver
    if args.project is not None:
        session = load_project(explicit=args.project)
    elif canon is not None:
        session = staging.new_session_project(canon.base_iri)
    else:
        session = load_project()
    build_server(session).run()
