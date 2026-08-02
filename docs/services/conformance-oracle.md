<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Conformance oracle (`cds-oracle`)

> **Honest limits (P1):** no authentication yet (P6) — loopback bind by default; never
> expose beyond localhost before then. In-process consumers use the
> `cds.contracts.ConformanceOracle` seam directly; the HTTP client implementation of that
> seam is deferred (spec §11 D8) until a consumer runs out-of-process.

The oracle is the **stateless verification service**: a model *instance* (Turtle) goes in, a
conformance verdict against the model *family* comes out — with **granular findings for
remediation**. Each finding carries the named `rule` (a stable shape identity), the `focus`
node it fired on, an authored `message`, and the tier (`T1` violation / `T2` warning / `T3`
info). The oracle never authors, never stores, and never judges fitness for purpose.

**Verification ≠ validation.** The oracle answers the machine question — *"did we build it
right?"* (structure, grounding, construction-order preconditions). *"Did we build the right
thing?"* is validation, which is irreducibly human and lives at the K2 commit gate. Conflating
the two in either direction is a design error; during composition the oracle's findings are
**advisory** (the [facilitator](facilitator.md) tolerates intermediate invalid states), and
only the commit gate blocks.

## Surface

Exactly three routes (drift-guarded by `tests/unit/test_oracle_api.py`):

| Route | What |
|---|---|
| `POST /verify` | `{"turtle": "...", "check_conflicts": true}` → `{"conforms": bool, "findings": [{tier, severity, rule, focus, message}]}`; unparseable Turtle → `400` with the parser's reason |
| `GET /rules` | the named rule identities findings refer to — the remediation cross-reference |
| `GET /healthz` | liveness |

Swagger UI at `/docs`; the committed spec is [`openapi-oracle.json`](openapi-oracle.json)
(drift-checked byte-identically).

## Running

```bash
pip install "cds[oracle]"
cds-oracle           # 127.0.0.1:8801
```

## Related docs

[Facilitator service](facilitator.md) · [MCP server](mcp-server.md) ·
[Model store](model-store.md) · [Architecture spec](../architecture/cds-web-app.md) ·
[Factoring](../architecture/factoring.md)
