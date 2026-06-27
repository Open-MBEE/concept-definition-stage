"""The top-level abstract base for modeling a system through its whole life cycle.

A lifecycle model **necessarily starts with the Concept Definition stage**; later stages
(System Definition, …) specialize the same base. The base declares two licenses:

* ``code_license`` — the license of our code/structure (default ``Apache-2.0``).
* ``text_license`` — the license the rendered *text* outputs operate under (default
  ``CC-BY-NC-SA-4.0``).

License-keyed View override (consumed by the View, slice 8): the View renders restricted canon
(e.g. SEBoK definitions, which are CC-BY-NC-SA) only when ``text_license`` is **compatible with
SEBoK**; otherwise it cites the authoritative source. Any report rendered with restricted canon
inherits that text license (ShareAlike). The **operator**, not the tool, chooses the licenses
and is responsible for whether the circumstances qualify.

``TextLicense`` / ``CodeLicense`` enumerate common licenses (SPDX ids) for convenience and
defaults; the fields accept **any** id (SPDX or custom), so the set is user-extensible.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel
from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.namespaces import CDS, SPDX


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
# license (the BY-NC-SA family, where ShareAlike is satisfied). Other sources/compatibilities
# are a later refinement; for now we simply gate on SEBoK compatibility.
_SEBOK_COMPATIBLE: frozenset[str] = frozenset(
    {TextLicense.CC_BY_NC_SA.value, TextLicense.CC_BY_NC_SA_3.value}
)


def sebok_renderable(text_license: str) -> bool:
    """Whether SEBoK (CC-BY-NC-SA) text may be rendered under ``text_license``."""
    return text_license in _SEBOK_COMPATIBLE


def license_iri(license_id: str) -> URIRef:
    """Ground a license id to an IRI (SPDX for known ids; the id itself if already a URL)."""
    return URIRef(license_id) if license_id.startswith("http") else SPDX[license_id]


class LifecycleModel(BaseModel):
    """A model of a system across its life cycle (abstract base; stages specialize it)."""

    id: str
    label: str
    stage: str
    code_license: str = CodeLicense.APACHE_2_0
    text_license: str = TextLicense.CC_BY_NC_SA


def lifecycle_to_graph(model: LifecycleModel) -> Graph:
    """Emit the lifecycle model resource (typed, labelled, with its licenses as SPDX IRIs)."""
    g = Graph()
    s = URIRef(model.id)
    g.add((s, RDF.type, CDS.LifecycleModel))
    g.add((s, RDFS.label, Literal(model.label)))
    g.add((s, CDS.stage, Literal(model.stage)))
    g.add((s, CDS.codeLicense, license_iri(model.code_license)))
    g.add((s, CDS.textLicense, license_iri(model.text_license)))
    return g
