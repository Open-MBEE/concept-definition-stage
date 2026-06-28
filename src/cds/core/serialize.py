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

import re
from collections import defaultdict

from rdflib import RDF, Graph, URIRef
from rdflib.namespace import NamespaceManager
from rdflib.term import Node

# A prefixed name's local part is only emitted when it is parse-safe (a conservative subset of
# Turtle's PN_LOCAL): otherwise rdflib will happily produce an invalid qname such as
# ``sebok:Engineered_System_(glossary)`` (parentheses are not allowed) that fails to re-parse.
_PARSE_SAFE_LOCAL = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")


def canonical_turtle(graph: Graph, *, prefixes: dict[str, str]) -> str:
    """Serialize ``graph`` to canonical, byte-deterministic Turtle.

    ``prefixes`` maps prefix -> namespace IRI; any namespace not listed renders as a full IRI.
    """
    nm = NamespaceManager(Graph(), bind_namespaces="none")
    for pfx, ns in prefixes.items():
        nm.bind(pfx, ns, override=True, replace=True)

    def n3(node: Node) -> str:
        rendered = node.n3(nm)
        if isinstance(node, URIRef) and not rendered.startswith("<"):
            # a prefixed name was produced — keep it only if its local part is parse-safe
            local = rendered.partition(":")[2]
            if not (_PARSE_SAFE_LOCAL.match(local) and not local.endswith(".")):
                return f"<{node}>"
        return rendered

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
