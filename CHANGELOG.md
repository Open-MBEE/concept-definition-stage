# Changelog

All notable changes to `cds` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.1.0] — 2026-07-03

First versioned release. Full vertical slice of the Concept Definition stage: 36 terms built,
SHACL-verified, SysML v2–anchored, and rendered to PDF. Proven interoperability with the
Flexo MMS and SysML v2 services.

### Added

**Vocabulary (M layer)**
- 25 SEBoK v2.14 glossary terms with verbatim definitions, upstream attribution
  (`cds:definitionSource`), citations, and grounding edges
- 14 GtWR v4 characteristic statements (C1–C10, C12–C15) with verbatim definitions;
  C11 held pending a clean source copy
- 7 in-prose Stakeholder Needs Definition concepts (Goal, Objective, Solution Class,
  Driver, Constraint, Approving Authority, Need Statement)
- Integrated Set of Needs encoded from GtWR
- SysML v2 equivalence anchors for 5 constructs: `RequirementDefinition`, `PartDefinition`,
  `UseCaseDefinition`, `AttributeUsage`, and supporting properties — no vendored OWL cache,
  pure `owl:equivalentClass` axioms (DSG pattern)
- `cds:Waiver` RDF for accepted T2/T3 findings (append-only, `ontology/waivers.ttl`)

**Core infrastructure**
- `cds:Authority` / `cds:Source` / `cds:VerificationActivity` ASoT model (PROV-O)
- Content-addressed source snapshots in `sources/` (SHA-256 keyed)
- SHACL shapes enforcing 7-stage construction order (`ontology/shapes/`)
- Tri-severity verification: T1 = `sh:Violation` (build gate, never waivable),
  T2 = `sh:Warning`, T3 = `sh:Info`
- Deterministic byte-identical Turtle serialization (sorted URIs, stable timestamps)
- Pydantic write-scope guardrails on the authoring CLI
- `cds:LifecycleModel` with `text_license` / `code_license` (SPDX, operator-controlled)
- Parsimony engine: MIREOT usage-driven slices + per-source triple budgets

**CLI**
- `cds build` — YAML term sources → RDF
- `cds verify` — SHACL conformance gate
- `cds render` — license-keyed Typst→PDF (cite vs. reproduce based on `text_license`)

**Interoperability**
- Flexo MMS Layer-1 round-trip client (`src/cds/flexo.py`) — proven in-memory; live tests
  skip without credentials
- Flexo SysML v2 service integration (roadmap T9): 3-test suite — connectivity, corpus
  load, and Definition→Usage bridge via live Starforge elements

**Tests**
- 109 unit and integration tests (0 failures)
- Machine-verified faithfulness: GtWR always-on, SEBoK gated on operator-held PDF
- License-leak, provenance-integrity, and offline SysML join proofs
- Live T9 SysML v2 interop tests (auto-skip without `.env`)

**Docs & governance**
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1)
- `NOTICE`, `THIRD_PARTY_LICENSES.md`
- `docs/sources.md` — REFERENCE-tier source acquisition guide
- `ROADMAP.md` — 8 development tracks + pre-push readiness checklist
- `AGENTS.md` — vendor-neutral authoring contract (no-fabrication rule)

### Held / known issues

- **C11 (Consistent):** GtWR PDF text layer drops one word; `skos:definition` awaits a clean
  source copy (`docs/retrieval-queue.md`)
- **X7 (Incremental build):** Build is currently all-or-nothing for unverified terms; an
  automated per-term `retrieval_status` held-out mechanism is deferred to v0.2
- **w3id registration:** `https://w3id.org/cds#` namespace is used but not yet registered
  (non-blocking; T2 in the roadmap)

[0.1.0]: https://github.com/Open-MBEE/cds/releases/tag/v0.1.0
