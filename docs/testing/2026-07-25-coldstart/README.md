# Run: 2026-07-25 — Cold-start (discovery) user test

**Build under test:** branch `feat/local-package-mapping` after the Phase-0 onboarding baseline
(`1051974`). **Method:** [cold-start walkthrough](../methodology.md#cold-start) — five fresh agents
start *cold* and experience the journey (README → install → init → first records) as a persona,
tagging friction by view (github-read / install / pip-use / clone-dev / docsite).

## Personas & verdicts

| # | Persona | Verdict |
| --- | --- | --- |
| P1 | Sam — software engineer, **no SEBoK** vocabulary | Completed the happy path, but would **bounce on vocabulary** solo (`cds explain`/`guide` don't exist; glossary buried); `--help` reads as academic. |
| P2 | Dr. Rao — systems engineer/PM, **not a Python dev** | **Bounces at INSTALL** — no venv step, `uv` assumed-but-uninstalled, no PyPI. Post-install: faithful & delightful. Flags 2 domain gaps (MOE traceability, ConOps). |
| P3 | Maya — non-technical **founder** | **Cannot install solo** (source + uv + git = wall) — the hard floor. With an AI assistant the flow is usable, but nothing gets her *to* the assistant unaided. |
| P4 | Alex — **both-savvy** control | Expert path fast & clean; damage concentrated in **two correctness bugs** (comma-list link corruption; verify has no dangling-ref check) that pass the tool's own checker. |
| — | Docs-only (no AI) | **Reached a compiled brief from docs alone** ✓. But docs don't *teach* the vocabulary in depth and have factual drift (AGENTS.md/CLAUDE.md, clone URL, two first-mappings). |

## Headlines

1. **The happy path works and the brief is a real payoff** — every persona (and the docs-only run)
   reached a clean compiled brief. Install → init → author → verify → compile holds end-to-end.
2. **Install is the hard floor for non-developers** — and the Phase-0 README's install steps are
   *actually broken as written* (no venv creation, `uv` not installed first). PyPI is the durable fix.
3. **There is no in-CLI way to look up a term** — every persona reached for `cds explain`/`cds guide`
   and hit "No such command." The canon ships but isn't surfaced; the tool outsources term-teaching to
   an AI, leaving CLI-only users stranded exactly where newcomers are weakest.
4. **Two correctness bugs undercut "checkable data"** — comma-separated link values silently corrupt
   into one bad IRI, and `verify` never catches a link to a nonexistent record.
5. **Doc drift** — `AGENTS.md`↔`CLAUDE.md`, clone-URL mismatch, an orphaned `mkdocs.yml`, a leaked
   private plan path, and two contradictory "first mappings."

See [`findings.md`](findings.md) for the ranked, tagged, deduped list and the **onboarding
benchmark** (acceptance criteria for the release milestone). Raw per-persona reports are summarized
there; full transcripts were delivered to the orchestrator this session.
