# Retrieval queue (human-retrieval escalation — local fallback)

The agent **never fabricates canon**. When required canonical content is not yet secured, it is escalated to
a human here (and/or as a `retrieval` GitHub issue once the remote exists). The dependent term is **held out
of the build** until the artifact is provided and verified.

- **text** → wiki source grab (paste verbatim `{{...}}` wikitext) → `terms/<slug>.src.wiki`
- **image/figure** → screenshot → content-addressed snapshot in `sources/` (`sourceType=image`) + caption

**Status:** `pending` → `provided` → `verified`. A term builds only when `verified`.

**Built (verified, in `concept-definition.ttl`) — 23 terms:** System-of-Interest, Engineered System,
System Context, Stakeholder, Problem, Threat, Opportunity, Life Cycle, Concept Definition, Mission
Analysis, Stakeholder Needs and Requirements, System Requirement, Mission, Capability, Solution,
Measure of Effectiveness, Traceability, Operational Concept, Logical Architecture, Functional
Architecture, System Boundary, Function, System Definition. Each carries a verbatim SEBoK v2.14
glossary definition (spot-checked byte-identical to the held PDF), its upstream attribution
(`cds:definitionSource`), a citation, and a grounding edge.

## Held — genuinely blocked, NOT fabricated

| Term | Authority | Status | Reason |
|---|---|---|---|
| Risk | SEBoK | held — needs clean source | `pdftotext` corrupted the bulleted definition (1) (DAU 2003): merged tokens ("andThe", "2003)A risk") make a faithful transcription impossible. Needs a wiki source-grab. |
| MBSE | SEBoK | held — no glossary entry | "Model-Based Systems Engineering" has **no `(glossary)` entry** in SEBoK v2.14 (it is an article, not a glossary term). No verbatim definition to extract; decide whether to source it elsewhere or drop from the seed set. |

## In-prose concepts — need the topic-page sources (capture pass, slice 10)

MGO (Mission/Goals/Objectives), Integrated Set of Needs, need-statement format, Stakeholder Register,
Approving Authority, Driver, Constraint, Solution Class — these come from the **Business or Mission
Analysis** and **Stakeholder Needs Definition** topic pages (wikitext), not the glossary; secure those
sources before encoding.
