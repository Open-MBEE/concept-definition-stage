# Findings — 2026-07-25 sim-usertest

Ranked, with final disposition. Tags: **BUG · FRICTION · SKILL · ENHANCEMENT**.
Fixes landed in two commits: `0477229` (safe bugs) and the decisions commit (see
[`decisions.md`](decisions.md)).

| # | Finding | Tag · Severity | Disposition |
| --- | --- | --- | --- |
| 1 | **Re-authoring a slug *appended*** instead of replacing → contradictory multi-valued records; no `edit`/`rm`; skill forbids hand-editing → **no safe correction path**. (battery #4, S1 #1, S2 #1) | BUG · critical | **FIXED** — authoring is now an upsert (replace-by-subject) across `new`/`park`/`queue`/`synthesis`/`tension`; added `cds rm`. `0477229` |
| 2 | `verify` false-negative: a doubled label/description passed clean (no max-cardinality). (S2 #4) | BUG · high | **FIXED** — `sh:maxCount 1` on instance/synthesis label + description. `0477229` |
| 3 | No read-back; `cds new` echoed only the IRI, hiding the silent append. (S1 #4/#5, S2 #3) | FRICTION · high | **FIXED** — `cds show` / `cds list`; `cds new` echoes stored fields. `0477229` |
| 4 | Orphan-need check under-fired (need with a stakeholder but no goal not flagged, though skill promises it). (S1 #3) | BUG · medium | **FIXED** — added `NeedServesNoGoal` (T3 info). `0477229` |
| 5 | Skill: stale "when M5 lands" caveat; no batching guidance; no correction guidance; `--addresses` undocumented. (S1 #7/#8/#9) | SKILL · medium | **FIXED** — skill updated (correction section, batched-elicitation, close-loop, `--addresses`). `0477229` + decisions commit |
| 6 | A spaced slug crashed with an unhandled rdflib traceback; loose chars accepted. (battery #9) | BUG · medium | **DECIDED → FIXED** — reject non-kebab slugs with a friendly error (exit 2). See [`decisions.md`](decisions.md). |
| 7 | Facilitator commentary leaks into the brief (no note-vs-content separation). (S1 #6, S2 #3) | ENHANCEMENT · medium | **DECIDED → FIXED (partial)** — added a `cds:supersedes` link + `--supersedes` for change provenance; a dedicated note field was **not** adopted. |
| 8 | No way to close/resolve a tension; `cds rm` didn't cover side-ledgers. (S2 #6) | ENHANCEMENT · low–med | **DECIDED → FIXED** — `cds tension resolve` (drops from brief) + `cds rm` extended to `park`/`queue`/`tension`. |
| 9 | `build` vs `verify` report different warning/lint counts (validate different graphs). (S2 #5) | FRICTION · low | **REPORTED** — correct but confusing; output could name which graph it validated. Not changed. |
| 10 | Slug becomes a misleading label after a reversal (immutable id). (S2 #7) | MINOR · low | **REPORTED** — path is `cds rm` + re-create under a better slug (or `--supersedes`). |

## Validated as working (do not regress)

- The `cds-elicit` skill is followable end-to-end; calm one-question glossing held.
- Relations (`--refines` / `--for-stakeholder` / `--serves-goal` / `--addresses`) persist and render.
- Conflict checks (`shall` / orphan / duplicate / empty-set) fire; buyer≠user modeled in both runs.
- Bad-input paths, empty project, `init` idempotency, byte-stable compile, and CDS-repo isolation.
