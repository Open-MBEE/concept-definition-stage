# CDS — Testing Record

A durable, inspectable history of how the CDS package is tested: the **methodologies** we use, the
**raw logs** from each run, and the **findings + decisions** that came out of them. Modeled loosely
on the `experiments/` convention in
[Open-MBEE/flexo-conflict-resolution-policy-research](https://github.com/Open-MBEE/flexo-conflict-resolution-policy-research/tree/main/experiments):
a top-level index, one folder per run, each folder self-describing with its own logs.

This is distinct from unit tests (in [`tests/`](../../tests/)), which check individual functions.
Here we record **end-to-end / user-facing testing** of the tool as a whole.

## Methodologies

- [`methodology.md`](methodology.md) — **Simulated two-player user test**: two independent
  sub-agents (a naive domain-expert "human" + a facilitator following the vendored `cds-elicit`
  skill) run a full session against the real CLI, plus a scripted robustness battery. Reusable for
  future runs.
- [`live-qa/methodology.md`](live-qa/methodology.md) — **Live human-facilitated QA**: a real facilitator
  executes a test plan against the actual tool while the maintainer logs reactions verbatim, stamped to
  an exact commit. Catches ergonomic/wording/product-philosophy signals the synthetic agents can't feel.
  Runs are indexed in [`live-qa/`](live-qa/).

## Run index

| Date | Run | Method | Headline outcome |
| --- | --- | --- | --- |
| 2026-08-02 | [live-qa/2026-08-02-bb2d4a7](live-qa/2026-08-02-bb2d4a7/) | Live human-facilitated (6-step plan + MCP probes, Ollama qwen2.5:7b) | Core guarantees held (commit gate, audit chain, K5 bait). 4 confirmed bugs: MCP inert link fields, no-op changeplan clobber, Voilà missing `ipykernel`, facilitator silent empty-turns. Structural: K5 not enforced over raw MCP. Guiding principle captured ("computational models, not documents"). |
| 2026-07-25 | [sim-usertest](2026-07-25-sim-usertest/) | 2× two-agent sessions + battery | Found the critical "**can't safely correct a record**" bug (re-authoring appended). All safe bugs fixed with tests; 4 maintainer decisions captured & implemented. |
| 2026-07-25 | [coldstart](2026-07-25-coldstart/) | 5× cold-start walkthroughs (4 personas + docs-only) | Discovery→install→init→first-records journey. Install is the non-dev floor; no in-CLI term lookup; 2 correctness bugs (link corruption, no dangling-ref check); doc drift. Produced the **onboarding benchmark** (release acceptance criteria). |

## Related (kept outside this repo, by design)

Notes from **human pilots** with real people (e.g. the first friend-facilitated session) live in a
private folder `~/Documents/cds-user-testing/`, not in git — those are concept-/person-specific and
were deliberately kept out of the codebase. This in-repo record covers the **engineering QA** runs
(synthetic personas, no real subject), which are safe and useful to preserve here.

## Conventions

- One folder per run: `YYYY-MM-DD-<slug>/` with its own `README.md` (design + summary), raw logs,
  a `findings.md`, and — when a run drives changes — a `decisions.md` linking to the commits.
- Logs are copied in as Markdown so the history survives even after scratch dirs are cleaned.
- Every recommendation should trace to a concrete observation in a log.
