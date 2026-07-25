# Run: 2026-07-25 — Simulated user test (pre-pilot QA)

**Build under test:** branch `feat/local-package-mapping` (M0–M5).
**Method:** [simulated two-player user test](../methodology.md) — 2 two-agent sessions + a scripted
robustness battery.
**Question:** Does the built package survive a realistic session before the maintainer pilots it?

## Contents

- [`battery.md`](battery.md) — scripted robustness battery results.
- [`session-s1-tool-library.md`](session-s1-tool-library.md) — S1: "Dana", non-technical community
  organizer (neighborhood tool-lending library). Full session; friction log + brief.
- [`session-s2-ev-charging.md`](session-s2-ev-charging.md) — S2: "Priya", detail-oriented engineer
  (apartment EV-charging scheduler). Relations + reversal probe; friction log + brief.
- [`findings.md`](findings.md) — ranked findings (bug / friction / skill-gap / enhancement).
- [`decisions.md`](decisions.md) — the four maintainer decisions, rationale, and implementing commits.

## Headline

**The tool could not safely *correct* a record.** Re-authoring a slug *appended* rather than
replacing, so a reversal ("free → paid", "equal-split → usage-based") left the record asserting both
the old and new wording at once; `verify` passed it (false-negative) and `compile` hid it by picking
one value alphabetically. With the skill's "never hand-edit the Turtle" rule and no `edit`/`rm`, there
was **no sanctioned correction path**. Both sessions and the battery hit it independently.

## Outcome

- **Fixed (safe/clear bugs), with regression tests:** upsert-on-reauthor + `cds rm`; `verify`
  `maxCount 1` guard; `NeedServesNoGoal` check; `cds show`/`cds list`; `cds new` field echo; skill
  edits. Commit `0477229`.
- **Maintainer decisions (captured + implemented):** supersedes link; reject bad slugs with a
  friendly error; tension resolve + extend `rm` to side-ledgers. See [`decisions.md`](decisions.md).
- **Validated as working:** the `cds-elicit` skill is followable end-to-end; relations render
  correctly; park/queue/tension and the buyer≠user split were elicited naturally; repo isolation and
  determinism held.

## What worked (do not regress)

Both facilitators set up, read, and followed the skill through a full two-halves session with calm
one-question glossing. `--refines`/`--for-stakeholder`/`--serves-goal`/`--addresses` all persisted
and rendered. The battery confirmed graceful handling of bad input, empty projects, `init`
idempotency, byte-stable compile, and CDS-repo isolation.
