# cds Roadmap — Open-MBEE public push and beyond

v0.1 is built: the full vertical slice (solicit → represent → present) + Flexo interop, 36 terms +
the C1–C15 companion vocab, dual-anchored (SysML v2 + GtWR/NRM), SHACL-verified, license-keyed view,
self-model dogfood. This roadmap turns it into a published Open-MBEE OSS project and scopes what's next.

Each item below is written to become a **GitHub issue** once the public remote exists (`gh issue create`
with the suggested label). `P*` = pre-push readiness; `T*` = the eight requested tracks; `X*` =
additionally identified.

---

## Pre-push readiness (do before/at the public push)

### P1 — CI workflow (`ci`, `blocker`)
**What:** GitHub Actions running `pytest` + `ruff check` + `mypy --strict` on PR and push (Python
3.11 + 3.12 matrix), plus a determinism job that regenerates `cds-core.ttl` / `concept-definition.ttl`
and fails on diff.
**Why:** the public repo must be green-by-construction; the slice-1 CI was a stub.
**Done when:** a passing CI badge on `main`; the determinism check guards the committed artifacts.

### P2 — Third-party canon & license compliance + NOTICE (`legal`, `blocker`)
**What:** a `NOTICE` / `THIRD_PARTY_LICENSES.md` enumerating each canon source (SEBoK v2.14 CC-BY-NC-SA,
GtWR v4 summary reproduction-with-attribution, ANSI/EIA, ISO/IEC/IEEE attributions in `definitionSource`)
and the **standards-in-code** rationale for materializing verbatim text in the committed M.
**Why:** the public Open-MBEE repo commits verbatim BY-NC-SA SEBoK definitions in `concept-definition.ttl`
(the hallucination guard, Delta D2). This is a deliberate call but must be documented and confirmed
acceptable for an Open-MBEE-hosted repo; the **license-keyed View** is the redistribution control.
**Done when:** NOTICE lands; an Open-MBEE maintainer signs off on the M-layer verbatim policy.

### P3 — Governance & identity (`governance`)
**What:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, Open-MBEE community norms; reconcile the open
`pyproject` author identity (Zargham vs "cds contributors") flagged in `ISSUES.md`.
**Done when:** contribution docs present; author/copyright fields consistent across `pyproject` + `LICENSE`.

### P4 — Release & versioning (`release`)
**What:** SemVer + git tags + `CHANGELOG.md`; `owl:versionInfo` on the scheme already tracks the version.
Cut **v0.1.0**. A release checklist (build/verify/render green + determinism + tag).
**Done when:** `v0.1.0` tagged; CHANGELOG started.

### P5 — Source-acquisition doc (`docs`)
**What:** document that operators obtain the SEBoK v2.14 PDF and the GtWR v4 summary themselves (the
PDFs are NOT vendored — REFERENCE tier), and how the build references them by content hash.
**Done when:** `docs/sources.md` explains acquisition + the hashes in `seed.py`.

---

## The eight tracks

### T1 — Publish to PyPI (`packaging`)
**What:** publish `cds` to the PyPI index (hatchling build already configured). Trusted-publisher (OIDC)
release from CI on tag; `cds` console script ships.
**Acceptance:** `pip install cds` (or the final dist name) installs the CLI; a tagged release auto-publishes.
**Notes:** confirm the distribution name (`cds` is likely taken on PyPI — reserve `concept-definition-stage`
or an `openmbee-cds` name). Decide what ships: code only (the canon PDFs and operator data stay external).

### T2 — Register `w3id.org/cds` (`namespace`)
**What:** PR to the w3id.org community repo so `https://w3id.org/cds#` (+ `/term/`, `/src/`, `/license/`,
`/waiver/`, `/characteristic/`, `/scheme/`) resolve (303/redirect to the published ontology + docs).
**Acceptance:** the IRIs dereference to the cds-core / concept-definition artifacts (or the docs site).
**Notes:** currently used as-is (non-blocking). Coordinate the redirect target with T3 (GitHub Pages).

### T3 — mkdocs → GitHub Pages (`docs`)
**What:** configure mkdocs(-material) + mkdocstrings to build the design spec, construction-order prose,
auto API docs, and the rendered vocabulary; publish to GitHub Pages from CI.
**Acceptance:** a live Pages site on push to `main`; API reference + the Concept Definition vocabulary
(the Typst/HTML view) are browsable. Wire the w3id redirect (T2) here.

### T4 — OSLC requirements-ontology compatibility (`interop`, `integration-test`)
**What:** integration tests that the cds vocabulary aligns with the **OSLC RM/QM** requirements ontologies
(the same `oslc-rm.ttl` / `oslc-qm.ttl` flexo-rtm vendors). Map `cds:Term` need/requirement concepts to
`oslc_rm:Requirement` etc.; round-trip a cds need/requirement into an OSLC-RM shape and back.
**Acceptance:** skip-if-absent integration tests proving cds ↔ OSLC-RM mappings hold; an alignment file
(`ontology/extracts/oslc-rm.alignment.ttl`) of the `skos:*Match` edges.
**Notes:** this is also the first real consumer of the dormant parsimony engine — OSLC becomes a cached
external source to MIREOT-slice + budget.

