"""Authoring — write a user's concept-definition instances into *their* repo, deterministically.

The accumulation primitive (``_merge_into``, ported from ant-rdf) is the heart: parse the existing
per-kind Turtle file if present, union the new record's triples, and re-serialize with the canonical
writer so the file is byte-stable regardless of authoring order. Every record of a kind accumulates
into one file (``instances/<kind>.ttl``); the container lives in ``instances/synthesis.ttl``.

All writes funnel through here and :mod:`cds.core.workspace` — the single I/O choke point kept
for a future remote (Flexo/MMS) backend and a pyoxigraph store.

**Mutation modes (ADR-9).** These functions operate on a *working copy* — the user's project
dir or a session staging root — which is **scratch**: :func:`create_record` (refuses an
existing slug), :func:`edit_record` (requires one), :func:`upsert_record` (the explicit
old-style replace, used by the commit gate and fixtures), and the ``remove_*`` deletions are
all legitimate there. The **append-only** primitives — :func:`retract_record`,
:func:`mark_superseded` — only ever add triples (lifecycle markers); they express
durable-record intent and never remove content. The commit gate (P2) is the sole crossing
from scratch into the durable record.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.model.instances import (
    Record,
    Synthesis,
    record_iri,
    record_to_graph,
    synthesis_iri,
    synthesis_to_graph,
    type_iri_for_kind,
)
from cds.core.model.notes import (
    ParkedItem,
    RetrievalItem,
    RetrievalStatus,
    Tension,
    TensionStatus,
    parked_iri,
    parked_to_graph,
    queue_iri,
    queue_to_graph,
    tension_iri,
    tension_to_graph,
)
from cds.core.namespaces import CDS, CDS_TERM, DCTERMS, SKOS
from cds.core.serialize import canonical_turtle
from cds.core.workspace import Project

#: Prefixes bound in every instance Turtle file (``proj`` is added per-project at write time).
_BASE_PREFIXES: dict[str, str] = {
    "cds": str(CDS),
    "cdsterm": str(CDS_TERM),
    "dcterms": str(DCTERMS),
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": str(SKOS),
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def _prefixes(project: Project) -> dict[str, str]:
    return {**_BASE_PREFIXES, "proj": project.base_iri}


class RecordExistsError(KeyError):
    """``create`` on a slug that already exists — use ``edit`` (or supersede) instead (F-2)."""


class RecordNotFoundError(KeyError):
    """``edit``/``retract`` on a record that does not exist."""


class AlreadyRetractedError(KeyError):
    """A second retraction of the same record — the marker is append-once (no reason rewrite)."""


def _merge_into(target: Path, addition: Graph, project: Project) -> None:
    """Upsert a record: parse-if-exists → **replace** the subject's triples → deterministic write.

    This is an *upsert*, not a blind union: re-authoring a slug replaces that subject's prior
    triples rather than appending, so correcting/reversing an answer (re-run ``cds new`` with the
    fixed values) yields a single clean record instead of a contradictory multi-valued one. Other
    subjects in the same file are untouched (per-kind accumulation still holds).
    """
    graph = Graph()
    if target.exists():
        graph.parse(target, format="turtle")
    for subject in set(addition.subjects()):
        graph.remove((subject, None, None))  # upsert: drop any prior assertions for this subject
    graph += addition
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(canonical_turtle(graph, prefixes=_prefixes(project)), encoding="utf-8")


def _remove_subject(target: Path, subject: URIRef, project: Project) -> bool:
    """Delete a subject's triples from ``target``; returns False if it wasn't present."""
    if not target.exists():
        return False
    graph = Graph()
    graph.parse(target, format="turtle")
    if (subject, None, None) not in graph:
        return False
    graph.remove((subject, None, None))
    target.write_text(canonical_turtle(graph, prefixes=_prefixes(project)), encoding="utf-8")
    return True


def _synthesis_file(project: Project) -> Path:
    return project.instances_dir / "synthesis.ttl"


def _kind_file(project: Project, kind: str) -> Path:
    return project.instances_dir / f"{kind}.ttl"


def create_synthesis(project: Project, syn: Synthesis) -> URIRef:
    """Author (or update) the mapping container; returns its IRI."""
    _merge_into(_synthesis_file(project), synthesis_to_graph(syn, base=project.base_iri), project)
    return synthesis_iri(project.base_iri, syn.slug)


def _record_exists(project: Project, kind: str, slug: str) -> bool:
    graph = _load(_kind_file(project, kind))
    return (record_iri(project.base_iri, kind, slug), None, None) in graph


def create_record(project: Project, rec: Record) -> URIRef:
    """Author a NEW instance record; refuses an existing slug (scratch mode, ADR-9/F-2)."""
    if _record_exists(project, rec.kind, rec.slug):
        raise RecordExistsError(
            f"{rec.kind} {rec.slug!r} already exists. Edit it, or create a new slug "
            f"with supersedes={rec.slug!r} to replace it in the durable record "
            f"(`cds explain changes` compares the options)"
        )
    return upsert_record(project, rec)


def edit_record(project: Project, rec: Record) -> URIRef:
    """Edit an EXISTING record in place (scratch mode); refuses an absent slug."""
    if not _record_exists(project, rec.kind, rec.slug):
        raise RecordNotFoundError(f"no {rec.kind} {rec.slug!r} to edit — create it first")
    return upsert_record(project, rec)


def upsert_record(project: Project, rec: Record) -> URIRef:
    """Replace-or-create a record unconditionally — the explicit upsert.

    The primitive behind :func:`create_record`/:func:`edit_record`; also used directly by
    the commit gate (approver-confirmed revisions) and by fixtures/migrations.

    Authored ``supersedes`` targets that are project-local existing records get the inverse
    ``cds:supersededBy`` marker appended **eagerly** (ADR-9): the scratch graph and the
    gate-merged graph read identically, and the superseded record leaves the current view
    the moment its replacement is authored.
    """
    _merge_into(_kind_file(project, rec.kind), record_to_graph(rec, base=project.base_iri), project)
    s = record_iri(project.base_iri, rec.kind, rec.slug)
    for target in rec.supersedes:
        iri = target if "://" in target else str(record_iri(project.base_iri, rec.kind, target))
        if not iri.startswith(project.base_iri):
            continue  # external reference — nothing local to mark
        rel = iri[len(project.base_iri):]
        tkind, _, tslug = rel.partition("/")
        if not tslug or not _record_exists(project, tkind, tslug):
            continue  # dangling target — surfaced by verify, not silently marked
        graph = _load(_kind_file(project, tkind))
        old = record_iri(project.base_iri, tkind, tslug)
        if (old, CDS.supersededBy, s) not in graph:
            mark_superseded(project, tkind, tslug, by=s)
    return s


def remove_record(project: Project, kind: str, slug: str) -> bool:
    """Delete a record from the WORKING COPY (scratch mode); returns False if absent.

    In the durable record deletion does not exist — use :func:`retract_record` there.
    """
    return _remove_subject(
        _kind_file(project, kind), record_iri(project.base_iri, kind, slug), project
    )


def _append_marker_triples(project: Project, kind: str, additions: Graph) -> None:
    """APPEND-ONLY write: union marker triples into the kind file — nothing is removed."""
    target = _kind_file(project, kind)
    graph = _load(target)
    graph += additions
    target.write_text(canonical_turtle(graph, prefixes=_prefixes(project)), encoding="utf-8")


def retract_record(
    project: Project, kind: str, slug: str, *, reason: str | None = None
) -> URIRef:
    """Retire a record with an append-only marker (ADR-9): content triples are preserved."""
    s = record_iri(project.base_iri, kind, slug)
    graph = _load(_kind_file(project, kind))
    if (s, None, None) not in graph:
        raise RecordNotFoundError(f"no {kind} {slug!r} to retract")
    if (s, CDS.retracted, Literal(True)) in graph:
        raise AlreadyRetractedError(f"{kind} {slug!r} is already retracted")
    marker = Graph()
    marker.add((s, CDS.retracted, Literal(True)))
    if reason is not None:
        marker.add((s, CDS.retractionReason, Literal(reason)))
    _append_marker_triples(project, kind, marker)
    return s


def mark_superseded(project: Project, kind: str, slug: str, *, by: URIRef) -> None:
    """Append the materialized inverse marker ``cds:supersededBy`` to the OLD record (ADR-9)."""
    s = record_iri(project.base_iri, kind, slug)
    graph = _load(_kind_file(project, kind))
    if (s, None, None) not in graph:
        raise RecordNotFoundError(f"no {kind} {slug!r} to mark superseded")
    marker = Graph()
    marker.add((s, CDS.supersededBy, by))
    _append_marker_triples(project, kind, marker)


def merge_subject_graph(project: Project, subject: URIRef, source: Graph) -> None:
    """Upsert one subject's triples (taken from ``source``) into its per-kind file.

    The commit gate's merge primitive: routes by the IRI's ``<kind>/<slug>`` path segment
    (``synthesis`` → the container file). Uses the same deterministic upsert as authoring.
    """
    rel = str(subject)[len(project.base_iri):]
    kind = rel.split("/", 1)[0]
    target = _synthesis_file(project) if kind == "synthesis" else _kind_file(project, kind)
    sub = Graph()
    for triple in source.triples((subject, None, None)):
        sub.add(triple)
    _merge_into(target, sub, project)


def find_referrers(project: Project, target: URIRef) -> list[URIRef]:
    """Subjects anywhere in the project that link to ``target`` — the retraction/discard
    pre-check (lineage pattern): callers warn with this list rather than dangling silently."""
    graph = project_graph(project)
    return sorted(
        {s for s, _p, o in graph.triples((None, None, target))
         if isinstance(s, URIRef) and s != target},
        key=str,
    )


def list_records(project: Project, kind: str) -> list[tuple[str, str]]:
    """Every record of ``kind`` as ``(slug, label)``, sorted by slug."""
    graph = _load(_kind_file(project, kind))
    out: list[tuple[str, str]] = []
    for s in graph.subjects(RDF.type, type_iri_for_kind(kind)):
        label = graph.value(s, RDFS.label)
        out.append((str(s).rsplit("/", 1)[-1], str(label) if label is not None else ""))
    return sorted(out)


def show_record(project: Project, kind: str, slug: str) -> list[str] | None:
    """Human-readable display lines for one record, or ``None`` if absent."""
    graph = _load(_kind_file(project, kind))
    s = record_iri(project.base_iri, kind, slug)
    if (s, None, None) not in graph:
        return None
    lines = [f"{kind} {slug}  <{s}>"]
    label = graph.value(s, RDFS.label)
    desc = graph.value(s, DCTERMS.description)
    lines.append(f"  label:       {label}")
    lines.append(f"  description: {desc}")
    for pred in ("forStakeholder", "servesGoal", "refines", "addresses", "supersedes", "cites",
                 "characterizes", "heldBy", "stance"):
        targets = sorted(str(o).rsplit("/", 1)[-1] for o in graph.objects(s, CDS[pred]))
        if targets:
            lines.append(f"  {pred}: {', '.join(targets)}")
    # lifecycle state (ADR-9/G-6): append-only must be inspectable, not taken on faith
    if (s, CDS.retracted, None) in graph:
        reason = graph.value(s, CDS.retractionReason)
        lines.append("  retracted:   true" + (f" ({reason})" if reason is not None else ""))
    superseded_by = sorted(str(o).rsplit("/", 1)[-1] for o in graph.objects(s, CDS.supersededBy))
    if superseded_by:
        lines.append(f"  supersededBy: {', '.join(superseded_by)}")
    return lines


def project_graph(project: Project) -> Graph:
    """Load and merge every instance Turtle file in the project (sorted, for determinism)."""
    graph = Graph()
    instances = project.instances_dir
    if instances.is_dir():
        for ttl in sorted(instances.glob("*.ttl")):
            graph.parse(ttl, format="turtle")
    return graph


# ------------------------------------------------------------------------------- side ledgers


def _parked_file(project: Project) -> Path:
    return project.instances_dir / "parked.ttl"


def _queue_file(project: Project) -> Path:
    return project.instances_dir / "queue.ttl"


def _load(target: Path) -> Graph:
    graph = Graph()
    if target.exists():
        graph.parse(target, format="turtle")
    return graph


def create_parked(project: Project, item: ParkedItem) -> URIRef:
    """Park an out-of-scope idea; returns its IRI."""
    _merge_into(_parked_file(project), parked_to_graph(item, base=project.base_iri), project)
    return parked_iri(project.base_iri, item.slug)


def list_parked(project: Project) -> list[tuple[str, str]]:
    """Every parked item as ``(slug, label)``, sorted by slug."""
    graph = _load(_parked_file(project))
    out: list[tuple[str, str]] = []
    for s in graph.subjects(RDF.type, CDS.ParkedItem):
        label = graph.value(s, RDFS.label)
        out.append((str(s).rsplit("/", 1)[-1], str(label) if label is not None else ""))
    return sorted(out)


def create_queue_item(project: Project, item: RetrievalItem) -> URIRef:
    """Add an open unknown to the retrieval queue; returns its IRI."""
    _merge_into(_queue_file(project), queue_to_graph(item, base=project.base_iri), project)
    return queue_iri(project.base_iri, item.slug)


def set_queue_status(
    project: Project,
    slug: str,
    status: RetrievalStatus,
    *,
    locator: str | None = None,
) -> None:
    """Advance a queue item's status (and optionally record where the answer was found)."""
    target = _queue_file(project)
    graph = _load(target)
    s = queue_iri(project.base_iri, slug)
    if (s, RDF.type, CDS.RetrievalItem) not in graph:
        raise KeyError(f"no queue item {slug!r}")
    graph.remove((s, CDS.retrievalStatus, None))
    graph.add((s, CDS.retrievalStatus, Literal(status.value)))
    if locator is not None:
        graph.remove((s, CDS.locator, None))
        graph.add((s, CDS.locator, Literal(locator)))
    target.write_text(canonical_turtle(graph, prefixes=_prefixes(project)), encoding="utf-8")


