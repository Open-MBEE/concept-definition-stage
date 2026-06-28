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

import yaml
from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef

from cds import __version__
from cds.core.anchors.sysml import sysml_anchor_graph
from cds.core.asot.models import Source
from cds.core.asot.rdf import to_graph as asot_to_graph
from cds.core.model.term import Term, load_term, term_to_graph
from cds.core.namespaces import CDS, CDS_TERM, DCTERMS, OMG_SYSML, PROV, SKOS, SPDX, SYSML
from cds.core.serialize import canonical_turtle
from cds.stages.concept_definition.seed import GTWR_SOURCE, seed_authorities, seed_sources

SCHEME = URIRef("https://w3id.org/cds/scheme/concept-definition")
CHARACTERISTICS_SCHEME = URIRef("https://w3id.org/cds/scheme/need-characteristics")
TERMS_DIR = Path(__file__).resolve().parent / "terms"
OUTPUT_TTL = Path(__file__).resolve().parents[4] / "ontology" / "concept-definition.ttl"

CHARACTERISTICS_FILE = Path(__file__).resolve().parent / "characteristics.yaml"

_PREFIXES: dict[str, str] = {
    "cds": str(CDS),
    "cdsterm": str(CDS_TERM),
    "dcterms": str(DCTERMS),
    "owl": str(OWL),
    "prov": str(PROV),
    "omg-sysml": str(OMG_SYSML),
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "skos": str(SKOS),
    "spdx": str(SPDX),
    "sysml": str(SYSML),
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


def characteristics_graph() -> Graph:
    """The GtWR C1–C15 companion vocab (SKOS scheme cited to GtWR); C1–C9 verbatim, C10–C15 held."""
    g = Graph()
    gtwr = URIRef(GTWR_SOURCE.id)
    label = Literal("GtWR well-formedness characteristics (C1-C15)")
    g.add((CHARACTERISTICS_SCHEME, RDF.type, SKOS.ConceptScheme))
    g.add((CHARACTERISTICS_SCHEME, RDFS.label, label))
    g.add((CHARACTERISTICS_SCHEME, PROV.wasDerivedFrom, gtwr))
    for entry in yaml.safe_load(CHARACTERISTICS_FILE.read_text()):
        s = URIRef(f"https://w3id.org/cds/characteristic/{entry['notation']}")
        g.add((s, RDF.type, SKOS.Concept))
        g.add((s, SKOS.inScheme, CHARACTERISTICS_SCHEME))
        g.add((s, SKOS.notation, Literal(entry["notation"])))
        g.add((s, SKOS.prefLabel, Literal(entry["name"])))
        if entry.get("definition") is not None:  # C1–C9 verbatim; C10–C15 held (names only)
            g.add((s, SKOS.definition, Literal(entry["definition"])))
        g.add((s, CDS.cites, gtwr))
    return g


def build_concept_definition_graph() -> Graph:
    """Assemble the full scheme graph: boundary objects + scheme node + grounded terms."""
    authorities = seed_authorities()
    sources = seed_sources()
    g = asot_to_graph(authorities=authorities, sources=sources)
    g += scheme_graph(sources)
    for term in load_terms():
        g += term_to_graph(term, scheme=SCHEME)
    g += characteristics_graph()  # the GtWR C1-C15 companion vocab
    g += sysml_anchor_graph(g)  # equivalence axioms for the invoked SysML constructs
    return g


def write_concept_definition_ttl(graph: Graph | None = None) -> Path:
    """Write the deterministic ``ontology/concept-definition.ttl`` artifact; returns its path."""
    g = graph if graph is not None else build_concept_definition_graph()
    OUTPUT_TTL.write_text(canonical_turtle(g, prefixes=_PREFIXES))
    return OUTPUT_TTL
