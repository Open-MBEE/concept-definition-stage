"""RDF namespaces used across cds.

The ``cds:`` core lives at ``https://w3id.org/cds#`` (w3id registration is a non-blocking
TODO). Everything else is reused W3C / OMG vocabulary.
"""

from __future__ import annotations

from rdflib import Namespace

CDS = Namespace("https://w3id.org/cds#")  # vocabulary / classes / properties (hash)
CDS_TERM = Namespace("https://w3id.org/cds/term/")  # individual concepts (slash)
PROV = Namespace("http://www.w3.org/ns/prov#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
SEBOK = Namespace("https://sebokwiki.org/wiki/")
SPDX = Namespace("https://spdx.org/licenses/")  # ground licenses to the SPDX registry
CDS_LICENSE = Namespace("https://w3id.org/cds/license/")  # custom (SPDX LicenseRef-) licenses
CDS_WAIVER = Namespace("https://w3id.org/cds/waiver/")  # first-class SHACL waivers (audit data)
# SysML v2: a local namespace for the constructs we use, aliased to the OMG SysML v2 OWL rendering
# via owl:equivalentClass/Property axioms (no vendored OWL cache; the established DSG pattern).
SYSML = Namespace("https://www.omg.org/spec/SysML/2.0/")  # local terms
OMG_SYSML = Namespace("http://www.omg.org/spec/SysML/20240501/")  # OMG OWL rendering (alias target)
