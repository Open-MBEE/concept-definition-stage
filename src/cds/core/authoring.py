"""Authoring — write a user's concept-definition instances into *their* repo, deterministically.

The accumulation primitive (``_merge_into``, ported from ant-rdf) is the heart: parse the existing
per-kind Turtle file if present, union the new record's triples, and re-serialize with the canonical
writer so the file is byte-stable regardless of authoring order. Every record of a kind accumulates
into one file (``instances/<kind>.ttl``); the container lives in ``instances/synthesis.ttl``.

All writes funnel through here and :mod:`cds.core.workspace` — the single I/O choke point kept
for a future remote (Flexo/MMS) backend and a pyoxigraph store.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.model.instances import (
    KIND_TERM,
    Record,
    Synthesis,
    record_iri,
    record_to_graph,
    synthesis_iri,
    synthesis_to_graph,
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


def create_record(project: Project, rec: Record) -> URIRef:
    """Author (upsert) a single instance record into its per-kind file; returns its IRI."""
    _merge_into(_kind_file(project, rec.kind), record_to_graph(rec, base=project.base_iri), project)
    return record_iri(project.base_iri, rec.kind, rec.slug)


def remove_record(project: Project, kind: str, slug: str) -> bool:
    """Delete a record; returns False if it didn't exist."""
    return _remove_subject(
        _kind_file(project, kind), record_iri(project.base_iri, kind, slug), project
    )


def list_records(project: Project, kind: str) -> list[tuple[str, str]]:
    """Every record of ``kind`` as ``(slug, label)``, sorted by slug."""
    graph = _load(_kind_file(project, kind))
    out: list[tuple[str, str]] = []
    for s in graph.subjects(RDF.type, CDS_TERM[KIND_TERM[kind]]):
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
    for pred in ("forStakeholder", "servesGoal", "refines", "addresses", "supersedes", "cites"):
        targets = sorted(str(o).rsplit("/", 1)[-1] for o in graph.objects(s, CDS[pred]))
        if targets:
            lines.append(f"  {pred}: {', '.join(targets)}")
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
