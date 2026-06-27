"""Controlled vocabularies (the ASoT enums) grounded as SKOS concepts.

The "ground everything, no bare terms" ethos applies to our own control vocab too:
``authorityKind`` / ``sourceType`` / ``captureTier`` / ``retrievalStatus`` are SKOS concepts
in named schemes (emitted into ``cds-core.ttl``), never string literals.
"""

from __future__ import annotations

from enum import StrEnum

from rdflib import RDF, Graph, Literal, URIRef

from cds.core.asot.models import (
    AuthorityKind,
    CaptureTier,
    RetrievalStatus,
    SourceType,
    VerificationMethod,
)
from cds.core.model.lifecycle import IpStatus
from cds.core.namespaces import CDS, SKOS

_SCHEMES: tuple[type[StrEnum], ...] = (
    AuthorityKind,
    SourceType,
    CaptureTier,
    RetrievalStatus,
    VerificationMethod,
    IpStatus,
)


def scheme_iri(enum_cls: type[StrEnum]) -> URIRef:
    """The ``skos:ConceptScheme`` IRI for a controlled vocabulary."""
    return CDS[enum_cls.__name__]


def controlled_concept(member: StrEnum) -> URIRef:
    """The ``skos:Concept`` IRI for one controlled-vocabulary value."""
    return CDS[f"{type(member).__name__}/{member.value}"]


def controlled_vocab_graph() -> Graph:
    """Emit every controlled vocabulary as a SKOS concept scheme (for ``cds-core.ttl``)."""
    g = Graph()
    g.bind("cds", CDS)
    g.bind("skos", SKOS)
    for enum_cls in _SCHEMES:
        scheme = scheme_iri(enum_cls)
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        for member in enum_cls:
            concept = controlled_concept(member)
            g.add((concept, RDF.type, SKOS.Concept))
            g.add((concept, SKOS.inScheme, scheme))
            g.add((concept, SKOS.prefLabel, Literal(member.value)))
    return g
