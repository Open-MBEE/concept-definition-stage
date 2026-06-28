"""Demand-driven materialization (MIREOT) with a per-source parsimony budget.

The bloat risk is anchoring: a ``cds:sysmlConstruct`` or ``skos:*Match`` edge references a large
external ontology. The rule is **reference ≠ materialize** — an anchor is one cheap IRI triple,
always allowed; pulling that term's *local description* in is a separate, budgeted step, done only
for IRIs we actually hold a source (cache) for, and only as a **minimal MIREOT slice** (label + one
definition + optionally the DIRECT parent — never the transitive supertype closure).

The build inventories the external IRIs invoked across the vocabulary, materializes exactly those it
has a source for, and reports materialized-vs-referenced with a per-source triple budget. A caller
fails the build when ``report.within_budget`` is False (parsimony review forced).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from rdflib import RDFS, Graph, URIRef

from cds.core.namespaces import CDS, CDS_LICENSE, CDS_TERM, CDS_WAIVER, DCTERMS, SKOS

# the anchor predicates whose external objects are candidates for materialization
_ANCHOR_PREDICATES: frozenset[URIRef] = frozenset(
    {
        RDFS.subClassOf,
        SKOS.exactMatch,
        SKOS.closeMatch,
        SKOS.broadMatch,
        SKOS.narrowMatch,
        SKOS.relatedMatch,
        CDS.sysmlConstruct,
    }
)

# our own namespaces — never "external", never materialized
_INTERNAL_PREFIXES: tuple[str, ...] = (
    str(CDS),
    str(CDS_TERM),
    str(CDS_LICENSE),
    str(CDS_WAIVER),
)

# label / definition predicates a minimal slice may carry (first match wins, one of each)
_LABEL_PREDICATES = (SKOS.prefLabel, RDFS.label)
_DEFINITION_PREDICATES = (SKOS.definition, RDFS.comment, DCTERMS.description)


def _is_internal(iri: URIRef) -> bool:
    return any(str(iri).startswith(prefix) for prefix in _INTERNAL_PREFIXES)


def invoked_external_iris(graph: Graph) -> set[URIRef]:
    """The external IRIs the graph anchors to (objects of anchor predicates, minus our own)."""
    return {
        o
        for _s, p, o in graph
        if p in _ANCHOR_PREDICATES and isinstance(o, URIRef) and not _is_internal(o)
    }


def mireot_slice(iri: URIRef, source: Graph, *, depth: int = 0) -> Graph:
    """A minimal slice of ``iri``: one label + one definition + (depth≥1) the direct parent.

    Never follows the supertype chain — ``depth`` caps at the *direct* ``rdfs:subClassOf`` parents.
    """
    g = Graph()
    for pred in _LABEL_PREDICATES:
        label = next(iter(source.objects(iri, pred)), None)
        if label is not None:
            g.add((iri, pred, label))
            break
    for pred in _DEFINITION_PREDICATES:
        definition = next(iter(source.objects(iri, pred)), None)
        if definition is not None:
            g.add((iri, pred, definition))
            break
    if depth >= 1:
        for parent in source.objects(iri, RDFS.subClassOf):
            if isinstance(parent, URIRef):
                g.add((iri, RDFS.subClassOf, parent))
    return g


@dataclass(frozen=True)
class ParsimonyReport:
    """The materialized-vs-referenced accounting for one build."""

    materialized_iris: tuple[str, ...]
    referenced_only: tuple[str, ...]
    triples_per_source: Mapping[str, int] = field(default_factory=dict)
    over_budget: tuple[str, ...] = ()

    @property
    def within_budget(self) -> bool:
        return not self.over_budget


def _source_key_for(iri: URIRef, sources: Mapping[str, Graph]) -> str | None:
    """The source whose namespace prefix covers ``iri`` (longest match), or None if uncached."""
    matches = [key for key in sources if str(iri).startswith(key)]
    return max(matches, key=len) if matches else None


def build_extracts(
    graph: Graph,
    *,
    sources: Mapping[str, Graph],
    budgets: Mapping[str, int],
    depth: int = 0,
) -> tuple[Graph, ParsimonyReport]:
    """Materialize minimal slices for invoked IRIs we hold a source for; report the rest.

    ``sources`` maps a namespace prefix -> its cached source graph; ``budgets`` maps the same prefix
    -> a max materialized-triple count. Invoked IRIs without a source stay **reference-only**.
    """
    extracts = Graph()
    materialized: list[str] = []
    referenced_only: list[str] = []
    triples_per_source: dict[str, int] = {key: 0 for key in sources}

    for iri in sorted(invoked_external_iris(graph), key=str):
        key = _source_key_for(iri, sources)
        slice_ = mireot_slice(iri, sources[key], depth=depth) if key is not None else Graph()
        if key is None or len(slice_) == 0:
            # no source, or the source's namespace matched but it doesn't actually describe the IRI
            referenced_only.append(str(iri))
            continue
        extracts += slice_
        triples_per_source[key] += len(slice_)
        materialized.append(str(iri))

    over_budget = tuple(
        key for key, count in triples_per_source.items() if key in budgets and count > budgets[key]
    )
    report = ParsimonyReport(
        materialized_iris=tuple(materialized),
        referenced_only=tuple(referenced_only),
        triples_per_source=triples_per_source,
        over_budget=over_budget,
    )
    return extracts, report
