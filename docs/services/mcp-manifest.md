<!-- GENERATED — do not edit. Regenerate: `uv run python -m cds.mcp.manifest_doc`
     (drift-checked by tests/unit/test_docs_drift.py). -->

# MCP tool manifest (K1 whitelist)

The MCP endpoint (`cds-mcp`) is a **text-in/text-out protocol surface**: an LLM orchestrator
speaks JSON tool calls over stdio, and the tools below are its **entire reachable surface**
(constraint K1 — no code, file, network, or shell affordance exists). Write tools produce
**candidates** into the session staging project, never canonical state; `cds_commit` is the
sole canonical path and refuses until the human-validated K2 gate (P2). The same registry is
mounted over HTTP by the facilitator service (`cds-serve`) — one whitelist, two transports.

Each tool's **mode** is its deontic class (ADR-9): `read` observes; `scratch` mutates the
session working copy only; `append` expresses durable-record intent by adding triples
(never removing); `commit` is the sole scratch→durable boundary.

| Tool | Mode | Arguments | Wraps | Description |
|---|---|---|---|---|
| `cds_commit` | commit | `—` | `cds.mcp.tools` | Merge staging into canonical through the K2 gate (requires the cds-reviewer role bound at server start); returns the executed change plan. |
| `cds_compile` | read | `synthesis=None, include_history=False` | `cds.mcp.tools` | Compile the staging graph to a Markdown brief; preview only. Scope to one mapping with synthesis=<slug>; include_history adds the superseded/retracted appendix. |
| `cds_discard` | scratch | `kind, slug` | `cds.mcp.tools` | Delete a staged candidate or ledger item from the working copy — scratch only, can never touch canonical state. |
| `cds_edit` | scratch | `kind, slug, label, description, synthesis, **kind-specific fields` | `cds.mcp.tools` | Edit an EXISTING staged record in place (scratch mode); refuses an absent slug — use cds_new to create one. |
| `cds_explain` | read | `name` | `cds.mcp.tools` | Explain a cds concept or record kind (read-only guidance). |
| `cds_list` | read | `kind` | `cds.mcp.tools` | List records of a kind visible to this session — staged candidates overlaid on the canonical current view (slug, label). |
| `cds_new` | scratch | `kind, slug, label, description, synthesis, **kind-specific fields` | `cds.mcp.tools` | Create a NEW record of a kind (candidate into staging); refuses an existing slug — use cds_edit to change one. |
| `cds_park_add` | scratch | `slug, label, description='', note=''` | `cds.mcp.tools` | Park an out-of-scope idea (kept, not dropped). |
| `cds_queue_add` | scratch | `slug, question, description=''` | `cds.mcp.tools` | File a retrieval item — the mandated dead-end on unsecured canon. |
| `cds_queue_set` | scratch | `slug, status, locator=None` | `cds.mcp.tools` | Advance a retrieval item's status (pending/provided/verified). |
| `cds_retract` | append | `kind, slug, reason=None` | `cds.mcp.tools` | Stage an append-only retraction (ADR-9): the record leaves the current view; its content and history are preserved. |
| `cds_show` | read | `kind, slug` | `cds.mcp.tools` | Show one record visible to this session (staged copy wins). |
| `cds_synthesis` | scratch | `slug, title, description=''` | `cds.mcp.tools` | Create/update the Synthesis (candidate into staging). |
| `cds_tension_add` | scratch | `slug, label, description='', between=None` | `cds.mcp.tools` | Record a named tension between records (surfaced, not hidden). |
| `cds_tension_resolve` | scratch | `slug` | `cds.mcp.tools` | Mark a tension resolved. |
| `cds_verify` | read | `check_conflicts=True` | `cds.mcp.tools` | Verify the staging graph — tri-severity findings; preview only. |
| `cds_waive` | append | `waiver_id, rule, reason, focus=None, by=None` | `cds.mcp.tools` | Waive a T2/T3 finding with a reason (append-only; T1 refused). |

Served manifest: 17 tools — drift-guarded at serve time (`cds.mcp.server.list_tools`) and by `tests/unit/test_mcp_whitelist.py`.
