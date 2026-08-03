"""Generate the MCP tool-manifest documentation — committed at ``docs/services/mcp-manifest.md``.

Deterministic Markdown from the transport-neutral registry; ``tests/unit/test_docs_drift.py``
fails on drift (the same discipline as the TTL determinism gate). Regenerate with::

    uv run python -m cds.mcp.manifest_doc
"""

from __future__ import annotations

import inspect
from pathlib import Path

from cds.mcp import server, tools

_HEADER = """\
<!-- GENERATED — do not edit. Regenerate: `uv run python -m cds.mcp.manifest_doc`
     (drift-checked by tests/unit/test_docs_drift.py). -->

# MCP tool manifest (K1 whitelist)

The MCP endpoint (`cds-mcp`) is a **text-in/text-out protocol surface**: an LLM orchestrator
speaks JSON tool calls over stdio, and the tools below are its **entire reachable surface**
(constraint K1 — no code, file, network, or shell affordance exists). Write tools produce
**candidates** into the session staging project, never canonical state; `cds_commit` is the
sole canonical path and refuses until the human-validated K2 gate (P2). The same registry is
mounted over HTTP by the facilitator service (`cds-serve`) — one whitelist, two transports.
"""


def _args_of(fn: object) -> str:
    parts: list[str] = []
    for name, param in inspect.signature(fn).parameters.items():  # type: ignore[arg-type]
        if name == "project":
            continue  # bound server-side to the session staging project
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            parts.append("**kind-specific fields")
            continue
        if param.default is inspect.Parameter.empty:
            parts.append(name)
        else:
            parts.append(f"{name}={param.default!r}")
    return ", ".join(parts) if parts else "—"


def manifest_markdown() -> str:
    lines = [_HEADER]
    lines.append("| Tool | Effect | Arguments | Wraps | Description |")
    lines.append("|---|---|---|---|---|")
    for name in sorted(tools.TOOLS):
        spec = tools.TOOLS[name]
        effect = "candidate write" if spec.writes else "read-only"
        wraps = spec.fn.__module__
        lines.append(f"| `{spec.name}` | {effect} | `{_args_of(spec.fn)}` | `{wraps}` "
                     f"| {spec.description} |")
    lines.append("")
    lines.append(f"Served manifest: {len(server.WHITELIST)} tools — drift-guarded at serve "
                 "time (`cds.mcp.server.list_tools`) and by `tests/unit/test_mcp_whitelist.py`.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    repo_root = Path(__file__).parents[3]  # src/cds/mcp/ -> repo
    out = repo_root / "docs" / "services" / "mcp-manifest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(manifest_markdown(), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
