"""SysML v2 structural anchoring by equivalence axioms (no vendored OWL cache).

The established DSG pattern (see ADCS-lifecycle-demo): we do **not** vendor the SysML v2 OWL or run
openCAESAR/JVM. Instead each *invoked* construct is declared locally in the ``sysml:`` namespace
and aliased to the OMG SysML v2 OWL rendering (``omg-sysml:``) via ``owl:equivalentClass`` /
``owl:equivalentProperty``, plus a minimal stub of the OMG-side target so it is not dangling.
Parsimony by construction: only constructs a term actually anchors to are emitted — one cheap axiom
each, pure Python, no runtime dependency. JPL/OpenMBEE tooling sees standard SysML v2 via the alias.
"""

from __future__ import annotations

from rdflib import OWL, RDF, Graph, URIRef

from cds.core.namespaces import CDS, OMG_SYSML, SYSML

# the few SysML constructs that are properties rather than classes (kind drives the axiom flavour)
_PROPERTY_CONSTRUCTS: frozenset[str] = frozenset({"declaredName", "text", "ownedRelationship"})


def _local_name(iri: URIRef) -> str | None:
    """The construct's local name if ``iri`` is in our ``sysml:`` namespace, else None."""
    text = str(iri)
    base = str(SYSML)
    return text[len(base) :] if text.startswith(base) else None


def invoked_constructs(graph: Graph) -> set[URIRef]:
    """The SysML constructs the graph's terms anchor to (objects of ``cds:sysmlConstruct``)."""
    return {
        o for _s, _p, o in graph.triples((None, CDS.sysmlConstruct, None)) if isinstance(o, URIRef)
    }


def sysml_anchor_graph(graph: Graph) -> Graph:
    """Emit equivalence axioms (+ OMG stubs) for every invoked SysML construct."""
    g = Graph()
    for iri in sorted(invoked_constructs(graph), key=str):
        local = _local_name(iri)
        if local is None:
            continue  # an anchor outside our sysml: namespace — leave as a bare reference
        omg = OMG_SYSML[local]
        is_property = local in _PROPERTY_CONSTRUCTS
        kind = OWL.ObjectProperty if is_property else OWL.Class
        equivalence = OWL.equivalentProperty if is_property else OWL.equivalentClass
        g.add((iri, RDF.type, kind))
        g.add((iri, equivalence, omg))
        g.add((omg, RDF.type, kind))  # minimal stub of the OMG-side target
    return g