### T5 — Next stage: System Requirements Definition (`design`, `next-stage`)
**What:** an initial design sketch (ADR + skeleton) for the **System Definition** stage's first activity,
**System Requirements Definition**, per the INCOSE SE Handbook v5 / SEBoK Fig 1 — the activity that
*transforms needs into requirements*.
**Critical framing:** cds's output — the **well-conformed integrated set of needs + life cycle concepts**
(`concept-definition.ttl`) — is *defined as the input* to this next stage. The next-stage tool **consumes
that artifact** and shares the `core`/`stages` seam (no fork).
**Acceptance:** an ADR documenting the handoff contract (what fields/shapes the next stage reads), a
`stages/system_requirements/` skeleton that loads `concept-definition.ttl` as input, and a SHACL
precondition that the input is a conformed, baselined integrated set of needs.

### T6 — Remote Flexo (Layer-1) + hybrid RDF/git interop (`interop`, `integration-test`)
**What:** exercise a **live Flexo MMS Layer-1** round-trip (the `FlexoHttpClient` path, currently
creds-gated/skipped) against the **Starforge** remote (`https://try-layer1.starforge.app`, `FLEXO_URL` /
`FLEXO_TOKEN` — the same deployment flexo-rtm's `@pytest.mark.live` tests use), plus a **hybrid RDF + git**
tracking model: the scheme versioned in git, branches/named-graphs in Flexo, reconciled (track Open-MBEE
`flexo-conflict-resolution-policy-research`).
**Acceptance:** CI integration job (skip-if-no-creds) that commits the scheme to a Starforge Layer-1 branch,
reads it back isomorphic, and validates a git↔Flexo sync of the same graph; an ADR on the hybrid model.

### T9 — cds ↔ SysML v2 models via the Flexo **SysML v2 service** (`interop`, `integration-test`, `sysml`)
**What:** test what happens when the cds scheme is **discussed alongside real SysML v2 models** stored in
Flexo through the **SysML v2 service** (the OMG SysML v2 API & Services / `omg-sysml:` RDF form) — *not* the
generic Layer-1 SPARQL service. This is the real validation of the SysML anchoring's purpose: do cds's
equivalence axioms actually connect cds terms to live SysML v2 model elements?
**Why / finding:** the alias target was **corrected to `https://www.omg.org/spec/SysML/20240801/SysML#`**
(flexo-rtm + the Flexo SysML v2 service namespace) — it was previously the older ADCS-demo `…/20240501/`,
which would *not* have matched any real SysML v2 model. This track is how that alignment gets proven.
**Acceptance:**
- A fixture corpus of real SysML v2 RDF (model flexo-rtm's `examples/sysmlv2/` — `omg-sysml:RequirementUsage`
  / `PartUsage` with `elementId`/`qualifiedName`/`owner`), loaded into a Flexo SysML v2-service branch.
- An integration test (skip-if-no-creds, against Starforge) that loads cds's scheme + the SysML v2 models
  into the same store and runs SPARQL that traverses cds-term → `owl:equivalentClass`/`equivalentProperty`
  → `omg-sysml:*` → an actual SysML v2 element — proving the anchor "lands."
- Resolve the **Definition vs Usage layer** explicitly: cds anchors to `*Definition` (it's a *vocabulary*),
  while SysML v2 models instantiate `*Usage`. Document/encode how a cds `RequirementDefinition` anchor
  relates to a model's `RequirementUsage` (e.g. via the SysML v2 definition↔usage typing), so queries that
  join cds canon to a model resolve correctly. Reuse flexo-rtm's `sysmlv2-anchored.shacl.ttl` profile as a
  conformance reference.
**Wired up (env ready):** the OpenMBEE Flexo **SysML v2 service** is live at
`https://experimental.starforge.app/`, accessed via the Open-MBEE **`sysmlv2-python-client`**
(`SysMLV2Client(base_url, bearer_token)` → `get_projects()`). Creds are in the gitignored `.env`
(`FLEXO_SYSMLV2_URL` / `FLEXO_SYSMLV2_TOKEN`); `tests/interop/test_flexo_sysmlv2.py` is the connectivity
scaffold (auto-skips until the client is installed). Run with
`uv run --env-file .env pytest tests/interop/test_flexo_sysmlv2.py`.
**Done offline already (`tests/unit/test_sysml_join.py`):** the Definition-level anchor join resolves via
an explicit `owl:equivalentClass` SPARQL path — **no OWL-RL needed** — and the Definition-vs-Usage gap is
demonstrated, so T9's remaining work is the live service + the typing bridge, not the reasoning question.
**Notes:** depends on T6 (Starforge creds) and the corrected namespace (done).

### T7 — Worked-example / educational repo (`education`, `new-repo`)
**What:** a **separate** public repo: a complete worked example (a real SoI's concept definition built with
cds) + educational content on **how and why** to use these tools — the AICC loop, the construction order,
the no-fabricated-canon discipline, the license-keyed view, the SysML/NRM anchoring.
**Acceptance:** the example repo builds/verifies/renders green using `cds` as a dependency; a tutorial walks
through authoring a term, securing a source, grounding, and rendering; ties to SEBoK Table 2 (the v0.2
needs-elicitation fixture) as the concrete case.
**Notes:** keep the heavy canon PDFs out; reference cds's source-acquisition doc (P5).

### T8 — LLM ergonomics + hosting services (`llm`, `design`)
**What:** (a) **define + test LLM ergonomics** — measure whether an LLM can reliably drive the CLI / author
YAML terms / run the AICC loop within the `AGENTS.md` contract without fabricating canon; add an MCP output
adapter (the V-layer `MCP` plugin) exposing the scheme + provenance to an LLM. (b) **Local hosting guidance**
— explicit instructions for running a local service combining cds + a **local LLM** (e.g. Ollama/llama.cpp
via MCP) as a concept-definition assistant. (c) **Sketch a web-hosted service** — architecture for a hosted
multi-tenant cds (the analyst-facing solicitation UI + the M/V/C separation as the service spine).
**Acceptance:** an `llm-ergonomics` eval harness (prompts → expected CLI/YAML actions, scored for
no-fabrication + construction-order adherence); a `docs/hosting-local.md` runbook; a `docs/hosting-web.md`
architecture sketch. **Discipline anchor:** the LLM is a prosthesis for retrieval/authoring, never a source
of canon — the eval must penalize any fabricated definition.

---

## Additionally identified (not in the original list)

### X1 — Resolve the remaining content hold (`canon`)
C11 (Consistent) set-characteristic: the held SEBoK/GtWR summary PDF drops one word ("is consistent if
[it] contains"). Secure a clean GtWR copy to add C11's `skos:definition`. (All other holds resolved.)

### X2 — v0.2 feature backlog (`v0.2`)
From the plan's "Explicitly deferred": the working **needs-elicitation loop** (AICC over multi-stakeholder
inputs); **Claim / Perspective / invariance** machinery (as-is/to-be, divergent perspectives — ant-rdf R3
reification); **`cds:Synthesis`** (the integrated-set-of-needs *instance*, agent∩entity); the **Marimo
provenance-audit view** (civic SPARQL→JSON→view); the **multi-party conflict-resolution policy**; **RAS /
OML-OWL export** interfaces.

### X3 — `omg-sysml` namespace verification (`namespace`)
The alias target is now `https://www.omg.org/spec/SysML/20240801/SysML#` (aligned to flexo-rtm / the Flexo
SysML v2 service). Remaining: verify the five anchored construct local-names (`RequirementDefinition`,
`PartDefinition`, `PartUsage`, `UseCaseDefinition`, `AttributeUsage`) exist verbatim in that OMG release and
match the Flexo SysML v2 service's element types (validated end-to-end by T9). Optional OML/OWL export.

### X4 — Parsimony materialization, once a real cache exists (`parsimony`)
When OSLC (T4) or PROV-O/SKOS are added as cached external sources, wire `build_extracts` materialization +
per-source triple budgets into `cds build` (the report wiring is already live; only the caches are missing).

### X5 — Perspectives & in-prose v0.2 captures (`canon`, `v0.2`)
Encode the as-is/to-be & green-/brown-field & push/pull **perspective primitives** and the SEBoK **Table 2
example need statements** (the v0.2 conformance fixture) when the claims/perspective machinery (X2) lands.

### X6 — Test hardening (`testing-hardening`)
From the pre-push test review. **Done now:** all-terms license-leak property, provenance-integrity audit,
machine-verified faithfulness (GtWR always-on + SEBoK PDF-gated), and the offline SysML-anchor join.
**Remaining:** (a) **build idempotence** — `cds build` twice yields zero git diff (docs-as-code, no commit
churn); (b) **malformed-authoring rejection** — a bad term YAML (missing `pref_label`, invalid grounding
relation, duplicate slug) is rejected by the C layer with a clear error; (c) **author-a-new-term UAT** —
the analyst's full loop (write YAML → build → verify → render) end-to-end; (d) **break-a-term UAT** — the
plan's own check: drop a citation / corrupt a `content_hash` → non-zero exit with an actionable T1 message.

### X7 — Incremental build vs all-or-nothing — **decision needed** (`design`, `discipline`)
The plan promised *incremental, not all-or-nothing*: held/unverified terms are excluded and the rest still
builds. As implemented, a term citing an unverified source **fails `cds verify` (T1) → the whole build
fails**; incrementality is currently *manual discipline* (only author verified terms; held ones live in
`docs/retrieval-queue.md`), not an automated held-out mechanism. **Decide:** is manual incrementality fine
for v0.1, or should the build read a per-term `retrieval_status`, **hold** pending terms (T2 + a build-report
line), and build the verified remainder? This matters most for T7 (worked example) and T8 (LLM-driven
authoring), where automated held-out is what keeps an LLM from forcing a fabricated definition through.
