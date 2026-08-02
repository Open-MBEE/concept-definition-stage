<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Factoring — the splittability contract

**Status:** normative for the monorepo · guards executed by `tests/unit/test_factoring.py`
(never a claim without an executing guard).

This monorepo is factored so that each component is a **would-be distribution**: a later
split into sibling packages/services (spec §11 D6) requires packaging changes only — no code
motion. The mechanism is `cds.contracts`: every cross-component call goes through a typed
Protocol there, never a direct sibling import; transport and LLM SDKs are lazy, in-function
imports, so every module imports (and autodocs) on a lean install.

## Component index

| Component | Package | Surface | One-paragraph role |
|---|---|---|---|
| **Modeling family** | `cds.core` + `cds.stages` | `cds` CLI | The model family (SKOS+PROV ontology, SHACL shapes, Pydantic guardrails) and the CLIs to build and check models against it. Frozen contracts: `verify()` (ADR-7c) with the internal `VerifierBackend` seam; `canonical_turtle` determinism. Unchanged by the app work. |
| **Contracts** | `cds.contracts` | (library) | The modularity keystone: `ConformanceOracle` (+ `InProcessOracle` reference) and `ModelStore` (= `cds.core.flexo.FlexoBackend`). Imports only `cds.core`. |
| **Conformance oracle** | `cds.oracle` | `cds-oracle` · extra `oracle` | Stateless verification service: model instance in → verdict + granular findings out ("build it right", machine). [Docs](../services/conformance-oracle.md). |
| **Facilitator** | `cds.facilitator` | `cds-serve` · extra `facilitator` | Correct-by-construction authoring service over the K1 registry (P1, non-LLM substance); P4 layers the AICC/LLM sidecar as UX. [Docs](../services/facilitator.md). |
| **Model datastore** | contract only (P1) | Flexo MMS target (T6) | Per-branch model-instance storage behind `ModelStore`; git-TTL is the durable record until T6. [Docs](../services/model-store.md). |
| **MCP tool server** | `cds.mcp` | `cds-mcp` · extra `mcp` | The K1 whitelist as an MCP/stdio transport; `cds.mcp.tools` is the **transport-neutral registry** both transports mount. [Docs](../services/mcp-server.md). |
| **Web app** | `cds.app` | (P5/P6) | Jupyter/Voilà front end driving the facilitator service. |
| **Deploy** | `deploy/` | (infra-as-code) | Traefik/JupyterHub/Keycloak composition — versioned in the monorepo, never shipped in the wheel. |

Process-grammar mapping (eBike lifecycle vocabulary): `Q` (query/lookup) = datastore,
`DC` (deterministic compute) = oracle, `LLM` + `HI` (human input) = facilitator/web app.

## Dependency direction (enforced)

```
cds.core  ←  cds.contracts  ←  { cds.mcp , cds.oracle }
                                    ↑
                              cds.facilitator  ←  cds.app (P5)
```

| Rule | Enforced by |
|---|---|
| `cds.core` imports nothing above it | `test_factoring.py` |
| `cds.contracts` imports only `cds.core`; no SDKs | `test_factoring.py` |
| `cds.mcp.tools` (the registry) imports no transport SDK, ever | `test_factoring.py` |
| `cds.oracle` never imports `cds.mcp`; `cds.facilitator` never imports `cds.oracle` — siblings couple only via `cds.contracts` | `test_factoring.py` |
| `cds.facilitator` MAY import `cds.mcp` (the registry it mounts) | (allowed edge) |
| Transport/LLM SDKs (`mcp`, `fastapi`, `uvicorn`, `anthropic`, `instructor`) are lazy in-function imports | `test_factoring.py` |
| Served surfaces cannot drift from the whitelist | `test_mcp_whitelist.py`, `test_facilitator_api.py`, `test_oracle_api.py` |
| Committed interface specs regenerate byte-identically | `test_docs_drift.py`, `test_oracle_api.py`, `test_facilitator_api.py` |

## Extras ↔ scripts ↔ would-be distributions

| Extra | Console script | Would-be distribution | Docs surface |
|---|---|---|---|
| *(base)* | `cds` | `cds` (lean CLI) | Sphinx ([api](../api.md)) |
| `mcp` | `cds-mcp` | `cds-mcp-server` | [mcp-server](../services/mcp-server.md) + [generated manifest](../services/mcp-manifest.md) |
| `oracle` | `cds-oracle` | `cds-oracle` | [conformance-oracle](../services/conformance-oracle.md) + `openapi-oracle.json` |
| `facilitator` | `cds-serve` | `cds-facilitator` | [facilitator](../services/facilitator.md) + `openapi-facilitator.json` |
| `store` | — | (read index; T6 store service) | [model-store](../services/model-store.md) |
| `app` | — (P5/P6) | `cds-app` | (P5) |

## Stateful roots — ownership & lifetime

| Root | What | Lifetime | Who may mutate |
|---|---|---|---|
| canonical `concept-definition/instances/*.ttl` | the record (git = system of record) | durable, versioned | **only** `cds_commit` through the K2 gate (P2) |
| session staging `Project` (scratch DATA_ROOT) | candidates, intermediate invalid states allowed | one session | the whitelisted write tools (facilitator/MCP) |
| Oxigraph read index (ADR-7a) | derived, rebuildable | rebuild at will | the sync job only; if it disagrees with git, git wins |
| `deploy/` volumes (Keycloak realm, hub state) | infra state | operational | `cds-admin` (P6) |

## Deferred seams (what / why / trigger — interface preserved)

| Seam | Module | Trigger |
|---|---|---|
| Rust SHACL backend (D1) | `cds.core.verify.VerifierBackend` | W3C-suite + differential parity green (VB.1) |
| HTTP `ConformanceOracle` client (D8) | `cds.contracts.ConformanceOracle` | an out-of-process consumer (P5/P6 app tier) |
| Flexo-backed store service (D9) | `cds.contracts.ModelStore` | ROADMAP T6 acceptance (live round-trip) |
| Session staging automation | `cds.mcp.staging.new_session_project` | P2 |
| PROV-O stamping + audit | `cds.mcp.provenance.stamp` | P3 |
| AICC/LLM sidecar | `cds.facilitator.aicc.run_turn` | P4 (BYO-LLM per ADR-8 amendment) |
| marimo substrate swap (D3) | app tier only | ops weight dominates |

## Related docs

[Architecture spec](cds-web-app.md) · [MCP server](../services/mcp-server.md) ·
[Facilitator](../services/facilitator.md) · [Conformance oracle](../services/conformance-oracle.md) ·
[Model store](../services/model-store.md)
