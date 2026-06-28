# cds — Concept Definition Stage

A **lifecycle-aware, stage-specific facilitation model** for the front end of systems engineering: the SEBoK
**Concept Definition** knowledge area (Business/Mission Analysis + Stakeholder Needs Definition). `cds`
commits SEBoK/INCOSE canon to version-controlled RDF — a docs-as-code, model-view-controller tool that takes
this stage from document-based to **model-based SE** without losing the qualitative inputs and judgments that
make concept definition real.

It does **not** invent ontology — it faithfully commits existing canon (SEBoK + INCOSE), grounded so scoping
traces forward into later stages (SysML v2). The deliverable is a **solution** (a system, capability, service,
operational change, or outcome — *never presumed to be a technology*) scoped as a System-of-Interest across
its full lifecycle.

## Status

**v0.1 — a reference vocabulary, exercised with precision.** 36 Concept Definition terms — the ~25 SEBoK
glossary terms plus in-prose article concepts (MGO, Solution Class, Driver/Constraint, Approving Authority,
Stakeholder Register, the need-statement format) and the GtWR need/requirement/Integrated-Set-of-Needs —
committed to a SKOS+PROV RDF scheme, dual-anchored to SysML v2 (construction correctness) and INCOSE NRM/GtWR
(prose canon, incl. the C1–C15 well-formedness characteristics), with full provenance (the ASoT /
boundary-object model), a license-keyed deterministic Typst→PDF view, and a Flexo MMS round-trip. Full
multi-stakeholder needs elicitation is v0.2.

## Architecture (MVC)

- **M (Model)** — canonical SKOS+PROV RDF, the authoritative spine.
- **V (View)** — pluggable downstream outputs: Typst→PDF now; OKF / MCP / Markdown later.
- **C (Controller)** — tightly constrained authoring (Pydantic write-scope guardrails + the AICC loop +
  the no-fabricated-canon discipline) — traceable and accountable.

Core is local-first Python (`rdflib` + `pyshacl`); the render layer additionally uses Typst + Pandoc.

## Discipline

`cds` never fabricates canon. Every definition is verbatim from a named authority and recorded as a
provenance-tracked boundary object; missing canon is escalated to a human, not guessed. See
[`AGENTS.md`](AGENTS.md) for the full authoring contract and the construction order.

## License

**Apache-2.0** for the code/structure (see [`LICENSE`](LICENSE)). Verbatim canon text is materialized in the
committed RDF (the M layer) as the hallucination guard; the **View** is license-keyed — it embeds restricted
canon (SEBoK is **CC BY-NC-SA**) only when the operator's `text_license` is compatible, otherwise it cites the
authoritative source instead of reproducing the text. Licenses are tracked, not enforced — the operator
judges compliance.
