<!-- GENERATED — do not edit. Regenerate: `uv run python -m cds.mcp.manifest_doc`
     (drift-checked by tests/unit/test_docs_drift.py). -->

# MCP tool manifest (K1 whitelist)

The MCP endpoint (`cds-mcp`) is a **text-in/text-out protocol surface**: an LLM orchestrator
speaks JSON tool calls over stdio, and the tools below are its **entire reachable surface**
(constraint K1 — no code, file, network, or shell affordance exists). Write tools produce
**candidates** into the session staging project, never canonical state; `cds_commit` is the
sole canonical path and refuses until the human-validated K2 gate (P2). The same registry is
mounted over HTTP by the facilitator service (`cds-serve`) — one whitelist, two transports.

| Tool | Effect | Arguments | Wraps | Description |
|---|---|---|---|---|
| `cds_commit` | candidate write | `—` | `cds.mcp.tools` | Merge staging into canonical (K2 gate; requires cds-reviewer). |
| `cds_compile` | read-only | `—` | `cds.mcp.tools` | Compile the staging graph to a Markdown brief; preview only. |
| `cds_edit` | candidate write | `kind, slug, label, description, synthesis, **kind-specific fields` | `cds.mcp.tools` | Edit an EXISTING staged record in place (scratch mode); refuses an absent slug — use cds_new to create one. |
| `cds_explain` | read-only | `name` | `cds.mcp.tools` | Explain a cds concept or record kind (read-only guidance). |
| `cds_list` | read-only | `kind` | `cds.mcp.tools` | List records of a kind in the session staging project (slug, label). |
| `cds_new` | candidate write | `kind, slug, label, description, synthesis, **kind-specific fields` | `cds.mcp.tools` | Create a NEW record of a kind (candidate into staging); refuses an existing slug — use cds_edit to change one. |
| `cds_park_add` | candidate write | `slug, label, description='', note=''` | `cds.mcp.tools` | Park an out-of-scope idea (kept, not dropped). |
| `cds_queue_add` | candidate write | `slug, question, description=''` | `cds.mcp.tools` | File a retrieval item — the mandated dead-end on unsecured canon. |
| `cds_queue_set` | candidate write | `slug, status, locator=None` | `cds.mcp.tools` | Advance a retrieval item's status (pending/provided/verified). |
| `cds_show` | read-only | `kind, slug` | `cds.mcp.tools` | Show one staged record by kind and slug. |
| `cds_synthesis` | candidate write | `slug, title, description=''` | `cds.mcp.tools` | Create/update the Synthesis (candidate into staging). |
| `cds_tension_add` | candidate write | `slug, label, description='', between=None` | `cds.mcp.tools` | Record a named tension between records (surfaced, not hidden). |
| `cds_tension_resolve` | candidate write | `slug` | `cds.mcp.tools` | Mark a tension resolved. |
| `cds_verify` | read-only | `check_conflicts=True` | `cds.mcp.tools` | Verify the staging graph — tri-severity findings; preview only. |
| `cds_waive` | candidate write | `waiver_id, rule, reason, focus=None, by=None` | `cds.mcp.tools` | Waive a T2/T3 finding with a reason (append-only; T1 refused). |

Served manifest: 15 tools — drift-guarded at serve time (`cds.mcp.server.list_tools`) and by `tests/unit/test_mcp_whitelist.py`.
