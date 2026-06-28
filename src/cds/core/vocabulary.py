"""The cds-core vocabulary — thin class/property declarations for the model.

This is the single Python source of truth for the ``cds:`` terms; ``ontology/cds-core.ttl`` is its
deterministic, committed build output (regenerate with ``write_core_ttl``). It formalizes the
classes the emitters have used as ``rdf:type`` since slice 4 — ``cds:Authority`` subClassOf
``prov:Agent``, ``cds:Source`` of ``prov:Entity``, ``cds:Term`` of ``skos:Concept`` — declares every
``cds:`` property, and folds in the controlled-vocabulary SKOS schemes. Domains/ranges are
deliberately omitted: the structural expectations live in the SHACL shapes; the core stays thin.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef

from cds import __version__
from cds.core.controlled import controlled_vocab_graph
from cds.core.namespaces import CDS, PROV, SKOS
from cds.core.serialize import canonical_turtle

CORE_TTL_PATH = Path(__file__).resolve().parents[3] / "ontology" / "cds-core.ttl"
CORE_ONTOLOGY = URIRef("https://w3id.org/cds")

CORE_PREFIXES: dict[str, str] = {
    "cds": str(CDS),
    "owl": str(OWL),
    "prov": str(PROV),
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "skos": str(SKOS),
}

# (local name, parent class or None, comment)
_CLASSES: tuple[tuple[str, URIRef | None, str], ...] = (
    ("Authority", PROV.Agent, "An entity holding authoritative content (a source's holder)."),
    ("Source", PROV.Entity, "A boundary object: a specific artifact held by an authority."),
    ("Term", SKOS.Concept, "A Concept Definition reference-vocabulary term."),
    ("RetrievalActivity", PROV.Activity, "The act of retrieving (capturing) a source."),
    ("VerificationActivity", PROV.Activity, "The act of verifying a source's content."),
    ("LifecycleModel", None, "A system modeled across its life cycle, from Concept Definition."),
    ("Waiver", None, "An append-only, conscious acceptance of a non-Violation verify finding."),
)

# (local name, comment) — properties whose value is a resource
_OBJECT_PROPS: tuple[tuple[str, str], ...] = (
    ("authorityKind", "The controlled kind of an authority."),
    ("captureTier", "How faithfully a source is captured (reference / snapshot)."),
    ("cites", "Links a term to a boundary-object source it draws on."),
    ("license", "The tracked SPDX license of a referenced asset (tracked, not enforced)."),
    ("codeLicense", "The code license declared by a lifecycle model."),
    ("textLicense", "The text license of a lifecycle model (gates restricted-canon rendering)."),
    ("retrievalStatus", "The construction-order state of a retrieval (pending/provided/verified)."),
    ("sourceType", "The controlled kind of artifact a source points at."),
    ("sysmlConstruct", "The SysML v2 construct a term structurally anchors to."),
    ("verificationMethod", "How a source's content was confirmed (checksum/visual/machine)."),
    ("wasVerifiedBy", "Links a source to a verification activity performed over it."),
    ("waivesFocus", "The specific focus node a waiver applies to."),
)

# (local name, comment) — properties whose value is a literal
_DATA_PROPS: tuple[tuple[str, str], ...] = (
    ("contentHash", "The content hash (e.g. sha256:...) of a captured source."),
    ("locator", "The locator (URI or document number) of a source."),
    ("snapshot", "The content-addressed local snapshot filename of a captured source."),
    ("retrievalIssue", "The retrieval-escalation issue URL for a not-yet-secured source."),
    ("verificationNote", "Prose note on how a verification was performed."),
    ("nrmCanon", "An INCOSE NRM / GtWR grounding note on a term."),
    ("stage", "The life-cycle stage label of a lifecycle model."),
    ("licenseText", "The verbatim terms of a custom license."),
    ("reproducible", "Whether a custom license permits reproduction/redistribution."),
    ("waivesRule", "The verify rule (check name) a waiver accepts."),
    ("waiverReason", "Why a waiver was consciously accepted."),
)


def core_vocab_graph() -> Graph:
    """Build the in-memory cds-core vocabulary (classes + properties + controlled schemes)."""
    g = Graph()
    g.add((CORE_ONTOLOGY, RDF.type, OWL.Ontology))
    g.add((CORE_ONTOLOGY, RDFS.label, Literal("cds core vocabulary")))
    g.add((CORE_ONTOLOGY, OWL.versionInfo, Literal(__version__)))

    for name, parent, comment in _CLASSES:
        s = CDS[name]
        g.add((s, RDF.type, RDFS.Class))
        g.add((s, RDF.type, OWL.Class))
        g.add((s, RDFS.label, Literal(name)))
        g.add((s, RDFS.comment, Literal(comment)))
        if parent is not None:
            g.add((s, RDFS.subClassOf, parent))

    for name, comment in _OBJECT_PROPS:
        _declare_property(g, name, OWL.ObjectProperty, comment)
    for name, comment in _DATA_PROPS:
        _declare_property(g, name, OWL.DatatypeProperty, comment)

    g += controlled_vocab_graph()
    return g


def _declare_property(g: Graph, name: str, kind: URIRef, comment: str) -> None:
    s = CDS[name]
    g.add((s, RDF.type, RDF.Property))
    g.add((s, RDF.type, kind))
    g.add((s, RDFS.label, Literal(name)))
    g.add((s, RDFS.comment, Literal(comment)))


def write_core_ttl() -> Path:
    """Write the deterministic ``ontology/cds-core.ttl`` artifact; returns its path."""
    CORE_TTL_PATH.write_text(canonical_turtle(core_vocab_graph(), prefixes=CORE_PREFIXES))
    return CORE_TTL_PATH
