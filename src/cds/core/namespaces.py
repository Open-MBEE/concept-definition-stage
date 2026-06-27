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
# Bound as ``sysml``. The exact authoritative URI is a TODO — see ISSUES.md
# (namespace alignment), resolved when the openCAESAR SysML v2 OWL cache is generated.
SYSML = Namespace("https://www.omg.org/spec/SysML/#")
