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

## Run index

| Date | Run | Method | Headline outcome |
| --- | --- | --- | --- |
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
