# Third-party content licenses

`cds` materializes verbatim definitions from authoritative systems engineering sources in its
RDF model layer (`ontology/concept-definition.ttl`). This file enumerates those sources and
their applicable license terms.

The tooling (Python source, SHACL shapes, CLI) is Apache-2.0. Only the verbatim definitions
in the M layer are subject to the source licenses below.

---

## SEBoK v2.14 — Systems Engineering Body of Knowledge

**Publisher:** SERC (Systems Engineering Research Center) / Stevens Institute of Technology  
**Version:** v2.14  
**URL:** https://sebokwiki.org/  
**License:** Creative Commons Attribution–NonCommercial–ShareAlike 4.0 International (CC BY-NC-SA 4.0)  
**License URL:** https://creativecommons.org/licenses/by-nc-sa/4.0/

**Used for:** Verbatim glossary definitions for the 25 SEBoK-sourced terms in
`ontology/concept-definition.ttl`. These definitions are materialized in the M layer as a
hallucination guard (see `AGENTS.md`). Rendered outputs (`views/`) do not reproduce verbatim
SEBoK text unless the operator's `text_license` is CC BY-NC-SA compatible; the default
rendering cites the source URL instead.

**Attribution:** Definitions reproduced from the *Systems Engineering Body of Knowledge*
(SEBoK), v2.14, published by SERC under CC BY-NC-SA 4.0.

---

## INCOSE GtWR v4 — Guide to the Roadmap (Characteristic Statements)

**Publisher:** INCOSE (International Council on Systems Engineering)  
**Version:** v4 summary  
**License:** INCOSE custom license — reproduction with attribution permitted for
non-commercial educational and research use. Contact INCOSE for commercial use.

**Used for:** The 14 verified GtWR characteristic-statement definitions (C1–C10, C12–C15)
in `ontology/concept-definition.ttl`. C11 is currently held pending a clean source copy.

**Attribution:** Characteristic statements reproduced from the *INCOSE Guide to the Roadmap*
(GtWR), v4, © INCOSE. Used with attribution under INCOSE's educational use terms.

---

## Referenced standards (not reproduced verbatim)

The following standards are cited as `cds:definitionSource` for individual terms. Their text
is **not reproduced** in the M layer; only the attribution metadata is recorded. No license
compliance obligation arises from citation alone.

| Source | Publisher |
|--------|-----------|
| ANSI/AIAA G-043-199 | AIAA |
| ANSI/EIA 1998 | EIA |
| ISO/IEC/IEEE 15288:2023 | ISO / IEC / IEEE |
| ISO/IEC/IEEE 2011 | ISO / IEC / IEEE |
| ISO/IEC/IEEE 2015 | ISO / IEC / IEEE |
| IEEE 1233-1998 (R2002) | IEEE |
| IEEE 2005 | IEEE |
| INCOSE 2007 (SE Vision 2020) | INCOSE |
| DoD 2009 | U.S. Department of Defense |
| DAU 2003 | Defense Acquisition University |

---

## Policy note on verbatim M-layer materialization

`cds` intentionally materializes verbatim definitions in the RDF M layer rather than storing
only citations. This is an engineering enforcement decision: the software holds the authoritative
text so it can verify that rendered outputs faithfully reflect canon, not LLM-generated
paraphrase. RDF triples are not human-consumable publication; the V layer is where distribution
controls apply. See `AGENTS.md` for the full rationale.

This policy has been reviewed with the Open-MBEE maintainers.
