# Deferred issues — to file as GitHub issues once the Open-MBEE remote exists

These are tracked here until the public remote is provisioned; then each becomes a `gh` issue.

- **w3id registration.** Register `https://w3id.org/cds#` via a PR to the w3id.org community
  repo so the namespace resolves. (Non-blocking; the IRI is used as-is until then.)
## Resolved

- **`sysml` namespace alignment + vendoring (slice 7).** Adopted the established DSG pattern (from
  ADCS-lifecycle-demo): **no openCAESAR/JVM, no vendored SysML OWL cache.** `sysml:` =
  `https://www.omg.org/spec/SysML/2.0/` (local terms) aliased to `omg-sysml:` =
  `http://www.omg.org/spec/SysML/20240501/` (the OMG OWL rendering) via `owl:equivalentClass` /
  `owl:equivalentProperty` axioms generated for the invoked constructs only (+ minimal OMG-side stubs).
  Pure-Python, parsimonious; replaces the plan's "generate via openCAESAR, vendor a static cache".

- **URI scheme** — hash (`cds#`) for vocabulary/classes, slash (`cds/term/`, `cds/src/`) for
  individuals. Confirmed.
- **SEBoK source = REFERENCE tier; vendor at the term level, not the PDF** (Zargham confirmed).
  The 14.7 MB BY-NC-SA PDF is **not** in the repo — registered as a REFERENCE-tier source (content
  hash + locator + checksum verification; operator holds the PDF). What we vendor is **term-level**:
  each term's verbatim definition + its ASoT provenance (citation to the source, grounding edge, and
  `cds:definitionSource` recording SEBoK's own upstream attribution, e.g. Dictionary.com 2012,
  ISO/IEC/IEEE 2015). The **ASoT provenance data is our primary contribution** — and capturing SEBoK's
  upstream attributions makes explicit that we leverage SEBoK's *curation of already-public content*,
  not proprietary text. (Contrast GtWR: small + reproduction-with-attribution → snapshot tier.)
- **Engineered System transcription — verified faithful.** Re-checked character-by-character: the
  encoded definition is identical to the held PDF once the two inline `(glossary)` wiki-link render
  artifacts are removed (it is the one term not byte-identical to raw `pdftotext`, by that deliberate
  artifact-stripping only — no transcription error). The `(Created for SEBoK)` attribution is captured
  in `cds:definitionSource`.
- **SEBoK definition handling** — *text in the model, citation in the view*: verbatim canon is
  **materialized in the committed RDF (M)** so the software can enforce standards + guard against
  hallucination; the **View layer** excludes the text and cites the authoritative source. Engineering
  enforcement > licensing bureaucracy (Z's deliberate call). RDF isn't human-consumable, so holding the
  text in M is not "distributing" it. (View-layer exclusion lands slice 8.)

## Open audit-flagged questions (not yet resolved)

- **Authorship / copyright identity.** `pyproject` names "Michael Zargham" while `LICENSE`
  says "cds contributors" — reconcile for an Open-MBEE community Apache repo.
- **`sources/private/` convention.** Reserved for genuinely-confidential source snapshots
  (sponsor docs, transcripts; v0.2). Verbatim canon TEXT is no longer gitignored (it lives in the
  committed M). Confirm `sources/private/` is the right home for confidential v0.2 material.
