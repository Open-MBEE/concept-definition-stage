"""`cds-mcp` server entrypoint — P1 deliverable (K1)."""
from __future__ import annotations

WHITELIST: tuple[str, ...] = (
    "cds_explain", "cds_list", "cds_show",
    "cds_verify", "cds_compile",
    "cds_synthesis", "cds_new", "cds_edit",
    "cds_queue_add", "cds_queue_set", "cds_park_add",
    "cds_tension_add", "cds_tension_resolve",
    "cds_waive", "cds_commit",
)
FORBIDDEN: frozenset[str] = frozenset(
    {"run_python", "exec", "eval", "read_file", "write_file", "shell", "http_get"}
)


def list_tools() -> list[str]:
    """Names the running server actually serves. P1: implement (docs 8.1)."""
    raise NotImplementedError("P1: implement the MCP tool manifest (K1)")


def main() -> None:
    raise NotImplementedError("P1: implement the `cds-mcp` server entrypoint")
