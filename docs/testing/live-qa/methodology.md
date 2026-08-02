# Methodology — live human-facilitated QA

A reusable protocol so live-QA runs are consistent and **comparable across commits**. Distinct from the
[simulated two-player](../methodology.md) method: here a real human is in the loop and their felt
reactions are first-class data.

## Roles

- **Facilitator** (an agent, e.g. Claude Code): executes the test plan command-by-command, shows the
  human *expected vs. observed* at each step, captures reactions **verbatim**, diagnoses deviations
  (root-cause, not just symptom), and assembles the record. Does not invent guarantees the code doesn't
  provide — verifies claims against the source.
- **Human tester** (the maintainer or a real user): reads outputs, gives gut reactions and design calls,
  drives the browser/subjective beats the facilitator can't see, and makes product-philosophy decisions.

## The loop (per command)

1. Run the command. Long-running servers go to the background; capture their logs.
2. State **expected vs. observed** in one line; on a deviation, diagnose it (reproduce, read the source,
   pin the file:line) before moving on.
3. Prompt the human for a reaction at each judgment beat; **log their words verbatim** (paraphrase loses
   the signal).
4. Append to the running record. Every recommendation must trace to a concrete observation in the log.

## Commit-stamping rule (non-negotiable)

Before starting, record the **full commit hash** and confirm the **working tree is clean**
(`git status --porcelain` empty). If dirty, either stash/commit first or record the diff — findings on a
dirty tree aren't attributable to a commit. Name the run folder `YYYY-MM-DD-<short-hash>`. Put the hash
in `environment.md` and the headers of `README.md` / `test-plan.md` / `qa-report.md`.

## Baseline-comparison rule

A re-run at a new commit compares its findings against the **prior run's `findings.md`**. Divergence is
signal, not noise:
- a finding that no longer reproduces → a fix landed; record the fixing commit in the prior run's (or the
  new run's) `decisions.md`.
- a new finding → a regression or a new surface; log it fresh.
Never compare findings across runs without checking the commit each was taken at.

## Per-run folder template

Copy this structure for each new run (`YYYY-MM-DD-<short-hash>/`):

```
README.md          # run summary: metadata + headline + "what's in this folder"
environment.md     # commit anchor (full hash, tree-clean), toolchain versions, pytest baseline, expected findings
test-plan.md       # the plan executed, verbatim, with a "executed at <hash>" header
execution-log.md   # command-by-command + observed output, grouped by step; [FINDING] tags; findings trace here
qa-report.md       # the assembled narrative report (exec summary, per-step, verbatim reactions, triage)
findings.md        # scannable register: ID / severity / title / step / file:line / status / log-trace
decisions.md       # maintainer decisions (Decision/Why/Applies-to/Fix-commit) + any guiding principles
artifacts/         # bait_harness / scripts, server-logs/, canonical-snapshot/ (evidence), transcripts/
```

Not every run needs every file (a quick run may fold `findings.md` into `qa-report.md`), but keep
`environment.md` (provenance) and `execution-log.md` (traceable evidence) always.

## What to capture that LARP can't

Ergonomic chafing, confusing errors, wording that grates ("feels like talking to an LLM"), missing
affordances, anything the human had to guess, and product-philosophy calls (priority conflicts,
licensing/ethics judgments). These are the reason a human is in the loop — record them prominently.

## Reference run

[`2026-08-02-bb2d4a7/`](2026-08-02-bb2d4a7/) — the first live-QA run; a complete worked example of this
template.
