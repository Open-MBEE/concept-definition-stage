# Construction order — structural integrity encodes process integrity

`cds` content is built **iteratively and loopily** (never one-shot) and evolves under version control. To
keep that epistemically sound, the implied order of operations is made **explicit** as a precedence DAG:
which triples must precede which for content to be correctly constructed. SHACL enforces it — each stage's
triples are invalid (Tier-1) until the prior stage's preconditions hold, so an out-of-order build is a
*structural* violation, not a silent process gap.

## The order

1. **Authority registered** — a `cds:Authority` (SEBoK, INCOSE, a sponsor, a stakeholder, a domain expert)
   exists before any source can bind to it.
2. **Citation record secured** — a `cds:Source` (boundary object) binds to the authority and moves through
   retrieval `pending → provided → verified`. Nothing downstream is valid until verified.
3. **Verbatim canon attached** — `skos:definition` / `cds:quote` may be attached **only on a verified
   source**. Verbatim text is held locally for verification; NC-source text is not redistributed.
4. **Concept created + cites the record** — a `cds:Concept` makes a concise `cds:cites` to the local citation
   record (two-hop traceability: concept → citation → authority).
5. **Concept grounded** — every concept carries ≥1 grounding edge (`rdfs:subClassOf` / a `skos:*Match`) to an
   existing vocabulary, and optionally a SysML v2 structural anchor. No bare terms.
6. **Concept admitted to the synthesis** — `prov:wasDerivedFrom` links the concept's sources into the
   `cds:Synthesis` (our authoritative output).
7. **Synthesis rendered / exported** — deterministic Typst→PDF; pluggable downstream adapters.

## AICC

The order *is* the **AICC** loop in motion, run by the Mission/Business Analyst (or any agent):
**Ask** (guided intake, prompting in construction order) → **Ingest** (retrieve/secure) →
**Confirm** (two-gate verbatim verification) → **Conform** (RDF per the order, SHACL-checked).

Documented in three registers, enforced in one: this prose, the `AGENTS.md` contract, and the CLI catechism
— all formally enforced by SHACL.
