<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Hosting locally (T8b) — cds + your own LLM, no infrastructure

The tool boundary is the product: `pip install "cds[mcp]"` gives you the reusable,
whitelisted tool server, and the model lives wherever you already run one.

## Path 1 — your MCP client brings the model (zero LLM config in cds)

```bash
pip install "cds[mcp]"
cds init ~/my-analysis
claude mcp add cds -- cds-mcp --project ~/my-analysis
```

Any MCP host works (Claude Code/Desktop, a local Ollama-backed host, …): the model reaches
exactly the 15+2 whitelisted tools ([manifest](services/mcp-manifest.md)) — candidates
only; committing needs a human with the reviewer role.

## Path 2 — the facilitation service + a local model (ADR-8 triplet)

```bash
pip install "cds[facilitator]"
CDS_LLM_BASE_URL="http://localhost:11434/v1" CDS_LLM_MODEL="llama3.1" CDS_LLM_API_KEY="ollama" \
  cds-serve --canonical ~/my-analysis --role cds-reviewer --approver "https://example.org/you"
```

`POST /chat` runs the AICC loop with the mechanical guards (unknown tools refused;
unsecured canon → retrieval queue dead-end); `/tools/*` and Swagger at `/docs` work with or
without a model. See [the playground](playground.md) for the full local loop including the
commit gate, provenance, and audit-chain verification.

## Related docs

[Playground](playground.md) · [MCP server](services/mcp-server.md) ·
[Facilitator](services/facilitator.md) · [Web hosting](hosting-web.md)
