# Live-QA run — 2026-08-02 @ `bb2d4a7`

**Modality:** live human-facilitated QA (real facilitator drives the tool, maintainer logs reactions
verbatim). **Commit:** `bb2d4a7` (`bb2d4a7517862e205be49af5c00b2dc4418215c7`), tree clean.
**Environment:** macOS · Python 3.12.12 · mcp SDK 2.0.0 · Ollama qwen2.5:7b. Baseline `pytest` →
324 passed, 17 skipped. Full detail in [`environment.md`](environment.md).

## What this was

Execution of the coding agent's 6-step local test plan ([`test-plan.md`](test-plan.md)) — CLI mutation
modes, the two services + stakeholder divergence, the commit gate + accountability trail, the MCP path
(+ Probes A/B/C), the AICC facilitator + scored eval, and the Voilà web shell.

## Headline

The **core guarantees held** where they're mechanically enforced: CLI mutation modes, the
`DivergingPositions` honest-multiperspective framing, the commit gate + hash-chained audit
(`verify_chain()=True`, git `+6`, provenance `llmMediated false`), the K2 403 refusal, and the SEBoK
anti-fabrication **bait (K5 escalate-then-stop, no fabrication)**.

**4 confirmed bugs** — B1 MCP link fields inert (high; independently reproduced), B2 no-op re-commit
clobbers the changeplan `.md`, B3 Voilà command missing `ipykernel`, B4 facilitator silent empty-turns
(no temperature). **Biggest structural insight (S1):** "BYO-LLM by construction" over-claims for an
*agentic* client — the K5 dead-end isn't enforced over raw MCP, only in the facilitator loop.
**Governing principle (D4/⭐):** *"you cannot follow engineering best practices if you cannot see them …
these are computational models, not documents"* — drove the licensing decision (D3: NC attestation +
license-flag propagation).

## What's in this folder

| File | Contents |
| --- | --- |
| [`environment.md`](environment.md) | Commit anchor + toolchain + baseline — the reproducibility provenance. |
| [`test-plan.md`](test-plan.md) | The coding agent's 6-step plan, verbatim. |
| [`execution-log.md`](execution-log.md) | Command-by-command with observed outputs; every finding traces here. |
| [`qa-report.md`](qa-report.md) | The full assembled report (exec summary, per-step, verbatim reactions, triage). |
| [`findings.md`](findings.md) | Scannable register: B1-B4 / S1-S4 / U1-U3, severity + file refs + trace. |
| [`decisions.md`](decisions.md) | Maintainer decisions (D1-D5) + the ⭐ guiding principle; fix-commit placeholders. |
| [`artifacts/`](artifacts/) | `bait_harness.py`, `server-logs/`, `canonical-snapshot/` (the audit/changeplan/provenance evidence), `transcripts/` (Probe A/B/C fresh-session logs). |

## Reproducing / re-running later

Re-run the plan at a future commit and compare the new findings against [`findings.md`](findings.md).
Divergence is signal: a finding that no longer reproduces means a fix landed (record its commit in
[`decisions.md`](decisions.md)); a new finding is a regression or new surface. See
[`../methodology.md`](../methodology.md) for the protocol.
