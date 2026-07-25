"""Side-ledger constructs — the parking-lot and the retrieval queue.

These are *tool* constructs, not concept-definition instances, so they live outside the
``cds:Synthesis`` integrated set (they carry no ``cds:Instance`` marker):

* **ParkedItem** — an out-of-scope / roadmap idea captured so a tangent doesn't derail the session
  and isn't lost. (Directly answers the pilot's rapid, non-linear ideation.)
* **RetrievalItem** — an open unknown to be *tracked, not answered*: a question with a
  ``pending → provided → verified`` status, honoring the "no fabricated canon" rule.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel
from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.namespaces import CDS, DCTERMS


class RetrievalStatus(StrEnum):
    """The construction-order state of an open retrieval."""

    PENDING = "pending"
    PROVIDED = "provided"
    VERIFIED = "verified"


class ParkedItem(BaseModel):
    """A parked, out-of-scope idea (roadmap material)."""

    slug: str
    label: str
    description: str = ""
    note: str | None = None
    related_to: str | None = None  # optional IRI of a related record/synthesis


class RetrievalItem(BaseModel):
    """An open unknown tracked through ``pending → provided → verified``."""

    slug: str
    question: str
    status: RetrievalStatus = RetrievalStatus.PENDING
    locator: str | None = None  # where the answer was found, once provided
    description: str = ""


class Tension(BaseModel):
    """A named conflict between records (surfaced, not hidden) — e.g. two needs that pull apart."""

    slug: str
    label: str
    description: str = ""
    between: list[str] = []  # IRIs of the records in tension


def parked_iri(base: str, slug: str) -> URIRef:
    return URIRef(f"{base}parked/{slug}")


def queue_iri(base: str, slug: str) -> URIRef:
    return URIRef(f"{base}queue/{slug}")


def tension_iri(base: str, slug: str) -> URIRef:
    return URIRef(f"{base}tension/{slug}")


def parked_to_graph(item: ParkedItem, *, base: str) -> Graph:
    g = Graph()
    s = parked_iri(base, item.slug)
    g.add((s, RDF.type, CDS.ParkedItem))
    g.add((s, RDFS.label, Literal(item.label)))
    if item.description:
        g.add((s, DCTERMS.description, Literal(item.description)))
    if item.note:
        g.add((s, CDS.parkNote, Literal(item.note)))
    if item.related_to:
        g.add((s, CDS.relatedTo, URIRef(item.related_to)))
    return g


def queue_to_graph(item: RetrievalItem, *, base: str) -> Graph:
    g = Graph()
    s = queue_iri(base, item.slug)
    g.add((s, RDF.type, CDS.RetrievalItem))
    g.add((s, RDFS.label, Literal(item.question)))
    g.add((s, CDS.retrievalStatus, Literal(item.status.value)))
    if item.description:
        g.add((s, DCTERMS.description, Literal(item.description)))
    if item.locator:
        g.add((s, CDS.locator, Literal(item.locator)))
    return g


def tension_to_graph(item: Tension, *, base: str) -> Graph:
    g = Graph()
    s = tension_iri(base, item.slug)
    g.add((s, RDF.type, CDS.Tension))
    g.add((s, RDFS.label, Literal(item.label)))
    if item.description:
        g.add((s, DCTERMS.description, Literal(item.description)))
    for iri in sorted(item.between):
        g.add((s, CDS.between, URIRef(iri)))
    return g
