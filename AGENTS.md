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

**Guard locally, reference in distribution.** We **do** hold the verbatim definition in our *local* RDF —
not to distribute it, but as a **hallucination guard**: the work checks every concept against the
authoritative text, never LLM weights, the same way an engineer checks SEBoK/the Handbook when it counts.
That local verbatim is the ground truth `verify` checks against (and is gitignored for NC sources). Only
*distribution* of NC text is excluded — committed/published artifacts strip NC verbatim and carry term +
reference (`cds:cites` + grounding) instead. Verbatim may be reproduced in distribution only for our own
gloss or reproduction-granting canon (e.g. the GtWR summary). The discipline: never fabricate or misrecall a
definition — secure the verbatim from the authority and check against it.

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
