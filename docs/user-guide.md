# User guide

A reference for the commands and concepts. If you haven't yet, read
[Getting started](getting-started.md) first. Run `cds --help` and `cds <command> --help` for the
authoritative, always-current details.

## The workspace

`cds` operates on **your** project, discovered from a `cds.toml` marker. Create it with `cds init`
(in your project folder). Everything is written under `concept-definition/` in that repo — never into
the `cds` install. You can point at a project explicitly with `--project` or `CDS_PROJECT`.

## The model

- A **synthesis** is the container for one concept-definition mapping (`cds synthesis`).
- **Records** are instances typed by the reference vocabulary — `mission`, `goal`, `objective`,
  `problem`, `opportunity`, `driver`, `constraint`, `moe`, `stakeholder`, `need`. Each carries a
  label, a description, and (optionally) links to other records.
- **Side ledgers** hold things that aren't part of the integrated set: the **parking-lot** (out-of-
  scope ideas), the **retrieval queue** (open unknowns), and **tensions** (named conflicts).

## Commands

### Authoring

- `cds init [PATH] [--name N]` — scaffold a workspace.
- `cds synthesis SLUG --title T [--description D]` — create/update the mapping container.
- `cds new KIND SLUG --synthesis S --label L --description D [links…]` — author a record. Links:
  `--for-stakeholder`, `--serves-goal`, `--refines`, `--addresses`, `--segment/--interest/--influence`
  (stakeholders), `--supersedes`, `--cites`. Add `--interactive` to be prompted.
- `cds show KIND SLUG` / `cds list KIND` — read back what's recorded.
- `cds rm KIND SLUG` — delete a record.

### Side ledgers

- `cds park add|list|rm …` — parking-lot for out-of-scope ideas.
- `cds queue add|set|list|rm …` — retrieval queue; advance status `pending → provided → verified`.
- `cds tension add|resolve|rm …` — record and reconcile conflicts (resolved ones drop from the brief).

### Checking & output

- `cds verify` — validate the mapping (structure + cross-record checks). Findings are tiered:
  **T1** fails, **T2/T3** are surfaced but don't fail. Common flags: a `need` written with "shall",
  a `need` with no stakeholder or no goal, duplicate statements, an empty integrated set.
- `cds compile [--output PATH]` — write a deterministic Markdown **brief**.
- `cds render` — the license-keyed Typst→PDF vocabulary view (needs the `typst` binary).

## Correcting records

Authoring is an **upsert**: re-running `cds new` with the same slug replaces that record cleanly.
Keep a change trail with `--supersedes <slug>`; delete with `cds rm`. Never hand-edit the `.ttl`.

## The discipline

`cds` never fabricates canon: every term's definition is verbatim from a named authority (SEBoK /
INCOSE). Needs use "need form" (never "shall") — requirements come in a later stage. See
[Construction order](construction-order.md) for the method.
