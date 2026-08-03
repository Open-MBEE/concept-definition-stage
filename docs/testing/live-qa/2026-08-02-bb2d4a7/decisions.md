# Maintainer decisions — live-QA run 2026-08-02 @ `bb2d4a7`

Decisions the maintainer made live during the run. Each: **Decision / Why / Applies-to / Fix commit**
(commit filled in when the change lands — this run folder is the "before" baseline). See
[`findings.md`](findings.md) for the finding IDs.

---

## D1 — `cds rm` on a committed record should confirm (U3)

- **Decision:** warn → prompt `Y/n` → proceed on `Y`; add `--yes`/`-y` to bypass for scripts.
- **Why:** *"i want an extra confirm step, warn, ask to confirm but then push through if confirm is Y."*
  Current behavior deletes with only a printed note, no confirmation.
- **Applies-to:** `cds rm` (CLI). Related to the mode-discoverability gap (U3).
- **Fix commit:** `6f41a9f`

## D2 — Human-readable audit ledger export (S2)

- **Decision:** add an export that renders the hash chain as a **table/report** — one row per event
  (seq, ts, action, approver, `+adds/~rev/^super/-retract/held`, short hash, per-row chain-OK), with an
  overall `verify_chain()` verdict banner. Offer as `cds audit export` and/or an HTTP `/audit` view.
- **Why:** *"i need a trail ledgered … in a table such that scanning is clearly in tact … most humans
  need a dashboard or a report … an option to export audit with the trace view."* The formal guarantee
  is trusted; the raw artifacts aren't human-scannable.
- **Applies-to:** extend `AuditLog` ([provenance.py:82](../../../../src/cds/mcp/provenance.py#L82)); new `cds audit` command (none today).
- **Fix commit:** `a8e91b3`

## D3 — Licensing: noncommercial attestation override + license-flag propagation (S3)

_Supersedes an earlier same-session call ("keep operator-flag only, no attestation"), which was reversed
after Probe B surfaced the real friction._

- **Decision (two prongs):**
  - **(a)** Build a **noncommercial attestation override** — user attests noncommercial/educational use
    (e.g. ABET senior design), unlocking **verbatim** SEBoK rendering. Record who/when in provenance
    (it's a legal assertion — audit it like an approver). Clears the **NC** prong.
  - **(b)** **Propagate BY-NC-SA license flags into the underlying files** when a record/view embeds
    SEBoK verbatim, so the derivative is correctly licensed at rest. Clears the **ShareAlike** prong
    (turns today's View-level "inherits restricted license" into per-file propagation).
  - Keep MCP-mode friction when **not** in NC-SA mode, but make entering that mode low-friction; never
    a dead-end. Keep the K5 bait **out** of the license logic (orthogonal). Add a render-license
    regression test (base harness in [artifacts/bait_harness.py](artifacts/bait_harness.py) + the
    scheme_view checks in [execution-log.md](execution-log.md) §Step 5).
- **Why:** see D4 (the guiding principle). A bare "noncommercial" attestation doesn't clear ShareAlike
  for a permissive output; (b) is the resolution — abide by construction rather than mislabel.
- **Applies-to:** [view.py](../../../../src/cds/core/render/view.py) `scheme_view`, [licenses.py](../../../../src/cds/core/licenses.py) `sebok_renderable`, the instance/canonical writers, and a new attestation surface. **Legal skim recommended before shipping the attestation wording.**
- **Fix commit:** `b15a268`

## D4 — ⭐ Guiding principle (governs D3 and the licensing surfaces)

Stated verbatim by the maintainer after Probe C:

> *"this is a huge ux issue, you cannot follow engineering best practices if you cannot see them. in mcp
> mode we do need the friction of the no if we're not in nc-sa mode but we need to make it comparatively
> easy to get into that mode as long as the user takes explicit responsibility for the call and we help
> them abide (eg with the license flags). our goal is improving engineering practices and preventing
> engineers from abiding standards is in direct conflict with engineering ethics. we prioritize the
> engineering quality first and do our best to keep the publishers happy. we don't sacrifice engineering
> quality because publishers are behind the times. these are not documents at all, they are computational
> models! and we need to make sure they are conformant to and faithful to the spirit of engineering best
> practice."*

**Mandates:** (1) keep the friction, kill the dead-end; entering NC-SA mode is one responsibility-taking
step + auto license propagation. (2) engineering-conformance is prioritized over publisher-license
accommodation. (3) records are **computational models, not documents** — the verbatim-reproduction
license machinery is over-fit to the wrong artifact; cite-only-with-grounding is the always-available
floor so an engineer is never fully blind. (4) treat as **high priority** (framed as an
engineering-ethics issue).

## D5 — Web app: separate identity from content authoring (S4)

- **Decision:** split the form so **identity/placement** (`kind`, `slug`, `synthesis` mapping — set-once)
  is distinct from **content** (`label`, `statement`, `links` — freely revisable); lock identity after
  create (or a create-vs-revise mode split). Bigger inputs (esp. Statement); order buttons by the flow
  (compose → stage → verify → compile → commit).
- **Why:** *"encourages editing content which should be stable like slugs … we need a separation between
  authoring triples and the contextual model metadata that is authored once."* Ties to U3 (make "which
  kind of change is this?" obvious).
- **Applies-to:** [src/cds/app/notebook/concept_definition_app.ipynb](../../../../src/cds/app/notebook/concept_definition_app.ipynb) and the widget layer.
- **Fix commit:** `a9f126b`

## D6 — S1 resolved: unverified-source hold at the commit gate

_Was the open design question; decided by the maintainer post-run (2026-08-02, via the
coding agent's decision prompt)._

- **Decision:** enforce at the **commit gate**, the one chokepoint every transport shares:
  records matching the `UnresolvedCitation` condition are held (like held-out X7),
  enumerated in the ChangePlan under their own heading, and enter the record only when the
  source is secured or the approver passes an explicit `include_unverified` (recorded in
  the audit event). No per-session state on the MCP path; the AICC conversational
  dead-end stays as-is, orthogonal. Docs reword the "BYO-LLM by construction" claim to
  locate the guarantee honestly (surface = whitelist; record = gate).
- **Why:** Probe B showed an agent over raw MCP can `cds_new → cds_commit` a definition
  with no escalate-then-stop gate; the whitelist confines the served surface, not an
  agentic client's own tools.
- **Applies-to:** [commit_gate.py](../../../src/cds/app/commit_gate.py),
  [verify.py](../../../src/cds/core/verify.py) (`unresolved_citations` shared helper),
  `cds_commit` tool arg, ADR-6 amendment, mcp-server.md.
- **Fix commit:** `6be2e87`
