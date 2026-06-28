"""The SKOS reference-vocabulary Term — authored as YAML, emitted as grounded SKOS RDF.

A term is a ``skos:Concept`` in the Concept Definition scheme. Following the "ground
everything, no bare terms" ethos, every term carries at least one grounding edge (an
alignment to an existing concept) and cites the boundary object(s) its definition came from.

Text in the model, citation in the view (the standards-in-code resolution):

* **M (RDF triples) — the verbatim text is materialized and committed.** The software must hold
  the standards to enforce them, and the verbatim is the **hallucination guard** (the work checks
  the authoritative text, never LLM memory). ``term_to_graph`` emits ``skos:definition`` when
  present. It is **not** gitignored and **not** stripped from the committed RDF.
* **V (compilers / views, slice 8) — the text is excluded; views cite the authoritative source.**
  Human-consumable outputs emit the citation (e.g. the sebokwiki URL), not our local copy.
  Non-distribution is enforced at the view layer — RDF triples are not human-consumable — not by
  withholding text from the model. (Engineering enforcement supersedes the licensing-bureaucracy
  layer; the View is simply restricted from emitting the held copy.)
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel
from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.namespaces import CDS, CDS_TERM, SKOS


class GroundingRelation(StrEnum):
    """The alignment predicate, chosen by tightest-correct semantic fit."""

    SUBCLASS_OF = "subclass-of"
    EXACT_MATCH = "exact-match"
    CLOSE_MATCH = "close-match"
    BROAD_MATCH = "broad-match"
    NARROW_MATCH = "narrow-match"
    RELATED_MATCH = "related-match"  # fuzzy / associative


_GROUNDING_PREDICATE: dict[GroundingRelation, URIRef] = {
    GroundingRelation.SUBCLASS_OF: RDFS.subClassOf,
    GroundingRelation.EXACT_MATCH: SKOS.exactMatch,
    GroundingRelation.CLOSE_MATCH: SKOS.closeMatch,
    GroundingRelation.BROAD_MATCH: SKOS.broadMatch,
    GroundingRelation.NARROW_MATCH: SKOS.narrowMatch,
    GroundingRelation.RELATED_MATCH: SKOS.relatedMatch,
}


class Grounding(BaseModel):
    """An alignment of our concept to an existing one (the grounding edge)."""

    relation: GroundingRelation
    target: str


class Term(BaseModel):
    """A Concept Definition vocabulary term (a ``skos:Concept``)."""

    slug: str
    pref_label: str
    alt_labels: list[str] = []
    definition: str | None = None
    grounding: list[Grounding] = []
    cites: list[str] = []
    broader: list[str] = []
    sysml_construct: str | None = None
    nrm_note: str | None = None


def term_iri(slug: str) -> URIRef:
    """The IRI of a term concept."""
    return CDS_TERM[slug]


def load_term(source: str | Path) -> Term:
    """Load a term from a YAML string or file path."""
    text = Path(source).read_text() if isinstance(source, Path) else source
    return Term.model_validate(yaml.safe_load(text))


def term_to_graph(term: Term, *, scheme: URIRef) -> Graph:
    """Emit a term as a grounded ``skos:Concept`` in ``scheme``."""
    g = Graph()
    s = term_iri(term.slug)
    g.add((s, RDF.type, CDS.Term))  # cds:Term rdfs:subClassOf skos:Concept (the SHACL target)
    g.add((s, RDF.type, SKOS.Concept))
    g.add((s, SKOS.inScheme, scheme))
    g.add((s, SKOS.prefLabel, Literal(term.pref_label)))
    for alt in term.alt_labels:
        g.add((s, SKOS.altLabel, Literal(alt)))
    if term.definition is not None:
        g.add((s, SKOS.definition, Literal(term.definition)))
    for grounding in term.grounding:
        g.add((s, _GROUNDING_PREDICATE[grounding.relation], URIRef(grounding.target)))
    for cite in term.cites:
        g.add((s, CDS.cites, URIRef(cite)))
    for broader in term.broader:
        g.add((s, SKOS.broader, term_iri(broader)))
    if term.sysml_construct is not None:
        g.add((s, CDS.sysmlConstruct, URIRef(term.sysml_construct)))
    if term.nrm_note is not None:
        g.add((s, CDS.nrmCanon, Literal(term.nrm_note)))
    return g
