"""Canonical, byte-deterministic Turtle serialization (the igor sort pattern).

Our graphs contain **no blank nodes** — every node is a minted IRI — so a fully-sorted writer
is a sufficient canonical form: identical triples produce byte-identical Turtle regardless of
insertion order. (RDFC-1.0 is available if a stricter canonical form is ever needed, e.g. once
blank nodes appear.)

Determinism rules: sorted ``@prefix`` block; subjects sorted; ``rdf:type`` first (as ``a``)
then predicates sorted; objects sorted. Rendering uses ``Node.n3`` so literals, datatypes and
escaping are handled correctly. Timestamps in the graph are stable inputs, never ``now()``.
"""

from __future__ import annotations

from collections import defaultdict

from rdflib import RDF, Graph
from rdflib.namespace import NamespaceManager
from rdflib.term import Node


def canonical_turtle(graph: Graph, *, prefixes: dict[str, str]) -> str:
    """Serialize ``graph`` to canonical, byte-deterministic Turtle.

    ``prefixes`` maps prefix -> namespace IRI; any namespace not listed renders as a full IRI.
    """
    nm = NamespaceManager(Graph(), bind_namespaces="none")
    for pfx, ns in prefixes.items():
        nm.bind(pfx, ns, override=True, replace=True)

    def n3(node: Node) -> str:
        return node.n3(nm)

    def pred_key(pred: Node) -> tuple[int, str]:
        return (0, "") if pred == RDF.type else (1, n3(pred))

    grouped: dict[Node, dict[Node, set[Node]]] = defaultdict(lambda: defaultdict(set))
    for s, p, o in graph:
        grouped[s][p].add(o)

    lines: list[str] = [f"@prefix {pfx}: <{ns}> ." for pfx, ns in sorted(prefixes.items())]
    lines.append("")

    for subject in sorted(grouped, key=n3):
        predicates = grouped[subject]
        clauses: list[str] = []
        for pred in sorted(predicates, key=pred_key):
            pred_str = "a" if pred == RDF.type else n3(pred)
            objects = ",\n        ".join(n3(o) for o in sorted(predicates[pred], key=n3))
            clauses.append(f"    {pred_str} {objects}")
        lines.append(n3(subject))
        lines.append(" ;\n".join(clauses) + " .")
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"
