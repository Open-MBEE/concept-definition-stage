"""The current view — ADR-9's graph-query filter over lifecycle markers.

A record is **current** iff it carries no ``cds:supersededBy`` and no ``cds:retracted true``.
The filter is a graph query, never a file/directory convention (lineage constraint: a
rendered view must be rebuildable from the union graph alone). The full graph keeps every
marker and every non-current record's content — the changelog is never lost by not being
displayed.

Scope note (D7-ready): if a view ever needs its own identity, mint an IRI usable unchanged
as a named-graph URI (e.g. ``https://w3id.org/cds/view/current``) — no IRI migration when
named graphs land.
"""

from __future__ import annotations

from rdflib import Graph, Literal
from rdflib.term import Node

from cds.core.namespaces import CDS


def is_current(graph: Graph, subject: Node) -> bool:
    """True iff ``subject`` is neither superseded nor retracted in ``graph``."""
    if (subject, CDS.supersededBy, None) in graph:
        return False
    return (subject, CDS.retracted, Literal(True)) not in graph


def current_view(graph: Graph) -> Graph:
    """The deterministic subgraph containing only current subjects' triples.

    Non-subject-scoped triples (e.g. waivers, ontology imports) pass through untouched —
    only subjects carrying a lifecycle marker are filtered out.
    """
    out = Graph()
    for s, p, o in graph:
        if is_current(graph, s):
            out.add((s, p, o))
    return out
