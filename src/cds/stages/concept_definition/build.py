"""Build the Concept Definition scheme: YAML term sources -> canonical SKOS+PROV Turtle.

The output ``ontology/concept-definition.ttl`` is a deterministic, committed artifact — a
``skos:ConceptScheme`` (a *provenance-tracked reference vocabulary*; ``cds:Synthesis`` is reserved
for v0.2) whose terms each carry a verbatim SEBoK definition, a citation to the verified boundary
object it came from, and a grounding edge to the SEBoK concept. The scheme ``prov:wasDerivedFrom``
its registered sources, seeding the faithful-capture audit.

The verbatim definitions are materialized here in the committed M (the hallucination guard); the
View (slice 8) excludes them and cites the source unless the operator's text license permits it.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef

from cds import __version__
from cds.core.asot.models import Source
from cds.core.asot.rdf import to_graph as asot_to_graph
from cds.core.model.term import Term, load_term, term_to_graph
from cds.core.namespaces import CDS, CDS_TERM, DCTERMS, PROV, SKOS, SPDX
from cds.core.serialize import canonical_turtle
from cds.stages.concept_definition.seed import seed_authorities, seed_sources

SCHEME = URIRef("https://w3id.org/cds/scheme/concept-definition")
TERMS_DIR = Path(__file__).resolve().parent / "terms"
OUTPUT_TTL = Path(__file__).resolve().parents[4] / "ontology" / "concept-definition.ttl"

_PREFIXES: dict[str, str] = {
    "cds": str(CDS),
    "cdsterm": str(CDS_TERM),
    "dcterms": str(DCTERMS),
    "owl": str(OWL),
    "prov": str(PROV),
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "skos": str(SKOS),
    "spdx": str(SPDX),
    # NB: no `sebok` prefix — the glossary URLs contain "(glossary)", which is not a parse-safe
    # Turtle local name, so they are emitted as full IRIs by the serializer.
}


def load_terms(terms_dir: Path = TERMS_DIR) -> list[Term]:
    """Load every YAML term source in ``terms_dir`` (sorted, for determinism)."""
    return [load_term(path) for path in sorted(terms_dir.glob("*.yaml"))]


def scheme_graph(sources: list[Source]) -> Graph:
    """The scheme node: a provenance-tracked ``skos:ConceptScheme`` derived from its sources."""
    g = Graph()
    g.add((SCHEME, RDF.type, SKOS.ConceptScheme))
    g.add((SCHEME, RDFS.label, Literal("Concept Definition Vocabulary")))
    g.add((SCHEME, DCTERMS.title, Literal("SEBoK Concept Definition reference vocabulary")))
    g.add((SCHEME, OWL.versionInfo, Literal(__version__)))
    for src in sources:
        g.add((SCHEME, PROV.wasDerivedFrom, URIRef(src.id)))
    return g


def build_concept_definition_graph() -> Graph:
    """Assemble the full scheme graph: boundary objects + scheme node + grounded terms."""
    authorities = seed_authorities()
    sources = seed_sources()
    g = asot_to_graph(authorities=authorities, sources=sources)
    g += scheme_graph(sources)
    for term in load_terms():
        g += term_to_graph(term, scheme=SCHEME)
    return g


def write_concept_definition_ttl(graph: Graph | None = None) -> Path:
    """Write the deterministic ``ontology/concept-definition.ttl`` artifact; returns its path."""
    g = graph if graph is not None else build_concept_definition_graph()
    OUTPUT_TTL.write_text(canonical_turtle(g, prefixes=_PREFIXES))
    return OUTPUT_TTL
