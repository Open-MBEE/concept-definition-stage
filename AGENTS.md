# AGENTS.md — `cds` authoring contract (LLM-agnostic)

This file is the **vendor-neutral** operating contract for any agent (LLM or the CLI itself) or human
working on `cds`. It is adapted from `ant-rdf`'s authoring contract but is not tied to any one tool. Tool-
specific files (e.g. `CLAUDE.md`) may symlink to this file.

`cds` ("Concept Definition Stage") commits SEBoK/INCOSE **Concept Definition** canon to version-controlled
RDF. The authoritative scoping document is the approved plan
(`~/.claude/plans/i-want-a-build-cryptic-sundae.md`).

## The one inviolable rule: no fabricated canon

**The agent NEVER fabricates or paraphrases canon.** A `skos:definition` or `cds:quote` may contain only
text a human retrieved verbatim from a named authority (the held SEBoK v2.14 PDF, the GtWR PDF, or another
registered source).

When required canon is not yet secured (a blocked page, a paywalled standard, an image/figure), the agent
**stops and escalates the retrieval to a human** (a `retrieval` GitHub issue, or a row in
`docs/retrieval-queue.md`). The dependent term is **held out of the build** until secured + verified.
Never guess; never invent; never cite a derivative (the `Incose-Extraction-*` / `SE-Primer` repos and
`Terminology`'s curated text are **orientation only**, never an authority).

**Text in the model, citation in the view.** The verbatim definition is **materialized in the M layer (RDF
triples) and committed** — the software must hold the standards to enforce them, and the verbatim is the
**hallucination guard** (the work checks the authoritative text, never LLM weights, the way an engineer
checks SEBoK/the Handbook when it counts). Do **not** gitignore it or strip it from the RDF. Non-distribution
is enforced at the **V layer**: compilers/views are *restricted from emitting* the verbatim and instead cite
the **authoritative source** (e.g. the sebokwiki URL), not our local copy. RDF triples are not
human-consumable, so holding the text in M is not "distributing" it. (Engineering enforcement supersedes the
licensing-bureaucracy layer — Zargham's deliberate call.) The discipline: never fabricate or misrecall a
definition — secure the verbatim and check against it.

**License-keyed View rendering (operator-controlled).** The lifecycle model (`cds:LifecycleModel`) declares a
`text_license` (default `CC-BY-NC-SA-4.0`) and a `code_license` (default `Apache-2.0`). The View renders
restricted canon (e.g. SEBoK definitions, which are CC-BY-NC-SA) **only when `text_license` is compatible
with SEBoK** (the BY-NC-SA family); otherwise it cites the authoritative source. Any report rendered with
restricted canon inherits that text license (ShareAlike). The **operator, not the tool**, chooses the
licenses and is responsible for whether the use qualifies (e.g. non-commercial education). The default
renders SEBoK; an operator wanting unencumbered outputs sets a permissive `text_license` (→ cite-only).
License ids are SPDX (or custom) — user-extensible.

## Authorities, not derivatives

Every definition **backtraces** to a primary authority — SEBoK or an INCOSE primary reference (SE Handbook,
NRM, GtNR, GtWR) — and is secured verbatim, recorded as a boundary object (`contentHash` + `retrievedAt` +
`verifiedAt`). Derivatives orient us to *what* to look up; they are never the source of canon.

## Construction order (structural integrity encodes process integrity)

Build in this precedence order — each stage's triples are invalid (SHACL T1) until the prior stage holds:

1. **Authority registered** (`cds:Authority`).
2. **Citation record secured** (`cds:Source` bound to the authority; `pending → provided → verified`).
3. **Verbatim canon attached** (`skos:definition` / `cds:quote`) — only on a `verified` source.
4. **Concept created + `cds:cites` the record.**
5. **Concept grounded** (alignment edge) + optionally **SysML-anchored**.
6. **Concept admitted to the `cds:Synthesis`** (`prov:wasDerivedFrom`).
7. **Synthesis rendered / exported.**

This is the **AICC** loop in motion: **Ask** (guided intake) → **Ingest** (retrieve) → **Confirm** (verbatim
verification) → **Conform** (RDF per the construction order, SHACL-checked). The mapping is loopy/iterative;
git + deterministic RDF make each commit a diffable, auditable state.

## Two enforcement layers

- **SHACL** governs the RDF (structure, grounding, construction-order preconditions).
- **Pydantic** governs the *tool* — CLI input validation + **write-scope guardrails** (what the CLI may/may
  not write). The C (authoring) layer is tightly constrained; the V (output) layer is pluggable.

## The verification gate (`cds verify`)

`cds verify` validates the graph against `ontology/shapes/*.ttl`. The **gate is SHACL conformance** — the
construction is correct iff pyshacl reports `conforms` (with warnings/infos allowed, exactly "no Tier-1
violation"). We surface the tool's own verdict rather than re-deriving it. On top of that verdict sits a
**Pythonic** reporting layer: a **tri-severity** ladder mapped to SHACL's native levels — **T1 = `sh:Violation`**
(fails the build), **T2 = `sh:Warning`**, **T3 = `sh:Info`** — exposed as plain `Finding`/`VerifyResult`
objects (no pyshacl results graph or SHACL vocabulary leaks to callers). The shapes encode the construction
order structurally (every check is a *named* shape, so each finding has a stable `rule`):

- a `cds:Source` must attribute to a *registered* `cds:Authority` (stage 1 precedes stage 2);
- the **verbatim-in-M hallucination guard** (stage 3): a `cds:Term` that materializes a `skos:definition`
  must `cds:cites` a source whose retrieval activity is **verified** — verbatim never enters the build
  unless it traces to a verified retrieval;
- a term must cite a source (stage 4), be grounded by ≥1 alignment edge — no bare terms (stage 5), and be
  admitted to a scheme (stage 6).

**Waivers are first-class RDF data** (`cds:Waiver`, carried in the graph — see `ontology/waivers.ttl`), not
a config side-car: the record of what was consciously accepted is versioned with the model and selects a
finding by its `rule`. They are **append-only** and can only ever suppress a T2/T3. **T1 is never waivable**
— a waiver that selects a Violation has no effect on it, and waivers never touch `conforms`.

**Definition of done (v0.1) — the gate:** `cds verify` **conforms** (T1-clean) on the seed + self-model
fixture; every built term is grounded (no bare terms) and its verbatim traces to a verified source;
warnings/lint are either resolved or carry an append-only `cds:Waiver` with a recorded reason. (This
restates the plan's v0.1 Definition of Done — keep the two in sync.)

## Determinism + redistribution

- The canonical TTL build is **byte-deterministic**: URIs not blank nodes for reified records; sorted-Turtle
  writer; timestamps are stable inputs (never build-time `now()`).
- **Redistribution:** SEBoK is **BY-NC-SA**. Published outputs **cite + link** (term + URL + verified-as-of);
  verbatim canon stays in local citation records for verification and is **not redistributed**. Our minted
  code/structure is **Apache-2.0**.

## Don't

- Don't hand-edit the canonical `.ttl` (YAML term sources are the ergonomic surface; the CLI compiles).
- Don't import the full SysML v2 library (demand-driven MIREOT slices only; reference ≠ materialize).
- Don't take `ant-rdf` as a code dependency (adapt-and-vendor its infra; cite it as a research reference).
