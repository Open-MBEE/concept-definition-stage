# Robustness battery — 2026-07-25

Scripted edge cases run directly against the installed CLI in a throwaway repo
(`uv pip install -e <cds>` → `cds init`). `[exit=N]` is the process exit code.

| # | Check | Result |
| --- | --- | --- |
| 1 | Empty-project `cds verify` / `cds compile` | OK (exit 0); brief renders with headers, no content. Graceful. |
| 2 | Unknown kind (`cds new bogus …`) | Clean message + `[exit=2]`. |
| 3 | Missing `--synthesis` (non-interactive) | Clean message + `[exit=2]`. |
| 4 | **Re-author same slug, changed description** | ❌ **BUG** — appended: `goal/reach` ended with TWO `dcterms:description` and TWO `rdfs:label` values. No update/upsert. |
| 5–6 | `shall` / orphan / duplicate detection | Fired: `NeedFormShall`, `NeedWithoutStakeholder`, `DuplicateStatement` (all T2). exit 0 (warnings don't fail gate). |
| 7 | `queue set` invalid status / nonexistent id | Both clean messages + `[exit=2]`. |
| 9 | **Slug with a space** (`cds new goal "bad slug"`) | ❌ **BUG/CRASH** — unhandled rdflib `Exception` + full traceback, `[exit=1]`. Slug with parens accepted (fragile IRI). |
| 10 | `tension add` without `--between` | Allowed (between optional). Fine. |
| 12 | Byte-stability of `cds compile` | PASS (identical hash on re-run). |
| 13 | `cds init` idempotency / re-run | PASS — all files "exists, skipped". |
| 14 | **CDS-repo isolation** (`git -C <cds> status`) | Clean — the test wrote nothing into the CDS repo. |

## Bugs surfaced

- **Re-author appends, not upserts** (#4) — confirmed later, in context, by both sessions.
- **No slug validation** (#9) — a spaced slug crashes; loose chars accepted.

Everything else behaved correctly, including all bad-input paths, conflict detection, determinism,
`init` idempotency, and repo isolation.
