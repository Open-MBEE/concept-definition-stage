<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Localhost playground — run it and poke it

> Every phase of the T8 web-app work must be playable on localhost the day it lands
> (owner requirement, 2026-08-02). This page is the always-current quickstart; each phase
> extends it. Commands are verified by hand at each phase checkpoint — if one doesn't work,
> that's a bug, file it.

## What you can play with today (P1)

Two HTTP services and one MCP endpoint, all over a scratch project. No login, loopback only.

### 0. One-time setup

```bash
uv sync --extra dev --extra mcp --extra oracle --extra facilitator
```

### 1. Scaffold a scratch project (your session staging root)

```bash
mkdir -p /tmp/cds-playground && uv run cds init /tmp/cds-playground --name playground
```

### 2. Start the services (two terminals)

```bash
uv run cds-serve --project /tmp/cds-playground --port 8800
```

```bash
uv run cds-oracle --port 8801
```

### 3. Play — the facilitator (correct-by-construction authoring)

Swagger UI: <http://127.0.0.1:8800/docs> · manifest: <http://127.0.0.1:8800/manifest>

```bash
curl -s -X POST http://127.0.0.1:8800/tools/cds_synthesis -H 'Content-Type: application/json' -d '{"slug":"demo","title":"My demo mapping"}'
```

```bash
curl -s -X POST http://127.0.0.1:8800/tools/cds_new -H 'Content-Type: application/json' -d '{"kind":"stakeholder","slug":"ops","label":"Operator","description":"Runs the system day to day.","synthesis":"demo"}'
```

```bash
curl -s -X POST http://127.0.0.1:8800/tools/cds_new -H 'Content-Type: application/json' -d '{"kind":"need","slug":"uptime","label":"Uptime","description":"The operator needs the system to stay available.","synthesis":"demo","for_stakeholder":["ops"]}'
```

```bash
curl -s -X POST http://127.0.0.1:8800/tools/cds_verify -H 'Content-Type: application/json' -d '{}'
```

```bash
curl -s -X POST http://127.0.0.1:8800/tools/cds_compile -H 'Content-Type: application/json' -d '{}'
```

Things worth trying on purpose: write a need containing "shall" (watch the `NeedFormShall`
warning — advisory, it never blocks you); try `cds_commit` (403 — the human commit gate
lands in P2); file a retrieval item with `cds_queue_add` (the escalate-never-invent path);
re-POST `cds_new` with an existing slug (409 with a three-way hint — `cds_edit` changes it).

**Scratch vs append-only (ADR-9):** discard a draft, retire a record, replace one —

```bash
curl -s -X POST http://127.0.0.1:8800/tools/cds_discard -H 'Content-Type: application/json' -d '{"kind":"goal","slug":"junk"}'
```

```bash
curl -s -X POST http://127.0.0.1:8800/tools/cds_retract -H 'Content-Type: application/json' -d '{"kind":"goal","slug":"old-goal","reason":"rolled into v2"}'
```

**Perspectives (positions):** let two stakeholders disagree honestly —

```bash
curl -s -X POST http://127.0.0.1:8800/tools/cds_new -H 'Content-Type: application/json' -d '{"kind":"position","slug":"council-on-coverage","label":"Council on coverage","description":"Coverage justifies the budget.","synthesis":"demo","characterizes":"objective/coverage","held_by":"council","stance":"supports"}'
```

Then `cds_verify` surfaces `DivergingPositions` as a T3 *finding* (divergence is valid,
never an error) and the brief gains a **Convergence & divergence** section. Retracted and
superseded records leave the brief but never the record — `cds compile --include-history`
shows the appendix.

### 4. Play — the conformance oracle (stateless checking)

Swagger UI: <http://127.0.0.1:8801/docs>

```bash
curl -s -X POST http://127.0.0.1:8801/verify -H 'Content-Type: application/json' -d '{"turtle":"@prefix cds: <https://w3id.org/cds#> . @prefix cdsterm: <https://w3id.org/cds/term/> . @prefix dcterms: <http://purl.org/dc/terms/> . <https://x/need/n1> a cds:Instance, cdsterm:need ; dcterms:description \"The system shall stay available.\" ."}'
```

```bash
curl -s http://127.0.0.1:8801/rules
```

### 5. Play — the MCP path (bring your own LLM)

Point any MCP client at the tool server; the model lives in the client (ADR-8):

```bash
claude mcp add cds -- uv run --directory /path/to/cds cds-mcp --project /tmp/cds-playground
```

Then ask your agent to author a concept definition — it can only reach the 15 whitelisted
tools ([manifest](services/mcp-manifest.md)).

### What lands next here

| Phase | New playground moves |
|---|---|
| P2 | staged→canonical commit as `cds-reviewer`; held-out terms visible in the report |
| P3 | inspect PROV-O provenance + replay the audit log |
| P4 | chat with the AICC facilitator (BYO-LLM triplet) |
| P5/P6 | the Voilà web app; login via Keycloak |

## Related docs

[LARP user-testing protocol](https://github.com/Open-MBEE/concept-definition-stage/blob/main/docs/testing/larp-user-testing.md) · [Facilitator](services/facilitator.md) ·
[Conformance oracle](services/conformance-oracle.md) · [MCP server](services/mcp-server.md)
