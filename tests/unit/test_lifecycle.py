"""The top-level lifecycle model base class + its text/code license fields.

A system is modeled through its whole life cycle, which necessarily starts with Concept
Definition. The abstract base declares a ``text_license`` and a ``code_license`` (defaults
CC-BY-NC-SA / Apache-2.0). The View (slice 8) renders restricted canon — e.g. SEBoK
definitions — only when the model's ``text_license`` is **compatible with SEBoK**; the
**operator** chooses the license and is responsible for whether the use qualifies.
"""

from __future__ import annotations

from rdflib import RDF, RDFS, Literal, URIRef

from cds.core.model.lifecycle import (
    CodeLicense,
    LifecycleModel,
    TextLicense,
    lifecycle_to_graph,
    sebok_renderable,
)
from cds.core.namespaces import CDS, SPDX

_ID = "https://w3id.org/cds/scheme/concept-definition"


def _model(**over: object) -> LifecycleModel:
    base: dict[str, object] = dict(id=_ID, label="Concept Definition", stage="concept-definition")
    base.update(over)
    return LifecycleModel(**base)  # type: ignore[arg-type]


def test_defaults_are_cc_by_nc_sa_text_and_apache_code() -> None:
    m = _model()
    assert m.text_license == TextLicense.CC_BY_NC_SA
    assert m.code_license == CodeLicense.APACHE_2_0


def test_license_fields_are_extensible_with_a_custom_id() -> None:
    m = _model(text_license="MY-ORG-LICENSE-1.0")
    assert m.text_license == "MY-ORG-LICENSE-1.0"


def test_sebok_renders_only_for_a_sebok_compatible_text_license() -> None:
    assert sebok_renderable(TextLicense.CC_BY_NC_SA)  # default -> render allowed
    assert sebok_renderable("CC-BY-NC-SA-3.0")  # SEBoK's own version
    assert not sebok_renderable(TextLicense.CC_BY)  # permissive -> cite-only
    assert not sebok_renderable(CodeLicense.APACHE_2_0)  # not a compatible text license


def test_lifecycle_to_graph_emits_spdx_license_iris() -> None:
    g = lifecycle_to_graph(_model())
    s = URIRef(_ID)
    assert (s, RDF.type, CDS.LifecycleModel) in g
    assert (s, RDFS.label, Literal("Concept Definition")) in g
    assert (s, CDS.codeLicense, SPDX["Apache-2.0"]) in g
    assert (s, CDS.textLicense, SPDX["CC-BY-NC-SA-4.0"]) in g
