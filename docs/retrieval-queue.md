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

- **Risk** — *now captured in full*: def (1)'s DAU-2003 measure sentence was recovered via pymupdf (two
  `pdftotext` space-drops at obvious word boundaries fixed — all words present), combined with the
  Conrow-2008 sentence. `definition_source = "DAU 2003; Conrow 2008"`.
- **MBSE** — SEBoK's glossary curates INCOSE's SE Vision 2020 definition (`INCOSE 2007`). A more
  authoritative primary source (INCOSE directly) may be sought later; SEBoK is the v0.1 boundary object.

## GtWR canon — one remaining hold

- **C1–C10, C12–C15** — *captured verbatim* (recovered from the summary sheet via pymupdf default-mode
  extraction; cited to GtWR, reproduction-licensed). **C11 (Consistent)** — `held`: the PDF text layer
  genuinely drops one word ("...a set of requirements is consistent if **[it]** contains..."; the `it`
  glyph exists elsewhere on the page but not here), so the full statement is not faithfully
  transcribable. C11's name is encoded; its `skos:definition` awaits a clean source-grab.
- **Integrated Set of Needs** — *available* in the GtWR summary (defined there verbatim); a good
  candidate to encode next, sourced from GtWR rather than the SEBoK topic pages.

## In-prose concepts — need the topic-page sources (capture pass, slice 10)

MGO (Mission/Goals/Objectives), Integrated Set of Needs, need-statement format, Stakeholder Register,
Approving Authority, Driver, Constraint, Solution Class — these come from the **Business or Mission
Analysis** and **Stakeholder Needs Definition** topic pages (wikitext), not the glossary; secure those
sources before encoding.
