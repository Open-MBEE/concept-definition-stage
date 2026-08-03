"""License designations (SPDX) — a cross-cutting concern for the lifecycle model and for any
externally-referenced asset in the ASoT model.

We **track** licenses for auditability; we do **not** enforce compliance. The operator of the
tool, not the tool, is responsible for determining whether their use of a source complies with
its tracked license. ``TextLicense`` / ``CodeLicense`` enumerate common ids for convenience and
defaults; any SPDX id (or a custom id / URL) is accepted, so the set is user-extensible.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel
from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.namespaces import CDS, CDS_LICENSE, DCTERMS, SPDX


class TextLicense(StrEnum):
    """Common content/text licenses (SPDX ids). Extensible — any id is accepted."""

    CC_BY_NC_SA = "CC-BY-NC-SA-4.0"
    CC_BY_NC_SA_3 = "CC-BY-NC-SA-3.0"
    CC_BY_SA = "CC-BY-SA-4.0"
    CC_BY = "CC-BY-4.0"
    CC0 = "CC0-1.0"


class CodeLicense(StrEnum):
    """Common code licenses (SPDX ids). Extensible — any id is accepted."""

    APACHE_2_0 = "Apache-2.0"
    MIT = "MIT"
    BSD_3 = "BSD-3-Clause"
    MPL_2_0 = "MPL-2.0"
    EPL_2_0 = "EPL-2.0"
    GPL_3_0 = "GPL-3.0-only"


# SEBoK is CC-BY-NC-SA; rendering its text is permitted only into a SEBoK-compatible text
# license (the BY-NC-SA family, where ShareAlike is satisfied). Other source/license
# compatibilities are a later refinement; for now we simply gate on SEBoK compatibility.
_SEBOK_COMPATIBLE: frozenset[str] = frozenset(
    {TextLicense.CC_BY_NC_SA.value, TextLicense.CC_BY_NC_SA_3.value}
)


def sebok_renderable(text_license: str) -> bool:
    """Whether SEBoK (CC-BY-NC-SA) text may be rendered under ``text_license``."""
    return text_license in _SEBOK_COMPATIBLE


# DRAFT wording, pending the maintainer's legal review (live-QA 2026-08-02, D3a).
# Guiding principle (D4): the license friction stays, the dead-end goes. Taking this
# attestation is one explicit act of responsibility; the tool then propagates the
# BY-NC-SA license into everything the verbatim touches so the user abides by
# construction (D3b handles ShareAlike; this statement handles NonCommercial).
NONCOMMERCIAL_ATTESTATION_STATEMENT = (
    "I attest that this use of SEBoK content is noncommercial (for example, educational "
    "use such as an accredited student design project), and I take responsibility for "
    "that determination. I understand the output embeds SEBoK text and is licensed "
    "CC BY-NC-SA, with attribution preserved."
)


class Attestation(BaseModel):
    """A recorded noncommercial-use assertion (D3a) — a legal act, audited like an
    approver decision: who took responsibility, and in what context.

    Clears only the NonCommercial prong; ShareAlike is cleared by license propagation
    (the rendering that honors an attestation carries CC BY-NC-SA at rest).
    """

    attester: str  # who takes responsibility (IRI or name)
    context: str = ""  # e.g. "ABET senior design project"
    statement: str = NONCOMMERCIAL_ATTESTATION_STATEMENT


def license_iri(license_id: str) -> URIRef:
    """Ground a license id to an IRI.

    A full URL is used as-is; an SPDX ``LicenseRef-…`` (custom/document-local) license grounds to
    our ``cds/license/`` namespace; any other id is treated as a standard SPDX id (spdx.org).
    """
    if license_id.startswith("http"):
        return URIRef(license_id)
    if license_id.startswith("LicenseRef-"):
        return CDS_LICENSE[license_id]
    return SPDX[license_id]


class CustomLicense(BaseModel):
    """A document-local custom license (SPDX ``LicenseRef-…``) with its verbatim terms.

    ``reproducible`` records whether the terms permit reproduction/redistribution — which the
    View consults (independently of SEBoK compatibility). We track; the operator judges.
    """

    ref: str
    name: str
    text: str
    reproducible: bool
    source: str | None = None


# The INCOSE GtWR v4 summary grants reproduction with attribution — so its terms (and the summary
# itself) are reproducible. Verbatim from the summary's COPYRIGHT INFORMATION (held PDF).
GTWR_LICENSE = CustomLicense(
    ref="LicenseRef-INCOSE-GtWR-Summary",
    name="INCOSE Guide to Writing Requirements v4 Summary — reproduction with attribution",
    text=(
        "Given this is a summary of the Guide for Writing Requirements, permission to reproduce "
        "and use this summary is granted, with attribution to INCOSE and the original author(s) "
        "where practical, provided this copyright notice is included with all reproductions and "
        "derivative works."
    ),
    reproducible=True,
    source="INCOSE-TP-2010-006-04",
)


def custom_license_graph(lic: CustomLicense) -> Graph:
    """Emit a self-describing definition of a custom license."""
    g = Graph()
    s = license_iri(lic.ref)
    g.add((s, RDF.type, DCTERMS.LicenseDocument))
    g.add((s, RDFS.label, Literal(lic.name)))
    g.add((s, CDS.licenseText, Literal(lic.text)))
    g.add((s, CDS.reproducible, Literal(lic.reproducible)))
    if lic.source is not None:
        g.add((s, DCTERMS.source, Literal(lic.source)))
    return g
