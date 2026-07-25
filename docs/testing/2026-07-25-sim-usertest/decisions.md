# Decisions — 2026-07-25 sim-usertest

Four judgment calls the findings raised, decided by the maintainer (Michael Zargham) and implemented
on branch `feat/local-package-mapping`. (The critical bugs in [`findings.md`](findings.md) #1–#5 were
already fixed in `0477229` before these.)

## D1 — Notes vs. content (findings #7)

**Question:** facilitator commentary leaks into the human-facing brief because a record's note and its
content share the `description` field. How to separate them?
**Decision: add a `supersedes` link** (not a separate note field).
**Rationale:** the maintainer preferred change-*provenance* over a free-text annotation. A corrected
record can point to what it replaced, giving an audit trail of intentional revisions.
**Implemented:** `Record.supersedes` (list of IRIs) → `cds:supersedes`; `cds new … --supersedes
<slug-or-iri>` (same-kind slug or full IRI); rendered in the brief and `cds show` as
`supersedes: <name>`. Tests in `tests/unit/test_decisions.py`.
**Left open:** a dedicated note-vs-content field was *not* adopted; general commentary still has no
home. Revisit if it recurs.

## D2 — Slug handling (findings #6)

**Question:** a slug with a space crashed the CLI. Reject, auto-slugify, or defer?
**Decision: reject invalid slugs with a friendly error.**
**Rationale:** slugs are identifiers that flow into IRIs; predictable, clean ids beat silent coercion.
**Implemented:** a shared `validate_slug` (kebab-case `^[a-z0-9]+(-[a-z0-9]+)*$`) via a `Slug`
annotated type on every authorable model; the CLI turns the resulting `ValidationError` into a clean
message + exit 2 (no traceback). Tests cover model + CLI.

## D3 — Tension resolve + side-ledger deletion (findings #8)

**Question:** stale tensions keep rendering after a reversal, and `cds rm` only covered the 10 record
kinds. What to add?
**Decision: add a resolve status to tensions AND extend `rm` to the side-ledgers.**
**Rationale:** the most complete correction story — settled conflicts drop out of the brief, and any
side-ledger item can be deleted.
**Implemented:** `Tension.status` (`open`/`resolved`, SHACL-guarded); `cds tension resolve <slug>`
(resolved tensions are excluded from the compiled brief); `cds park rm` / `cds queue rm` /
`cds tension rm`. Tests in `tests/unit/test_decisions.py`.

## D4 — Sequencing

**Decision: implement the decided fixes now**, on the branch, with tests; no PR yet. Done.

## Result

Full suite **159 passed / 4 skipped**, ruff + mypy clean. All three feature decisions verified in a
live cross-repo repro (bad slug → friendly error; `--supersedes` recorded + shown; `tension resolve`
drops from brief; `park/queue rm` work). Branch remains unmerged for maintainer review.

## Still reported, not changed (maintainer's call for later)

- `build` vs `verify` count clarity (findings #9).
- Slug-immutability ergonomics after a reversal (findings #10).
- A dedicated note-vs-content field (D1 left-open).
