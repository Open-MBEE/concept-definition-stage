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

## In-prose concepts (slice 10 capture pass)

**From the Business or Mission Analysis page (provided by the operator; verbatim confirmed in the held
PDF, cited to SEBOK_SOURCE):**
- *Captured:* **Goal**, **Objective**, **Solution Class** — article concepts with no glossary entry,
  grounded by `relatedMatch` (to Mission / Mission / Solution) and waived in `ontology/waivers.ttl`
  (no tighter SEBoK target exists). MGO = Mission (glossary) + Goal + Objective.
- *Held:* **Stakeholder Register** — SEBoK describes it mid-prose ("...captured in a stakeholder
  register, noting each stakeholder and their involvement...") but gives no clean definition sentence;
  encoding it would require paraphrase. Hold until a crisp source.
- Also available here but already done elsewhere: Operational Concept, Measure of Effectiveness, Mission,
  problem/threat/opportunity (glossary); as-is/to-be & green-/brown-field (v0.2 perspective primitives).

**Driver, Constraint** — *captured* from their SEBoK glossary entries (exact-match grounding).

**From the Stakeholder Needs Definition page (full, captured):** **Approving Authority**, **Stakeholder
Register**, and **Need Statement** (the need-statement format — "The stakeholders need the system to",
no "shall") — all verbatim-confirmed in the held PDF, cited to SEBOK_SOURCE, grounded by relatedMatch
(to Stakeholder / Stakeholder / Need) and waived. Both Concept Definition topic pages are now captured.

Deferred by design: SEBoK Table 2 example need statements (ID/Name/Need/Rationale/Source) = the v0.2
conformance fixture; as-is/to-be & green-/brown-field = v0.2 perspective primitives.
