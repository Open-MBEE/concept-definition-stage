# Findings & onboarding benchmark — 2026-07-25 cold-start

Consolidated, deduped, ranked. Tags: **view** (github-read / install / pip-use / clone-dev / docsite)
× **type** (bug / doc / learner-UX / guardrail / domain). Disposition set after implementation:
**FIXED** this round, or **REC** (recommended → issue/milestone).

## Correctness bugs (pip-use) — highest severity

| # | Finding (who) | Disposition |
| --- | --- | --- |
| C1 | **Comma-list link values silently corrupt data.** `--for-stakeholder eng,platform` → one bad IRI `.../stakeholder/eng,platform`, not two links; `show`/brief render it as valid. Link-target slugs aren't validated. (P4) | **FIXED** — validate link slugs (kebab) + split comma lists; reject bad targets with a friendly error. |
| C2 | **`verify` has no referential-integrity check.** A need → a nonexistent stakeholder/goal passes clean. verify catches *orphan* (no link) and *no-goal*, but not *dangling* (link to a missing slug). Undercuts "checkable data." (P4) | **FIXED** — dangling-reference check (T2) over all links. |
| C3 | **Traceback leak + exit 0 on crash outside a project.** `CdsProjectNotFound` dumps a Rich traceback; `verify` outside a project exits 0 despite crashing. (P4) | **FIXED** — catch project-resolution errors → one-line stderr + nonzero exit. |

## Install (install) — the hard floor for non-developers

| # | Finding (who) | Disposition |
| --- | --- | --- |
| I1 | **Phase-0 install steps are broken as written:** no venv creation, `uv` assumed-but-not-installed, no non-uv fallback, no "Download ZIP." `uv pip install -e .` verbatim fails ("command not found: uv" / "no virtual environment found"). (P2, P3) | **FIXED** — corrected install (create+activate venv; install-uv note; a plain `python -m venv`+`pip` path; troubleshooting). |
| I2 | **No PyPI package** — the one command non-devs know (`pip install …`) doesn't exist; name `cds` may collide on PyPI. (P2, P3) | **REC** — milestone (T1); guard the name. |
| I3 | No install troubleshooting/FAQ (uv-not-found, no-venv, system-Python-3.9). (P2) | **FIXED** — added to install docs. |

## Learner-UX / term comprehension (pip-use, docs) — universal