def list_queue(project: Project) -> list[tuple[str, str, str]]:
    """Every retrieval item as ``(slug, status, question)``, sorted by slug."""
    graph = _load(_queue_file(project))
    out: list[tuple[str, str, str]] = []
    for s in graph.subjects(RDF.type, CDS.RetrievalItem):
        status = graph.value(s, CDS.retrievalStatus)
        label = graph.value(s, RDFS.label)
        out.append(
            (
                str(s).rsplit("/", 1)[-1],
                str(status) if status is not None else "",
                str(label) if label is not None else "",
            )
        )
    return sorted(out)


def _tension_file(project: Project) -> Path:
    return project.instances_dir / "tension.ttl"


def create_tension(project: Project, item: Tension) -> URIRef:
    """Record (upsert) a named conflict between records; returns its IRI."""
    _merge_into(_tension_file(project), tension_to_graph(item, base=project.base_iri), project)
    return tension_iri(project.base_iri, item.slug)


def set_tension_status(project: Project, slug: str, status: TensionStatus) -> None:
    """Mark a tension open/resolved; resolved tensions drop out of the compiled brief."""
    target = _tension_file(project)
    graph = _load(target)
    s = tension_iri(project.base_iri, slug)
    if (s, RDF.type, CDS.Tension) not in graph:
        raise KeyError(f"no tension {slug!r}")
    graph.remove((s, CDS.tensionStatus, None))
    graph.add((s, CDS.tensionStatus, Literal(status.value)))
    target.write_text(canonical_turtle(graph, prefixes=_prefixes(project)), encoding="utf-8")


def remove_parked(project: Project, slug: str) -> bool:
    """Delete a parked idea; returns False if absent."""
    return _remove_subject(_parked_file(project), parked_iri(project.base_iri, slug), project)


def remove_queue_item(project: Project, slug: str) -> bool:
    """Delete a retrieval-queue item; returns False if absent."""
    return _remove_subject(_queue_file(project), queue_iri(project.base_iri, slug), project)


def remove_tension(project: Project, slug: str) -> bool:
    """Delete a tension; returns False if absent."""
    return _remove_subject(_tension_file(project), tension_iri(project.base_iri, slug), project)
