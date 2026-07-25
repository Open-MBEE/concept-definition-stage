"""Project-instance models — a user's *actual* concept-definition mapping (not the vocabulary).

The vocabulary (36 ``cds:Term`` concepts) is the *type system*; here a user authors **instances** of
it — their specific mission, goals, stakeholders, needs — collected under a ``cds:Synthesis``
(the mapping / integrated set). Per the chosen design, each record is **typed by the matching
vocabulary Term** (SKOS/OWL punning: the concept doubles as the instance's class) plus a
``cds:Instance`` marker so shapes can target every instance uniformly. A shared :class:`Record` base
carries label/description/provenance/membership; thin subclasses add the few kind-specific links.

Serialization is deterministic (sorted multivalues) and blank-node-free, so
:func:`cds.core.serialize.canonical_turtle` yields byte-stable output.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel
from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.namespaces import CDS, CDS_TERM, DCTERMS

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_slug(v: str) -> str:
    """Reject anything but kebab-case (lowercase letters, digits, single hyphens).

    Slugs flow directly into IRIs, so an invalid one (spaces, parens, uppercase) would otherwise
    produce broken Turtle or an ugly identifier. Rejecting early yields a friendly CLI error.
    """
    if not _SLUG_RE.match(v):
        raise ValueError(
            f"slug {v!r} must be kebab-case: lowercase letters, digits, and single hyphens "
            "(e.g. 'reach-a-human')"
        )
    return v


#: A validated kebab-case slug, reused across every authorable model.
Slug = Annotated[str, AfterValidator(validate_slug)]

#: Authorable kinds → the vocabulary term slug used as the instance's semantic ``rdf:type``.
KIND_TERM: dict[str, str] = {
    "mission": "mission",
    "goal": "goal",
    "objective": "objective",
    "driver": "driver",
    "constraint": "constraint",
    "moe": "measure-of-effectiveness",
    "problem": "problem",
    "opportunity": "opportunity",
    "stakeholder": "stakeholder",
    "need": "need",
}
KINDS: tuple[str, ...] = tuple(KIND_TERM)


# ------------------------------------------------------------------------------- IRI helpers


def synthesis_iri(base: str, slug: str) -> URIRef:
    """IRI of a mapping/synthesis container."""
    return URIRef(f"{base}synthesis/{slug}")


def record_iri(base: str, kind: str, slug: str) -> URIRef:
    """IRI of an instance record of ``kind``."""
    return URIRef(f"{base}{kind}/{slug}")


# ------------------------------------------------------------------------------- models


class Synthesis(BaseModel):
    """The mapping container — a project's concept definition / integrated set of needs."""

    slug: Slug
    title: str
    description: str = ""


class Record(BaseModel):
    """Shared base for every authored instance."""

    slug: Slug
    kind: str
    label: str
    description: str
    synthesis: str  # slug of the parent Synthesis
    cites: list[str] = []  # provenance: source IRIs
    supersedes: list[str] = []  # IRIs of record(s) this one replaces (change provenance)

    def model_post_init(self, _context: object) -> None:
        if self.kind not in KIND_TERM:
            raise ValueError(f"unknown kind {self.kind!r}; expected one of {', '.join(KINDS)}")


class Statement(Record):
    """A plain business/mission-analysis statement (mission, driver, constraint, moe, problem…)."""


class Goal(Record):
    """A goal — may address problems/opportunities."""

    addresses: list[str] = []  # slugs of problem/opportunity it addresses


class Objective(Record):
    """A measurable objective refining one or more goals."""

    refines: list[str] = []  # goal slugs


class Stakeholder(Record):
    """A stakeholder, optionally within a segment/perspective."""

    segment: str | None = None
    interest: str | None = None
    influence: str | None = None


class Need(Record):
    """A stakeholder need (need-form; the 'shall'-free check lives in verify)."""

    for_stakeholder: list[str] = []  # stakeholder slugs
    serves_goal: list[str] = []  # goal slugs


# ------------------------------------------------------------------------------- serialization


def synthesis_to_graph(syn: Synthesis, *, base: str) -> Graph:
    """Emit a ``cds:Synthesis`` container."""
    g = Graph()
    s = synthesis_iri(base, syn.slug)
    g.add((s, RDF.type, CDS.Synthesis))
    g.add((s, RDFS.label, Literal(syn.title)))
    if syn.description:
        g.add((s, DCTERMS.description, Literal(syn.description)))
    return g


def record_to_graph(rec: Record, *, base: str) -> Graph:
    """Emit an instance record: typed by its vocabulary Term + the ``cds:Instance`` marker."""
    g = Graph()
    s = record_iri(base, rec.kind, rec.slug)
    g.add((s, RDF.type, CDS.Instance))
    g.add((s, RDF.type, CDS_TERM[KIND_TERM[rec.kind]]))
    g.add((s, RDFS.label, Literal(rec.label)))
    g.add((s, DCTERMS.description, Literal(rec.description)))
    g.add((s, CDS.inSynthesis, synthesis_iri(base, rec.synthesis)))
    for cite in sorted(rec.cites):
        g.add((s, CDS.cites, URIRef(cite)))
    for superseded in sorted(rec.supersedes):
        g.add((s, CDS.supersedes, URIRef(superseded)))

    if isinstance(rec, Goal):
        for slug in sorted(rec.addresses):
            g.add((s, CDS.addresses, record_iri(base, "problem", slug)))
    elif isinstance(rec, Objective):
        for slug in sorted(rec.refines):
            g.add((s, CDS.refines, record_iri(base, "goal", slug)))
    elif isinstance(rec, Stakeholder):
        if rec.segment:
            g.add((s, CDS.segment, Literal(rec.segment)))
        if rec.interest:
            g.add((s, CDS.interest, Literal(rec.interest)))
        if rec.influence:
            g.add((s, CDS.influence, Literal(rec.influence)))
    elif isinstance(rec, Need):
        for slug in sorted(rec.for_stakeholder):
            g.add((s, CDS.forStakeholder, record_iri(base, "stakeholder", slug)))
        for slug in sorted(rec.serves_goal):
            g.add((s, CDS.servesGoal, record_iri(base, "goal", slug)))
    return g


#: Which model class to instantiate for each kind (subclass where it adds links; else Statement).
_MODEL_FOR_KIND: dict[str, type[Record]] = {
    "goal": Goal,
    "objective": Objective,
    "stakeholder": Stakeholder,
    "need": Need,
}


def model_for_kind(kind: str) -> type[Record]:
    """The :class:`Record` subclass used to author ``kind`` (``Statement`` by default)."""
    if kind not in KIND_TERM:
        raise ValueError(f"unknown kind {kind!r}; expected one of {', '.join(KINDS)}")
    return _MODEL_FOR_KIND.get(kind, Statement)
