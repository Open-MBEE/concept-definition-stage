<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Facilitator service (`cds-serve`)

> **Honest limits (P1):** no authentication yet (P6); no automated session staging (P2);
> `cds_commit` returns 403 until the K2 gate lands (P2); the AICC/LLM sidecar is P4 —
> what runs today is the non-LLM substance. Never expose beyond localhost before P6.

The facilitator service is the **correct-by-construction authoring surface**: it *creates*
conforming models, where the [oracle](conformance-oracle.md) only checks them. The posture is
"e-bike-style" facilitation — the human steers, the service assists — and the substance is
the constrained authoring protocol, not the LLM:

- **One route per whitelisted tool** (`POST /tools/<name>`): the same K1 registry the MCP
  server mounts — one whitelist, two transports, drift-guarded on both.
- **Pydantic-gated candidate writes**: request schemas derive from the registry signatures;
  a malformed or deep-invalid record is a 422, and valid writes land as candidates in the
  bound session staging project — never canonical state.
- **Graded strictness**: `POST /tools/cds_verify` returns advisory tri-severity findings
  while you compose (intermediate invalid states are expected and allowed); only the commit
  gate blocks, and that gate is *human* (K2, validation — "build the right thing").
- **Escalate, never invent**: `cds_queue_add` files a retrieval item when canon is
  unsecured — the mandated dead-end that makes fabrication a structural impossibility.

`GET /manifest` returns the served whitelist; `GET /healthz` liveness. Swagger UI at `/docs`
when running; the committed spec is [`openapi-facilitator.json`](openapi-facilitator.json)
(drift-checked byte-identically by `tests/unit/test_facilitator_api.py`).

## Running

```bash
pip install "cds[facilitator]"
cds-serve --project /path/to/staging-root   # loopback bind by default
```

## The P4 layer

The AICC loop (Ask → Ingest → Confirm → Conform) and the LLM sidecar arrive in P4 **as a UX
affordance over this same API** — the agent translates natural language into these typed
routes and renders results back; it never gains an affordance this API doesn't have.
Bring-your-own-LLM is an operator deployment variable (spec ADR-8): one OpenAI-compatible
endpoint triplet (`base_url`, `model`, `api_key`); end users never see a model picker.

## Related docs

[MCP server](mcp-server.md) · [MCP manifest (generated)](mcp-manifest.md) ·
[Conformance oracle](conformance-oracle.md) · [Model store](model-store.md) ·
[Architecture spec](../architecture/cds-web-app.md) · [Factoring](../architecture/factoring.md)
