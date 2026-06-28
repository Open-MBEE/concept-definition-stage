# Deferred issues — to file as GitHub issues once the Open-MBEE remote exists

These are tracked here until the public remote is provisioned; then each becomes a `gh` issue.

- **w3id registration.** Register `https://w3id.org/cds#` via a PR to the w3id.org community
  repo so the namespace resolves. (Non-blocking; the IRI is used as-is until then.)
- **`sysml` namespace alignment.** The `sysml:` prefix currently maps to a placeholder URI
  (`https://www.omg.org/spec/SysML/#`). Align it to the authoritative OMG SysML v2 / openCAESAR
  OML namespace when the SysML v2 OWL cache is generated (slice 7). Kept simply `sysml` for now.

## Resolved

- **URI scheme** — hash (`cds#`) for vocabulary/classes, slash (`cds/term/`, `cds/src/`) for
  individuals. Confirmed.
- **SEBoK definition handling** — *text in the model, citation in the view*: verbatim canon is
  **materialized in the committed RDF (M)** so the software can enforce standards + guard against
  hallucination; the **View layer** excludes the text and cites the authoritative source. Engineering
  enforcement > licensing bureaucracy (Z's deliberate call). RDF isn't human-consumable, so holding the
  text in M is not "distributing" it. (View-layer exclusion lands slice 8.)

## Open audit-flagged questions (not yet resolved)

- **SEBoK source = REFERENCE tier (slice 6 decision — diverges from the plan's "snapshot tier").**
  The plan's implementability notes say the SEBoK v2.14 PDF is "held (snapshot tier)", but it was
  registered **REFERENCE-tier** instead: (a) the tiering rule keeps public curated canon to
  hash + locator, not vendored; (b) it is 14.7 MB; (c) SEBoK is BY-NC-**SA**, so vendoring the whole
  work into a public repo is redistribution. The content hash pins the version; the verbatim
  *definitions* (a small excerpt) still live in committed M (Delta D2). The operator holds the PDF.
  Contrast GtWR, which IS snapshot-tier (small + reproduction-with-attribution). **Confirm.**
- **Engineered System glossary-artifact transcription.** The SEBoK PDF renders two inline wiki-links
  inside the Engineered System definition as "SE Life Cycle (glossary)" / "System Context (glossary)".
  The `(glossary)` link artifacts were **omitted** so the definition reads as authored. This is the one
  seeded definition not byte-identical to pdftotext output. **Confirm** the artifact-stripping is the
  right faithful-transcription call (the alternative: keep them verbatim, artifacts and all).
- **Authorship / copyright identity.** `pyproject` names "Michael Zargham" while `LICENSE`
  says "cds contributors" — reconcile for an Open-MBEE community Apache repo.
- **`sources/private/` convention.** Reserved for genuinely-confidential source snapshots
  (sponsor docs, transcripts; v0.2). Verbatim canon TEXT is no longer gitignored (it lives in the
  committed M). Confirm `sources/private/` is the right home for confidential v0.2 material.
