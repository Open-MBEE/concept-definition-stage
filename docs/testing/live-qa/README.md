# Live-QA — human-facilitated testing record

**Live QA** = a real person facilitates a session against the actual tool while the tool's behavior is
executed and their reactions are logged **verbatim**, stamped to an exact commit. It complements the
[simulated / LARP](../methodology.md) runs in the parent [Testing Record](../README.md): the LARP agents
exercise coverage and robustness at scale; live QA catches the things a synthetic agent can't feel —
ergonomic chafing, wording that grates, "I had to guess," and product-philosophy calls that only a human
maintainer can make.

Each run is a self-describing folder (see [`methodology.md`](methodology.md) for the protocol and the
per-run template). Runs are named `YYYY-MM-DD-<short-commit>` so the commit provenance is in the path.

## Run index

| Date | Run | Commit | Method | Headline |
| --- | --- | --- | --- | --- |
| 2026-08-02 | [2026-08-02-bb2d4a7](2026-08-02-bb2d4a7/) | `bb2d4a7` | 6-step plan, live facilitated (+ MCP Probes A/B/C, Ollama qwen2.5:7b) | Core guarantees held (commit gate, audit chain, K5 bait). 4 confirmed bugs: MCP inert link fields, no-op changeplan clobber, Voilà missing `ipykernel`, facilitator silent empty-turns. Structural: K5 not enforced over raw MCP. Guiding principle captured: "computational models, not documents." |

## Why commit-stamping matters here

Findings are only meaningful against a known code state. Every run records the **full commit hash** and
**working-tree cleanliness** ([per-run `environment.md`](2026-08-02-bb2d4a7/environment.md)). A re-run at
a later commit compares its findings against the prior run's `findings.md` — divergence means a fix
landed (or a regression appeared), not noise. Never compare findings across runs without checking the
commit each was taken at.

## Scope / privacy

This modality is **engineering QA** — the subject is the tool, facilitated by the maintainer, with no
third-party human subject or concept-/person-specific data. That keeps it safely in-repo (consistent
with the parent record's carve-out). A future live run involving a **real external subject** keeps
person/concept-specific content in the private `~/Documents/cds-user-testing/` folder (not git) and
vendors only tool-behavior logs here.
