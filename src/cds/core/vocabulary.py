"""The cds-core vocabulary — class/property declarations for the model.

This is the single Python source of truth for the ``cds:`` terms; ``ontology/cds-core.ttl`` is its
deterministic, committed build output (regenerate with ``write_core_ttl``). It formalizes the
classes the emitters have used as ``rdf:type`` since slice 4 (``cds:Authority`` subClassOf
``prov:Agent``, ``cds:Source`` of ``prov:Entity``, ``cds:Term`` of ``skos:Concept``), declares every
``cds:`` property **with its domain and range** (discipline + inference support), and folds in the
controlled-vocabulary SKOS schemes.

Each term also carries a **framework role** (``cds:frameworkRole``): ``cds:Required`` — needed for
a construction-order-compliant model (it appears in every built term's authority→source→cited chain)
— vs ``cds:Available`` — situational/optional (licensing, lifecycle, waivers, optional anchors,
tier-specific or escalation fields). Required vs available is a first-class, queryable distinction.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, URIRef

from cds import __version__
from cds.core.controlled import controlled_vocab_graph
from cds.core.namespaces import CDS, DCTERMS, PROV, SKOS
from cds.core.serialize import canonical_turtle

CORE_TTL_PATH = Path(__file__).resolve().parents[3] / "ontology" / "cds-core.ttl"
CORE_ONTOLOGY = URIRef("https://w3id.org/cds")

CORE_PREFIXES: dict[str, str] = {
    "cds": str(CDS),
    "dcterms": str(DCTERMS),
    "owl": str(OWL),
    "prov": str(PROV),
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "skos": str(SKOS),
    "xsd": str(XSD),
}

REQUIRED = CDS.Required  # necessary for framework compliance
AVAILABLE = CDS.Available  # situational / optional

# (local name, parent class or None, framework role)
_CLASSES: tuple[tuple[str, URIRef | None, URIRef], ...] = (
    ("Authority", PROV.Agent, REQUIRED),
    ("Source", PROV.Entity, REQUIRED),
    ("Term", SKOS.Concept, REQUIRED),
    ("RetrievalActivity", PROV.Activity, REQUIRED),
    ("VerificationActivity", PROV.Activity, REQUIRED),
    ("LifecycleModel", None, AVAILABLE),
    ("Waiver", None, AVAILABLE),
)

# (local name, domain, range or None, framework role) — value is a resource
_OBJECT_PROPS: tuple[tuple[str, URIRef, URIRef | None, URIRef], ...] = (
    ("authorityKind", CDS.Authority, SKOS.Concept, REQUIRED),
    ("captureTier", CDS.Source, SKOS.Concept, REQUIRED),
    ("cites", CDS.Term, CDS.Source, REQUIRED),
    ("addresses", CDS.Term, CDS.Term, AVAILABLE),
    ("license", CDS.Source, DCTERMS.LicenseDocument, AVAILABLE),
    ("codeLicense", CDS.LifecycleModel, DCTERMS.LicenseDocument, AVAILABLE),
    ("textLicense", CDS.LifecycleModel, DCTERMS.LicenseDocument, AVAILABLE),
    ("retrievalStatus", CDS.RetrievalActivity, SKOS.Concept, REQUIRED),
    ("sourceType", CDS.Source, SKOS.Concept, REQUIRED),
    ("sysmlConstruct", CDS.Term, None, AVAILABLE),
    ("verificationMethod", CDS.VerificationActivity, SKOS.Concept, REQUIRED),
    ("wasVerifiedBy", CDS.Source, CDS.VerificationActivity, REQUIRED),
    ("waivesFocus", CDS.Waiver, None, AVAILABLE),
)

# (local name, domain, xsd range, framework role) — value is a literal
_DATA_PROPS: tuple[tuple[str, URIRef, URIRef, URIRef], ...] = (
    ("contentHash", CDS.Source, XSD.string, REQUIRED),
    ("locator", CDS.Source, XSD.string, REQUIRED),
    ("snapshot", CDS.Source, XSD.string, AVAILABLE),
    ("retrievalIssue", CDS.RetrievalActivity, XSD.string, AVAILABLE),
    ("verificationNote", CDS.VerificationActivity, XSD.string, AVAILABLE),
    ("nrmCanon", CDS.Term, XSD.string, AVAILABLE),
    ("definitionSource", CDS.Term, XSD.string, AVAILABLE),
    ("stage", CDS.LifecycleModel, XSD.string, AVAILABLE),
    ("licenseText", DCTERMS.LicenseDocument, XSD.string, AVAILABLE),
    ("reproducible", DCTERMS.LicenseDocument, XSD.boolean, AVAILABLE),
    ("waivesRule", CDS.Waiver, XSD.string, AVAILABLE),
    ("waiverReason", CDS.Waiver, XSD.string, AVAILABLE),
)

# rdfs:comment per term — kept out of the tuples to stay readable
_COMMENTS: dict[str, str] = {
    "Authority": "An entity holding authoritative content (a source's holder).",
    "Source": "A boundary object: a specific artifact held by an authority.",
    "Term": "A Concept Definition reference-vocabulary term.",
    "RetrievalActivity": "The act of retrieving (capturing) a source.",
    "VerificationActivity": "The act of verifying a source's content.",
    "LifecycleModel": "A system modeled across its life cycle, from Concept Definition.",
    "Waiver": "An append-only, conscious acceptance of a non-Violation verify finding.",
    "authorityKind": "The controlled kind of an authority.",
    "captureTier": "How faithfully a source is captured (reference / snapshot).",
    "cites": "Links a term to a boundary-object source it draws on.",
    "addresses": "A concept addresses the problem / threat / opportunity it is defined for (GtWR).",
    "license": "The tracked SPDX license of a referenced asset (tracked, not enforced).",
    "codeLicense": "The code license declared by a lifecycle model.",
    "textLicense": "The text license of a lifecycle model (gates restricted-canon rendering).",
    "retrievalStatus": "The construction-order state of a retrieval (pending/provided/verified).",
    "sourceType": "The controlled kind of artifact a source points at.",
    "sysmlConstruct": "The SysML v2 construct a term structurally anchors to.",
    "verificationMethod": "How a source's content was confirmed (checksum/visual/machine).",
    "wasVerifiedBy": "Links a source to a verification activity performed over it.",
    "waivesFocus": "The specific focus node a waiver applies to.",
    "contentHash": "The content hash (e.g. sha256:...) of a captured source.",
    "locator": "The locator (URI or document number) of a source.",
    "snapshot": "The content-addressed local snapshot filename of a captured source.",
    "retrievalIssue": "The retrieval-escalation issue URL for a not-yet-secured source.",
    "verificationNote": "Prose note on how a verification was performed.",
    "nrmCanon": "An INCOSE NRM / GtWR grounding note on a term.",
    "definitionSource": "The upstream attribution SEBoK records for a term's definition.",
    "stage": "The life-cycle stage label of a lifecycle model.",
    "licenseText": "The verbatim terms of a custom license.",
    "reproducible": "Whether a custom license permits reproduction/redistribution.",
    "waivesRule": "The verify rule (check name) a waiver accepts.",
    "waiverReason": "Why a waiver was consciously accepted.",
}


def required_terms() -> set[URIRef]:
    """The ``cds:`` terms necessary for a framework-compliant model (role ``cds:Required``)."""
    names = [name for name, _p, role in _CLASSES if role == REQUIRED]
    names += [name for name, _d, _r, role in _OBJECT_PROPS if role == REQUIRED]
    names += [name for name, _d, _r, role in _DATA_PROPS if role == REQUIRED]
    return {CDS[name] for name in names}


def core_vocab_graph() -> Graph:
    """Build the in-memory cds-core vocabulary (classes + properties + roles + control schemes)."""
    g = Graph()
    g.add((CORE_ONTOLOGY, RDF.type, OWL.Ontology))
    g.add((CORE_ONTOLOGY, RDFS.label, Literal("cds core vocabulary")))
    g.add((CORE_ONTOLOGY, OWL.versionInfo, Literal(__version__)))
    _declare_framework_roles(g)

    for name, parent, role in _CLASSES:
        s = CDS[name]
        g.add((s, RDF.type, RDFS.Class))
        g.add((s, RDF.type, OWL.Class))
        g.add((s, RDFS.label, Literal(name)))
        g.add((s, RDFS.comment, Literal(_COMMENTS[name])))
        g.add((s, CDS.frameworkRole, role))
        if parent is not None:
            g.add((s, RDFS.subClassOf, parent))

    for name, domain, range_, role in _OBJECT_PROPS:
        _declare_property(g, name, OWL.ObjectProperty, domain, range_, role)
    for name, domain, range_, role in _DATA_PROPS:
        _declare_property(g, name, OWL.DatatypeProperty, domain, range_, role)

    g += controlled_vocab_graph()
    return g


def _declare_framework_roles(g: Graph) -> None:
    g.add((CDS.frameworkRole, RDF.type, RDF.Property))
    g.add((CDS.frameworkRole, RDF.type, OWL.AnnotationProperty))
    g.add((CDS.frameworkRole, RDFS.label, Literal("frameworkRole")))
    role_comment = "Whether a term is Required for compliance or Available (optional)."
    g.add((CDS.frameworkRole, RDFS.comment, Literal(role_comment)))
    g.add((CDS.FrameworkRole, RDF.type, SKOS.ConceptScheme))
    for role, label in ((REQUIRED, "required"), (AVAILABLE, "available")):
        g.add((role, RDF.type, SKOS.Concept))
        g.add((role, SKOS.inScheme, CDS.FrameworkRole))
        g.add((role, SKOS.prefLabel, Literal(label)))


def _declare_property(
    g: Graph,
    name: str,
    kind: URIRef,
    domain: URIRef,
    range_: URIRef | None,
    role: URIRef,
) -> None:
    s = CDS[name]
    g.add((s, RDF.type, RDF.Property))
    g.add((s, RDF.type, kind))
    g.add((s, RDFS.label, Literal(name)))
    g.add((s, RDFS.comment, Literal(_COMMENTS[name])))
    g.add((s, RDFS.domain, domain))
    g.add((s, CDS.frameworkRole, role))
    if range_ is not None:
        g.add((s, RDFS.range, range_))


def write_core_ttl() -> Path:
    """Write the deterministic ``ontology/cds-core.ttl`` artifact; returns its path."""
    CORE_TTL_PATH.write_text(canonical_turtle(core_vocab_graph(), prefixes=CORE_PREFIXES))
    return CORE_TTL_PATH