| # | Finding (who) | Disposition |
| --- | --- | --- |
| L1 | **No in-CLI term lookup.** Every persona reached for `cds explain`/`cds define`/`cds guide`; all error. Per-kind `--help` is generic (never defines the kind). The shipped canon isn't surfaced. (P1–P4, docs-only) | **FIXED** — `cds explain <term>` (verbatim canon + gloss + example). |
| L2 | No `cds guide` "start here". (P1, P2, P3) | **FIXED** — `cds guide` prints the shipped getting-started. |
| L3 | The building-blocks glossary lives only in getting-started §4 — not in README or CLI. (P1, docs-only) | **FIXED** — glossary table added to README; `cds explain` in CLI. |
| L4 | `cds --help` top line ("commit SEBoK/INCOSE canon to RDF") + command help are insider-jargon (SHACL, Tier-1, `cds:Synthesis`, ASoT). (P1, P2, P3) | **FIXED** — plain-language-first help. |
| L5 | **"synthesis"** as the container noun is the single most confusing term. (P1, P3) | **FIXED (partial)** — glossed as "the mapping/container" in help & docs; not renamed (would break). |
| L6 | No "next step" nudge after `cds init`/commands. (P1, P3) | **FIXED** — `cds init` prints next steps. |
| L7 | verify output jargon (T2/need-form/orphan) unglossed; the "shall" flag shows no corrected example. (P1, P3) | **FIXED** — the shall finding now shows the need-form fix. |
| L8 | **"need form (never shall)" asserted ~5× but never shown.** No good-vs-bad example. (docs-only) | **FIXED** — worked example in docs + `cds explain need`. |
| L9 | `--interactive` doesn't teach (no definition/example at the prompt). (P3) | **REC** — surface `explain` in interactive later. |
| L10 | **Ordering trap** — construction order is implicit; authoring a need first is natural but needs a goal/stakeholder. (P3) | **REC** (partly covered by C2's dangling-ref surfacing). |
| L11 | No `cds --version`. (P4) | **FIXED**. |

## Doc drift / errors (github-read, docs, clone-dev, docsite)

| # | Finding (who) | Disposition |
| --- | --- | --- |
| D1 | getting-started says `init` drops **AGENTS.md**; it drops **CLAUDE.md**. (docs-only, P4) | **FIXED** — `init` now vendors a neutral AGENTS.md + thin CLAUDE.md (decision), so the doc is correct. |
| D2 | **Clone-URL mismatch:** README/getting-started (`concept-definition-stage`) vs CONTRIBUTING (`cds`). One 404s. (P4) | **FIXED** — reconciled to `concept-definition-stage`. |
| D3 | **Orphaned `mkdocs.yml`** competes with the Sphinx docsite; its nav omits the new pages. (P4) | **FIXED** — removed. |
| D4 | AGENTS.md leaks a **private plan path** (`~/.claude/plans/…`). (P4) | **FIXED** — scrubbed. |
| D5 | README "Under the hood"/License jargon ≈40% of the page. (P1, P3) | **FIXED** — trimmed / moved below the fold. |
| D6 | README lacks the glossary + puts acronyms before the "no background needed" reassurance. (P1, P3) | **FIXED**. |
| D7 | **Two contradictory "first mappings"** (README vs getting-started) + no authoring-order guidance. (docs-only) | **FIXED** — reconciled + an order line. |
| D8 | Example slug **`cd`** collides with the shell `cd`; the `synthesis cd` ↔ `--synthesis cd` link is unexplained. (docs-only) | **FIXED** — renamed the example slug. |
| D9 | construction-order.md is pointed to as "the vocabulary" but never defines the plain terms (dead end); unexplained "AICC". (P2, docs-only) | **FIXED** — term-lookup now points at `cds explain`; not construction-order. |
| D10 | compile brief omits a goal's `--addresses` link (stored in TTL, not rendered). (P4) | **FIXED**. |

## Domain fidelity (expert)

| # | Finding (P2) | Disposition |
| --- | --- | --- |
| F1 | **MOE has no traceability** — `moe` can't link to a goal/objective/need; SEBoK/INCOSE expects MOEs to trace. | **FIXED** — `moe --measures <slug>` link + rendered. |
| F2 | **No ConOps/operational-concept/lifecycle-concept kind**, though the shipped `need` definition references "lifecycle concepts." | **REC** — v0.2 vocabulary. |

## Validated (do not regress)

Happy path end-to-end for all personas; docs-only reached a brief unaided; the "shall" guardrail
fires; gentle errors for missing `--synthesis` / unknown kind; `cds new --help` inline relationship
docs; deterministic RDF + clean brief + PDF; the AI-assisted (Claude Code) flow is strong.

---

# Onboarding benchmark (release acceptance criteria)

The intermediate-milestone deliverable: concrete, testable criteria for "repo-link → first verified
mapping without bouncing." A release candidate must satisfy:

1. **Install (non-dev path):** the documented install works **verbatim** from a clean machine —
   including creating a virtual environment and obtaining `uv` (or a non-`uv` fallback) — with a
   troubleshooting entry for each known failure (no-uv, no-venv, old Python). *Durable:* a real
   `pip install` from PyPI (milestone I2).
2. **Comprehension without an AI:** a domain-naive user can look up any record kind's meaning **from
   the CLI** (`cds explain <kind>`) and from the README glossary — no need to read source or a PDF.
3. **First run is guided:** `cds --help` and per-command help read plain-language-first; `cds init`
   tells the user what to do next; `cds guide` exists.
4. **The checker is trustworthy:** `cds verify` catches **dangling references** and **malformed
   links** (not just orphans) — a model that passes verify has no silently-broken links.
5. **Docs are internally consistent:** one canonical first-mapping + authoring order; filenames and
   clone URL match reality; no orphaned toolchains or leaked private paths.
6. **Payoff intact:** `cds compile` renders every stored link (incl. goal `--addresses`) into a clean
   brief.

A future cold-start re-run (post-PyPI) should have every persona — *including the non-technical
founder, with an AI assistant* — reach a verified mapping, and the docs-only technical newcomer reach
one **unaided**.
