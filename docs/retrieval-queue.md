# Retrieval queue (human-retrieval escalation — local fallback)

The agent **never fabricates canon**. When required canonical content is not yet secured, it is escalated to
a human here (and/or as a `retrieval` GitHub issue once the remote exists). The dependent term is **held out
of the build** until the artifact is provided and verified.

- **text** → wiki source grab (paste verbatim `{{...}}` wikitext) → `terms/<slug>.src.wiki`
- **image/figure** → screenshot → content-addressed snapshot in `sources/` (`sourceType=image`) + caption

**Status:** `pending` → `provided` → `verified`. A term builds only when `verified`.

**Built (verified, in `concept-definition.ttl`) — 8 terms:** System-of-Interest, Engineered System,
System Context, Stakeholder, Problem, Threat, Opportunity, Life Cycle (includes the load-bearing
problem/threat/opportunity trio).

## Glossary terms still to extract from the held SEBoK v2.14 PDF

The verbatim text is in hand (`cds:src/sebok-v2-14`); each `pending-extraction` term needs its
definition (1) extracted, spot-checked, and encoded as a YAML term (definition + citation +
grounding), then it builds. (Not blocked — just not yet extracted.)

| Term | Authority | Source URL | Artifact | Status |
|---|---|---|---|---|
| Concept Definition | SEBoK | sebokwiki.org/wiki/Concept_Definition_(glossary) | text | pending-extraction |
| Mission Analysis | SEBoK | sebokwiki.org/wiki/Mission_Analysis_(glossary) | text | pending-extraction |
| Stakeholder Needs and Requirements | SEBoK | sebokwiki.org/wiki/Stakeholder_Needs_and_Requirements_(glossary) | text | pending-extraction |
| System Requirement | SEBoK | sebokwiki.org/wiki/System_Requirement_(glossary) | text | pending-extraction |
| Mission | SEBoK | sebokwiki.org/wiki/Mission_(glossary) | text | pending-extraction |
| Capability | SEBoK | sebokwiki.org/wiki/Capability_(glossary) | text | pending-extraction |
| Solution | SEBoK | sebokwiki.org/wiki/Solution_(glossary) | text | pending-extraction |
| Measure of Effectiveness (MoE) | SEBoK | sebokwiki.org/wiki/Measure_of_Effectiveness_(glossary) | text | pending-extraction |
| Traceability | SEBoK | sebokwiki.org/wiki/Traceability_(glossary) | text | pending-extraction |
| Operational Concept | SEBoK | sebokwiki.org/wiki/Operational_Concept_(glossary) | text | pending-extraction |
| MBSE | SEBoK | sebokwiki.org/wiki/Model-Based_Systems_Engineering_(glossary) | text | pending-extraction |
| Risk | SEBoK | sebokwiki.org/wiki/Risk_(glossary) | text | pending-extraction |
| Logical Architecture | SEBoK | sebokwiki.org/wiki/Logical_Architecture_(glossary) | text | pending-extraction |
| Functional Architecture | SEBoK | sebokwiki.org/wiki/Functional_Architecture_(glossary) | text | pending-extraction |
| System Boundary | SEBoK | sebokwiki.org/wiki/System_Boundary_(glossary) | text | pending-extraction |
| Function | SEBoK | sebokwiki.org/wiki/Function_(glossary) | text | pending-extraction |
| System Definition | SEBoK | sebokwiki.org/wiki/System_Definition_(glossary) | text | pending-extraction |

## In-prose concepts — need the topic-page sources (capture pass, slice 10)

MGO (Mission/Goals/Objectives), Integrated Set of Needs, need-statement format, Stakeholder Register,
Approving Authority, Driver, Constraint, Solution Class — these come from the **Business or Mission
Analysis** and **Stakeholder Needs Definition** topic pages (wikitext), not the glossary; secure those
sources before encoding.
