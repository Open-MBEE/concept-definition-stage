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

from pydantic import BaseModel
from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.licenses import CodeLicense, TextLicense, license_iri
from cds.core.namespaces import CDS

__all__ = [
    "CodeLicense",
    "LifecycleModel",
    "TextLicense",
    "license_iri",
    "lifecycle_to_graph",
]


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
