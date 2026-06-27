"""License IRI routing + custom (SPDX LicenseRef-) license references."""

from __future__ import annotations

from rdflib import RDF, RDFS, Literal, URIRef

from cds.core.licenses import GTWR_LICENSE, CustomLicense, custom_license_graph, license_iri
from cds.core.namespaces import CDS, CDS_LICENSE, DCTERMS, SPDX


def test_license_iri_routes_spdx_custom_and_url() -> None:
    ref = "LicenseRef-INCOSE-GtWR-Summary"
    assert license_iri("Apache-2.0") == SPDX["Apache-2.0"]  # standard SPDX -> spdx.org
    assert license_iri(ref) == CDS_LICENSE[ref]  # custom LicenseRef -> cds/license/
    assert license_iri("https://example.org/lic") == URIRef("https://example.org/lic")  # a URL


def test_gtwr_is_a_custom_reproducible_with_attribution_license() -> None:
    assert isinstance(GTWR_LICENSE, CustomLicense)
    assert GTWR_LICENSE.ref.startswith("LicenseRef-")
    assert GTWR_LICENSE.reproducible is True
    assert "attribution" in GTWR_LICENSE.text.lower()


def test_custom_license_graph_emits_a_self_describing_definition() -> None:
    g = custom_license_graph(GTWR_LICENSE)
    s = license_iri(GTWR_LICENSE.ref)
    assert (s, RDF.type, DCTERMS.LicenseDocument) in g
    assert (s, RDFS.label, Literal(GTWR_LICENSE.name)) in g
    assert (s, CDS.licenseText, Literal(GTWR_LICENSE.text)) in g
    assert (s, CDS.reproducible, Literal(True)) in g
