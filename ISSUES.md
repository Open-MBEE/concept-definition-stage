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
- **SEBoK definition handling** — *guard locally, reference in distribution*: the verbatim
  definition is held in the **local** RDF as a hallucination guard (the work checks the
  authoritative text, never LLM memory); only *distribution* of NC text is excluded — published
  repos strip NC verbatim and carry term + reference. (Published redistribution filter: slice 6.)

## Open audit-flagged questions (not yet resolved)

- **Authorship / copyright identity.** `pyproject` names "Michael Zargham" while `LICENSE`
  says "cds contributors" — reconcile for an Open-MBEE community Apache repo.
- **NC-verbatim gitignore convention.** `sources/private/` + `*.verbatim.txt` no longer needed for
  SEBoK (text is never stored), but still relevant for snapshotting **private/ephemeral** sources
  (sponsor docs, transcripts) — confirm the convention for those.
