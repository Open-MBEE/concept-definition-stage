# Retrieval queue (human-retrieval escalation — local fallback)

The agent **never fabricates canon**. When required canonical content is not yet secured, it is escalated to
a human here (and/or as a `retrieval` GitHub issue once the remote exists). The dependent term is **held out
of the build** until the artifact is provided and verified.

- **text** → wiki source grab (paste verbatim `{{...}}` wikitext) → `terms/<slug>.src.wiki`
- **image/figure** → screenshot → content-addressed snapshot in `sources/` (`sourceType=image`) + caption

**Status:** `pending` → `provided` → `verified`. A term builds only when `verified`.

**Built (verified, in `concept-definition.ttl`) — all 25 glossary terms.** Each carries a verbatim
SEBoK v2.14 glossary definition (several spot-checked byte-identical to the held PDF), its upstream
attribution (`cds:definitionSource`), a citation, and a grounding edge. Notes on two:

- **Risk** — encoded the clean Conrow-2008 sentence of def (1) (it parallels Problem/Threat/
  Opportunity); the DAU-2003 measure sentence is omitted (pdftotext-corrupted, not transcribable).
- **MBSE** — SEBoK's glossary curates INCOSE's SE Vision 2020 definition (`INCOSE 2007`). A more
  authoritative primary source (INCOSE directly) may be sought later; SEBoK is the v0.1 boundary object.

## GtWR canon — partial holds

- **C1–C9** — *captured verbatim* (recovered from the summary sheet by word-position de-columning with
  pymupdf; cited to GtWR, reproduction-licensed). **C10–C15** — `held — needs clean source`: the
  set-level characteristics column has PDF text-layer drops (missing function words, e.g.
  "requirements for entity", "requirements consistent if contains") that cannot be faithfully
  transcribed. Names are encoded; the `skos:definition`s await a clean source-grab.
- **Integrated Set of Needs** — *available* in the GtWR summary (defined there verbatim); a good
  candidate to encode next, sourced from GtWR rather than the SEBoK topic pages.

## In-prose concepts — need the topic-page sources (capture pass, slice 10)

MGO (Mission/Goals/Objectives), Integrated Set of Needs, need-statement format, Stakeholder Register,
Approving Authority, Driver, Constraint, Solution Class — these come from the **Business or Mission
Analysis** and **Stakeholder Needs Definition** topic pages (wikitext), not the glossary; secure those
sources before encoding.
