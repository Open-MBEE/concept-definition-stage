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
from typing import Literal as TypingLiteral

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


def _validate_slug_list(values: list[str]) -> list[str]:
    """Split comma-separated entries and validate each as a kebab slug.

    Catches the ``--for-stakeholder a,b`` corruption (one malformed IRI): the comma list becomes two
    validated slugs, and a bad target (space, comma-only, uppercase) is rejected rather than baked
    into an invalid IRI.
    """
    out: list[str] = []
    for value in values:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                out.append(validate_slug(part))
    return out


#: A list of kebab slugs referencing other records (comma-lists accepted, each validated).
SlugList = Annotated[list[str], AfterValidator(_validate_slug_list)]

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

#: Kinds typed by a MINTED cds-core class (tool structure, like cds:Tension) rather than a
#: canonical vocabulary Term — no cdsterm concept is fabricated for them (ADR-9 R7).
CORE_KIND_CLASS: dict[str, URIRef] = {"position": CDS.Position}

#: Every kind a user may author: the canon-typed kinds plus the core-class kinds.
AUTHORABLE_KINDS: tuple[str, ...] = (*KIND_TERM, *CORE_KIND_CLASS)


def type_iri_for_kind(kind: str) -> URIRef:
    """The semantic ``rdf:type`` for records of ``kind`` (vocabulary Term or core class)."""
    if kind in KIND_TERM:
        return CDS_TERM[KIND_TERM[kind]]
    return CORE_KIND_CLASS[kind]


def validate_record_ref(v: str) -> str:
    """A ``<kind>/<slug>`` reference to another record (e.g. ``objective/coverage``)."""
    kind, sep, slug = v.partition("/")
    if not sep or kind not in KIND_TERM:
        raise ValueError(
            f"record reference {v!r} must be '<kind>/<slug>' with kind one of "
            f"{', '.join(KIND_TERM)}"
        )
    validate_slug(slug)
    return v


#: A validated ``<kind>/<slug>`` reference to another record.
RecordRef = Annotated[str, AfterValidator(validate_record_ref)]


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
        if self.kind not in AUTHORABLE_KINDS:
            raise ValueError(
                f"unknown kind {self.kind!r}; expected one of {', '.join(AUTHORABLE_KINDS)}"
            )


class Statement(Record):
    """A plain business/mission-analysis statement (mission, driver, constraint, moe, problem…)."""


class Goal(Record):
    """A goal — may address problems/opportunities."""

    addresses: SlugList = []  # slugs of problem/opportunity it addresses


class Objective(Record):
    """A measurable objective refining one or more goals."""

    refines: SlugList = []  # goal slugs


class Stakeholder(Record):
    """A stakeholder, optionally within a segment/perspective."""

    segment: str | None = None
    interest: str | None = None
    influence: str | None = None


class Need(Record):
    """A stakeholder need (need-form; the 'shall'-free check lives in verify)."""

    for_stakeholder: SlugList = []  # stakeholder slugs
    serves_goal: SlugList = []  # goal slugs


class Position(Record):
    """A stakeholder's stance on another record — the X2-lite perspective primitive (ADR-9 R7).

    The description is the position statement; divergence between positions on the same
    target is surfaced as a *finding* (``DivergingPositions``), never a violation — two
    stakeholders may validly conflict on desired outcome or feasibility.
    """

    characterizes: RecordRef  # "<kind>/<slug>" of the record this stance reads
    held_by: Slug  # stakeholder slug
    stance: TypingLiteral["supports", "opposes", "prioritizes", "constrains", "reads-as"]
    invariance: str | None = None  # what this reading holds constant (lineage-compatible)


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
    g.add((s, RDF.type, type_iri_for_kind(rec.kind)))
    g.add((s, RDFS.label, Literal(rec.label)))
    g.add((s, DCTERMS.description, Literal(rec.description)))
    g.add((s, CDS.inSynthesis, synthesis_iri(base, rec.synthesis)))
    for cite in sorted(rec.cites):
        g.add((s, CDS.cites, URIRef(cite)))
    for superseded in sorted(rec.supersedes):
        # a bare slug resolves to a same-kind record (G-2: one reference rule everywhere);
        # a full IRI passes through untouched
        target = URIRef(superseded) if "://" in superseded \
            else record_iri(base, rec.kind, superseded)
        g.add((s, CDS.supersedes, target))

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
    elif isinstance(rec, Position):
        ckind, _, cslug = rec.characterizes.partition("/")
        g.add((s, CDS.characterizes, record_iri(base, ckind, cslug)))
        g.add((s, CDS.heldBy, record_iri(base, "stakeholder", rec.held_by)))
        g.add((s, CDS.stance, Literal(rec.stance)))
        if rec.invariance:
            g.add((s, CDS.invarianceCriterion, Literal(rec.invariance)))
    return g


#: Which model class to instantiate for each kind (subclass where it adds links; else Statement).
_MODEL_FOR_KIND: dict[str, type[Record]] = {
    "goal": Goal,
    "objective": Objective,
    "stakeholder": Stakeholder,
    "need": Need,
    "position": Position,
}


def model_for_kind(kind: str) -> type[Record]:
    """The :class:`Record` subclass used to author ``kind`` (``Statement`` by default)."""
    if kind not in AUTHORABLE_KINDS:
        raise ValueError(
            f"unknown kind {kind!r}; expected one of {', '.join(AUTHORABLE_KINDS)}"
        )
    return _MODEL_FOR_KIND.get(kind, Statement)
