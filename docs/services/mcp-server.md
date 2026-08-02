<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# MCP tool server (`cds-mcp`)

> **Honest limits (P1):** no authentication yet (arrives at P6 via the app tier); no
> automated session staging yet (arrives at P2 — you point the server at a staging project
> root yourself); `cds_commit` always refuses (the K2 commit gate lands in P2).

The MCP server is the **LLM-facing transport** of the cds tool boundary (constraint K1). It
is a *text-in/text-out protocol endpoint*: an MCP client (an LLM orchestrator such as Claude
Code/Desktop, or any local MCP host) speaks JSON tool calls over stdio, and the server's
manifest — exactly the 15 whitelisted tools, [generated reference](mcp-manifest.md) — is the
model's **entire reachable surface**. There is no code, file, network, or shell tool, and the
server refuses to start if the served manifest drifts from the committed whitelist.

## What it composes

The server is a thin mount over three components, joined by contracts
(see [factoring](../architecture/factoring.md)):

- the **authoring package** (`cds.core.authoring`, in-process) — every write tool produces
  **candidates** in the session staging project, never canonical state;
- the **conformance oracle** (via `cds.contracts.ConformanceOracle`; in-process default) —
  `cds_verify` returns advisory tri-severity findings;
- the **model store** (via `cds.contracts.ModelStore`) — session staging binds it in P2.

## Running

```bash
pip install "cds[mcp]"
cds-mcp --project /path/to/staging-root
```

Bring-your-own-LLM is **by construction** on this path: the model lives in whichever MCP
client connects; cds holds no LLM credential (spec ADR-8).

### What the whitelist does and does not confine

The K1 whitelist confines **what this server exposes** — nothing here can run code,
touch files, or reach the network. It does **not** confine an *agentic* client: a full
coding agent pointed at this server brings its own shell and file tools entirely outside
this boundary (live-QA 2026-08-02, Probe A: 22 agent-side shell calls alongside correct
cds tool use). The structural guarantee an operator can rely on is therefore layered:

- **the served surface** — only the 17 whitelisted tools, on every client;
- **the commit gate** — the sole path into the durable record: human role (K2), full
  verification, and an **unverified-source hold** — a staged record citing an unresolved
  source is excluded from the commit and enumerated in the change plan until a human
  secures the source or explicitly includes it (`include_unverified`, recorded in the
  audit log);
- **the constrained apps** (the Voila web app) — no agent-side tools exist at all.

The anti-fabrication *conversation* guard (escalate to the retrieval queue, then stop)
lives in the facilitator's AICC loop; on raw MCP the gate hold above is the enforcement
point. In short: the whitelist bounds the surface, the gate bounds the record.

## Related docs

[MCP manifest (generated)](mcp-manifest.md) · [Facilitator service](facilitator.md) ·
[Conformance oracle](conformance-oracle.md) · [Model store](model-store.md) ·
[Architecture spec](../architecture/cds-web-app.md) · [Factoring](../architecture/factoring.md)
