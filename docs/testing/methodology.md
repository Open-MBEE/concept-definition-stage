# Methodology — Simulated two-player user test

A repeatable way to exercise the CDS package the way a real session would, **before** (or alongside)
piloting with real people. It has two parts: interactive **two-agent sessions** and a scripted
**robustness battery**.

## Why two independent agents

CDS structures an asymmetric cooperative game: a human domain expert (Player 1) and an in-IDE model
(Player 2, facilitator/scribe). To test that honestly, the "human" must not know the tool's
internals and the "facilitator" must genuinely elicit and drive the CLI. So we use **two separate
sub-agents** — one can't game the other:

- **Human agent** — given a persona + a concept in mind + a set of realistic behaviors. Answers in
  plain language; never mentions the CLI/RDF. Behaviors we deliberately inject (from the pilot
  observations): a tangent (→ park), a genuine unknown (→ queue), a **buyer≠user** split, an
  accidental "shall" in a need, and a **reversal** of an earlier answer (stresses update semantics).
- **Facilitator agent** — reads the vendored `.claude/skills/cds-elicit.md` and *follows it* (this
  also tests that the skill is followable), asks one question at a time (may batch when natural),
  records each answer via the real `cds` CLI, and keeps a **brutal friction log**.

**Orchestration:** the main session spawns both agents and relays between them (or wires them
peer-to-peer via SendMessage and collects the facilitator's `SESSION COMPLETE` report). Each session
runs in its own throwaway repo: `uv venv --python 3.12` → `uv pip install -e <cds>` → `cds init`.

Use **multiple sessions with distinct personas/domains** (e.g. a non-technical organizer vs. a
detail-oriented engineer) — friction is often persona-dependent.

## The robustness battery (scripted, no human)

A checklist run directly against the installed CLI, covering what interactive sessions won't reliably
hit. At minimum:

- Empty-project `cds verify` / `cds compile` (graceful?).
- Bad input: unknown kind; missing required options; invalid/nonexistent `queue set`; **bad slug**.
- **Re-author the same slug with changed content** (update/upsert semantics — the highest-value
  probe; a reversal will hit this).
- Conflict detection fires (need-form "shall", orphan need, duplicate statement, empty set).
- Side-ledger re-adds (park/queue) — do they upsert or duplicate?
- Determinism: instance files + compiled brief byte-stable on re-run.
- `cds init` idempotency / `--force`.
- **CDS-repo isolation**: `git -C <cds> status` stays clean of the test's writes throughout.

## Turning results into action

1. Collect friction logs + inspect the resulting RDF/brief directly (don't trust self-report alone).
2. Rank findings: **bug / friction / skill-gap / enhancement** × severity, each with a repro.
3. Fix the **unambiguous, low-risk bugs** with regression tests (keep the suite green); surface the
   judgment-heavy items to the maintainer as explicit decisions.
4. Record everything in a dated run folder here.

## Cold-start (discovery) walkthrough

A higher-abstraction variant: the user doesn't know the tool exists yet — a colleague sends the
**repo link**. The journey starts at the README and must survive *discovery → install → init → first
records*, so the test evaluates the whole onboarding surface, not just usage.

- **Views.** Tag every friction by the view it belongs to: **github-read** (browser, README-first),
  **install**, **pip-use** (the installed package's own surfaces — `--help`, shipped guide,
  vendored assets), **clone-dev** (contributor), and **docsite** (the published docs). Each view must
  make sense on its own.
- **Personas across two axes** (technical × domain familiarity): e.g. engineer-without-SEBoK,
  systems-engineer-without-Python-tooling, non-technical founder, and a both-savvy control. Friction
  is persona-dependent — the control separates *real* bugs from *novice-only* friction.
- **Method.** Each persona is a fresh **cold** agent running a cognitive walkthrough: it experiences
  the journey in persona, actually drives the tool, and logs where *that* persona would stall or
  bounce — especially ontology-term confusion. Add one **docs-only** run (no AI, README + shell only)
  as the harshest test of the documentation alone.
- **Deliverable.** Beyond findings: an **onboarding benchmark** — testable acceptance criteria for
  "repo-link → first verified mapping without bouncing" — which feeds a release milestone.

## What "done" looks like

The tool survives a full two-halves session (business/mission analysis → stakeholder needs) with
tangents/unknowns/reversals, produces valid RDF + a readable brief in the user's own repo, and the
CDS repo is untouched — with any bugs found either fixed (with tests) or logged as decisions.
