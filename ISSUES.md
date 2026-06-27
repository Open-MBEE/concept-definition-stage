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

- **Authorship / copyright identity.** `pyproject` names "Michael Zargham" while `LICENSE`
  says "cds contributors" — reconcile for an Open-MBEE community Apache repo.
- **`sources/private/` convention.** Reserved for genuinely-confidential source snapshots
  (sponsor docs, transcripts; v0.2). Verbatim canon TEXT is no longer gitignored (it lives in the
  committed M). Confirm `sources/private/` is the right home for confidential v0.2 material.
