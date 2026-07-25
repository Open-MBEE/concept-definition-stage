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

from rdflib import Graph, URIRef

from cds.core.model.instances import (
    Record,
    Synthesis,
    record_iri,
    record_to_graph,
    synthesis_iri,
    synthesis_to_graph,
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
    """Parse-if-exists → union → deterministic re-serialize (the ant-rdf accumulation primitive)."""
    graph = Graph()
    if target.exists():
        graph.parse(target, format="turtle")
    graph += addition
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(canonical_turtle(graph, prefixes=_prefixes(project)), encoding="utf-8")


def _synthesis_file(project: Project) -> Path:
    return project.instances_dir / "synthesis.ttl"


def _kind_file(project: Project, kind: str) -> Path:
    return project.instances_dir / f"{kind}.ttl"


def create_synthesis(project: Project, syn: Synthesis) -> URIRef:
    """Author (or update) the mapping container; returns its IRI."""
    _merge_into(_synthesis_file(project), synthesis_to_graph(syn, base=project.base_iri), project)
    return synthesis_iri(project.base_iri, syn.slug)


def create_record(project: Project, rec: Record) -> URIRef:
    """Author a single instance record into its per-kind file; returns its IRI."""
    _merge_into(_kind_file(project, rec.kind), record_to_graph(rec, base=project.base_iri), project)
    return record_iri(project.base_iri, rec.kind, rec.slug)


def project_graph(project: Project) -> Graph:
    """Load and merge every instance Turtle file in the project (sorted, for determinism)."""
    graph = Graph()
    instances = project.instances_dir
    if instances.is_dir():
        for ttl in sorted(instances.glob("*.ttl")):
            graph.parse(ttl, format="turtle")
    return graph
