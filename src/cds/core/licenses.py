"""License designations (SPDX) — a cross-cutting concern for the lifecycle model and for any
externally-referenced asset in the ASoT model.

We **track** licenses for auditability; we do **not** enforce compliance. The operator of the
tool, not the tool, is responsible for determining whether their use of a source complies with
its tracked license. ``TextLicense`` / ``CodeLicense`` enumerate common ids for convenience and
defaults; any SPDX id (or a custom id / URL) is accepted, so the set is user-extensible.
"""

from __future__ import annotations

from enum import StrEnum

from rdflib import URIRef

from cds.core.namespaces import SPDX


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


def license_iri(license_id: str) -> URIRef:
    """Ground a license id to an IRI (SPDX for known ids; the id itself if already a URL)."""
    return URIRef(license_id) if license_id.startswith("http") else SPDX[license_id]
