# Third-party content licenses

`cds` materializes **verbatim definitions** from authoritative systems-engineering sources into its
RDF model layer (`ontology/concept-definition.ttl`). This file enumerates the sources whose text is
reproduced and their applicable license terms.

## The mixed-licensing map

The distribution carries two license regimes, and this file is the map between them:

- **The tooling** — Python source, SHACL shapes, CLI, the `cds:` vocabulary — is **Apache-2.0**
  (`LICENSE`).
- **The embedded verbatim canon** — the reproduced definitions materialized in
  `ontology/concept-definition.ttl` — **retains its upstream source license.** Two sources are
  reproduced verbatim: SEBoK (CC BY-NC-SA) and the INCOSE GtWR summary (reproduction-with-attribution).
  Their terms are recorded below.

Reproducing the canonical text is a deliberate engineering decision (the hallucination guard — see the
policy note at the end and `AGENTS.md`). Every reproduced definition is **fully cited** to its source;
`cds` does not claim to be an authoritative source, it acknowledges the canonical ones. The
authoritative, machine-readable enumeration of what is reproduced and from where lives in
`ontology/concept-definition.ttl` (`cds:cites` + `skos:definition`); the counts below are a snapshot
as of **v0.1.0**.

---

## SEBoK v2.14 — Guide to the Systems Engineering Body of Knowledge

**Publisher:** Systems Engineering Research Center (SERC) / Stevens Institute of Technology, for the
BKCASE project.
**Version:** v2.14
**URL:** https://sebokwiki.org/
**License:** Creative Commons Attribution–NonCommercial–ShareAlike 3.0 (CC BY-NC-SA 3.0)
**License URL:** https://creativecommons.org/licenses/by-nc-sa/3.0/
**SPDX id (as tracked in the model):** `CC-BY-NC-SA-3.0`

**Reproduced for:** verbatim glossary definitions for the **33** SEBoK-sourced terms in
`ontology/concept-definition.ttl` (v0.1.0). Each carries `cds:cites` to the registered SEBoK boundary
object and, where SEBoK records one, the upstream attribution SEBoK itself cites (`cds:definitionSource`
— see below).

**ShareAlike / NonCommercial note:** CC BY-NC-SA 3.0 carries **NonCommercial** and **ShareAlike**
terms. The reproduced SEBoK text remains under BY-NC-SA; it does **not** relicense under Apache-2.0.
The rendered View layer (`cds render` / `cds compile`) does **not** emit verbatim SEBoK text unless the
operator's configured `text_license` is BY-NC-SA-compatible (`sebok_renderable`); otherwise it cites the
source URL instead. Distribution obligations attach to the operator's chosen use, which `cds` tracks but
does not enforce.

**Attribution:** Definitions reproduced from the *Guide to the Systems Engineering Body of Knowledge*
(SEBoK), v2.14, © Stevens Institute of Technology / SERC, under CC BY-NC-SA 3.0.

---

## INCOSE GtWR v4 summary — Guide to Writing Requirements

**Publisher:** INCOSE (International Council on Systems Engineering)
**Document:** INCOSE-TP-2010-006-04 (Guide to Writing Requirements, v4 — summary)
**License (verbatim, from the summary's copyright information):**

> Given this is a summary of the Guide for Writing Requirements, permission to reproduce and use this
> summary is granted, with attribution to INCOSE and the original author(s) where practical, provided
> this copyright notice is included with all reproductions and derivative works.

Tracked in the model as `LicenseRef-INCOSE-GtWR-Summary` (self-describing, `cds:reproducible true`).

**Reproduced for** (in `ontology/concept-definition.ttl`, v0.1.0):

- the **14** GtWR well-formedness characteristic statements C1–C10 and C12–C15 (C11 is held pending a
  clean source copy — its concept is present, its definition is not); and
- **3** GtWR-native term definitions: `need`, `requirement`, `integrated-set-of-needs`.

**Attribution:** Reproduced from the *INCOSE Guide to Writing Requirements* (GtWR) v4 summary,
INCOSE-TP-2010-006-04, © INCOSE, with attribution under the summary's reproduction-with-attribution
terms. This copyright notice is included as those terms require.

---

## Upstream attributions preserved as provenance (not reproduced by `cds`)

Many SEBoK definitions record the source SEBoK *itself* drew them from. `cds` preserves that
attribution verbatim as metadata (`cds:definitionSource`) so the provenance chain is complete — but it
does **not** reproduce those upstream works' text. They are SEBoK's citations, carried through; **no
license obligation arises on `cds` from citation alone.** The authoritative list is the set of
`cds:definitionSource` values in `ontology/concept-definition.ttl`; as of v0.1.0 it includes:

ANSI/AIAA G-043-199 · ANSI/EIA 1998 · Ackoff 1971 · American Heritage Dictionary 2009 ·
Checkland 1999 · Conrow 2008 · "Created for SEBoK" · DAU 2003 · Dictionary.com 2012 · DoD 2009 ·
Flood and Carson 1993 · IEEE 1233-1998 (R2002) · IEEE 2005 · INCOSE 2007 (SE Vision 2020) ·
INCOSE GtWR 2023 · ISO/IEC/IEEE 15288:2023 · ISO/IEC/IEEE 2011 · ISO/IEC/IEEE 2015 · Pyster 2009 ·
Specking et al. 2018 · (modified from) Blanchard and Fabrycky 2011.

---

## Policy note on verbatim M-layer materialization

`cds` intentionally materializes verbatim definitions in the RDF model layer rather than storing only
citations. This is an engineering-fidelity decision: enforcing conformance with an engineering standard
without holding the standard's own words is a hallucination risk, so the software holds the
authoritative text to verify that rendered outputs reflect canon rather than model paraphrase. The
model layer is the enforcement substrate; the View layer is where the operator's distribution controls
apply (`text_license` gating). See `AGENTS.md` for the full rationale.

This policy has been reviewed with the Open-MBEE maintainers.
