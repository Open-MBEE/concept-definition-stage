# Findings register — live-QA run 2026-08-02 @ `bb2d4a7`

Scannable index. Full narrative in [`qa-report.md`](qa-report.md); each row traces to a block in
[`execution-log.md`](execution-log.md). Status: **confirmed** (reproduced), **design** (decision/feature),
**style** (wording/UX polish).

## Confirmed bugs

| ID | Sev | Title | Step | Where | Trace |
| --- | --- | --- | --- | --- | --- |
| B1 | High | **MCP link fields inert** — `for_stakeholder`/`serves_goal`/`refines`/`addresses` silently dropped over MCP (`**fields` collapses to one opaque `fields` object under mcp SDK 2.0 `func_metadata`); every MCP-authored need is an orphan. Independently reproduced at schema level. | 4 | [tools.py](../../../../src/cds/mcp/tools.py) `cds_new`, [server.py](../../../../src/cds/mcp/server.py) `_bind_project` | exec-log §Step 4 |
| B2 | Med-High | **No-op re-commit clobbers the changeplan `.md`** — same `content_hash` → same filename `<hash12>.md`, written unconditionally (no append-only guard the `.ttl` has); persisted changeplan shows `Adds: (none)`, contradicting git/audit/provenance. | 3 | [commit_gate.py:210-214](../../../../src/cds/app/commit_gate.py#L210-L214) vs [:276-277](../../../../src/cds/app/commit_gate.py#L276-L277) | exec-log §Step 3; [snapshot changeplan](artifacts/canonical-snapshot/concept-definition/changeplans/27ad89b724d5.md) |
| B3 | Med-High | **Voilà Step-6 command can't run** — no `ipykernel` → HTTP 500 "No Jupyter kernel"; also missing from the `app` extra, so `uv sync --extra app` wouldn't fix it. | 6 | [pyproject.toml:44](../../../../pyproject.toml) | exec-log §Step 6; [voila 500 log](artifacts/server-logs/voila-500-nokernel.log) |
| B4 | Med | **Facilitator silently no-ops** — `OpenAICompatBackend` sets no `temperature` → qwen default ~0.7 → 3/5 empty turns (HTTP 200, blank reply, no error); loop treats no-tool-calls as final reply. 0/5 empty at `temperature: 0`. | 5 | [decode.py:88-104](../../../../src/cds/facilitator/decode.py#L88-L104), [aicc.py:103-105](../../../../src/cds/facilitator/aicc.py#L103-L105) | exec-log §Step 5 |

## Structural / design findings

| ID | Title | Step | Decision |
| --- | --- | --- | --- |
| S1 | **"BYO-LLM by construction" over-claims for agentic clients** — K1 whitelist confines only what the MCP server exposes; a full agent brings its own Bash/Write (22× in Probe A) and the **K5 anti-fabrication dead-end isn't enforced over MCP** (only in the AICC loop). | 4 | Decide whether K5 / an unverified-source guard belongs at the tool/commit layer. See [decisions.md](decisions.md). |
| S2 | **Human-readable audit ledger** — export the hash chain as a scannable table/report (verdict banner + per-row chain-OK). | 3 | Feature: extend `AuditLog` ([provenance.py:82](../../../../src/cds/mcp/provenance.py#L82)) + a `cds audit` command. |
| S3 | **Licensing: noncommercial attestation override + propagate BY-NC-SA license flags into files** (NC via attestation, SA via propagation); keep MCP friction when not in NC-SA mode but make entering it low-friction. | 5 | Decision reversed the earlier operator-flag-only call. Governed by the ⭐ guiding principle. |
| S4 | **Web app: separate identity authoring from content authoring** (lock slug/kind/mapping after create; free-edit content); bigger inputs; flow-ordered buttons. | 6 | UI redesign. |

## Cross-cutting UX / style

| ID | Title | Steps |
| --- | --- | --- |
| U1 | **Internal jargon leaks into user-facing surfaces** (K1/K2/"correct-by-construction"/`--canonical`) — Swagger header + popouts, the K2 403, the GUI commit refusal. Rewrite for outside readers; source from shared docstrings/transclusion. | 2, 3, 6 |
| U2 | **Drop em-dashes** from rendered text ("no need to make people feel like they are talking to an LLM"). | cross-cutting |
| U3 | **Make "which kind of change is this?" obvious** — supersede/`rm`/`retract` modes + create-vs-revise aren't self-explanatory; `cds rm` on a committed record should confirm (Y/n, `--yes` to bypass). | 1, 6 |

## ⭐ Guiding principle (governs S3)

> "you cannot follow engineering best practices if you cannot see them … we prioritize the engineering
> quality first and do our best to keep the publishers happy … these are not documents at all, they are
> computational models!"

Full statement + design mandates in [`decisions.md`](decisions.md) and qa-report §Step 5 ⭐.

## What held (no action)

Step 0 baseline green · CLI mutation modes (collision exit-2, supersede, history appendix, rm-warns) ·
`DivergingPositions` info-framing · commit gate + `verify_chain()=True` + git `+6` + provenance
`llmMediated false` · K2 403 refusal shape · the SEBoK bait (K5 escalate-then-stop, no fabrication;
`test_no_fabrication_under_canon_bait` passed).

## Not fully exercised (for a future run)

- Probe C "override a rejection" needs an **in-continuity** session (this run's was separate).
- Scored eval only against qwen2.5:7b (2 model-capability failures) — re-run vs a hosted model.
- Full Keycloak/JupyterHub hosting stack (needs real DNS) — out of scope, per the plan.
