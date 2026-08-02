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


def main() -> None:
    raise NotImplementedError("P1: implement the `cds-mcp` server entrypoint")
