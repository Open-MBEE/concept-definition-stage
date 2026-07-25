# cds — Concept Definition Stage

**Define *what* a project is really about — its mission, goals, stakeholders, and needs — as
version-controlled, checkable data, with an AI helping you do it and a clean brief to show for it.**

`cds` is a small command-line tool for the **front end of a project**: the part where you work out the
problem, the mission, who has a stake, and what they actually need — *before* anyone designs a
solution. It records those decisions as structured data in **your own repository**, checks them for
common mistakes, and compiles them into a readable document. It's built on established systems-
engineering practice (the SEBoK "Concept Definition" knowledge area and INCOSE's needs/requirements
guidance), but you don't need to know any of that to start.

Who it's for: anyone scoping a project or product — a founder, a product manager, a systems or
software engineer — who wants the early "what are we even doing and for whom" thinking captured
rigorously instead of lost in a doc.

## Installation

> **Coming soon:** a `pip install` from PyPI (release in progress).
>
> **For now, install from source** (Python 3.11+; [`uv`](https://docs.astral.sh/uv/) recommended):
>
> ```bash
> git clone https://github.com/Open-MBEE/concept-definition-stage
> cd concept-definition-stage
> uv pip install -e .
> ```

## Quickstart

Work in **your own** project folder — `cds` writes your analysis there, never into its own install:

```bash
mkdir my-analysis && cd my-analysis
cds init --name my-analysis        # scaffolds the workspace (+ AI assistant files)

cds synthesis cd --title "My project"                     # start a mapping
cds new mission core --synthesis cd \
    --label "Reach a human" --description "Get a person to a verified human."
cds new goal reach --synthesis cd \
    --label "Reach" --description "Connect the seeker to a verified human."
cds new stakeholder seeker --synthesis cd \
    --label "Seeker" --description "The person trying to reach a human."
cds new need n1 --synthesis cd --for-stakeholder seeker --serves-goal reach \
    --label "Effortless reach" --description "The seeker needs to reach a human without skill."

cds verify                          # check the mapping for common mistakes
cds compile                         # -> concept-definition/briefs/concept-definition.md
```

**Using an AI-assisted editor** (Claude Code, etc.)? `cds init` drops in an assistant contract and a
facilitation skill, so the model in your editor can interview you and record your answers for you —
you talk, it ledgers. See the [full guide](docs/getting-started.md) for that flow.

## What you get

- Your concept definition as **deterministic RDF** in your repo (diff-able, reviewable).
- `cds verify` catches common slips (a "need" written like a requirement, a need with no stakeholder,
  duplicates, an empty set).
- `cds compile` produces a human-readable **brief** you can share.
- Nothing invented: every canonical definition is verbatim from a named authority (no LLM guessing).

## Learn more

- 📘 **[Getting started](docs/getting-started.md)** — the full first-session walkthrough.
- 📗 **[User guide](docs/user-guide.md)** — commands, the record kinds, the workflow.
- 🧭 **[Construction order](docs/construction-order.md)** — the method behind the tool.
- 🛠 **[Contributing](CONTRIBUTING.md)** and the authoring contract in **[AGENTS.md](AGENTS.md)**.

## Under the hood

Docs-as-code, model-view-controller: canonical **SKOS + PROV RDF** (the model), a tightly constrained
CLI (the controller), and pluggable **views** (a Markdown brief now; a Typst→PDF vocabulary render;
more later). Local-first Python (`rdflib` + `pyshacl`). It commits **SEBoK + INCOSE canon** — it does
not invent terminology — grounded so your scoping traces forward into later stages (SysML v2). The
deliverable is a **solution scoped as a System-of-Interest** — a system, capability, service, change,
or outcome, *never presumed to be a technology*. Full multi-stakeholder needs elicitation is on the
v0.2 track.

## License

**Apache-2.0** for the code (see [`LICENSE`](LICENSE)). Canonical standards text is handled carefully:
it lives in the local model as a verification guard, and rendered outputs are **license-keyed** — they
embed restricted canon (e.g. SEBoK, CC BY-NC-SA) only when your declared `text_license` is compatible,
otherwise they cite the authoritative source. See [`AGENTS.md`](AGENTS.md) and
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
