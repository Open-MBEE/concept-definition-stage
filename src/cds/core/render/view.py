"""The View projection — the license-keyed M → V step (cite vs. reproduce).

This is where the standards-in-code discipline pays off. The committed M holds the verbatim SEBoK
definitions (the hallucination guard). The **View** is *restricted from emitting* that verbatim
unless the operator's ``text_license`` is compatible with the source's license — otherwise it
**cites the authoritative source** instead. The operator, not the tool, chooses the license and owns
whether the use qualifies.

For v0.1 the only restricted source is SEBoK (CC-BY-NC-SA); ``sebok_renderable()`` makes the call.
A report rendered *with* the verbatim inherits the restricted text license (ShareAlike); the default
(``CC-BY-NC-SA-4.0``) renders, a permissive license (e.g. ``CC-BY-4.0``) flips the whole View to
cite-only. The projection is a plain dataclass tree — Typst is just one downstream adapter over it.
"""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import RDF, Graph, URIRef
from rdflib.namespace import RDFS, SKOS

from cds.core.licenses import Attestation, TextLicense, sebok_renderable
from cds.core.namespaces import CDS

_GROUNDING_LABEL: dict[URIRef, str] = {
    RDFS.subClassOf: "subclass of",
    SKOS.exactMatch: "exact match",
    SKOS.closeMatch: "close match",
    SKOS.broadMatch: "broad match",
    SKOS.narrowMatch: "narrow match",
    SKOS.relatedMatch: "related match",
}


@dataclass(frozen=True)
class TermView:
    """One term as the View presents it — definition present only if the license permits."""

    iri: str
    pref_label: str
    alt_labels: tuple[str, ...]
    definition: str | None  # None when license-excluded (cite-only)
    cite_only: bool
    definition_source: str | None  # SEBoK's upstream attribution (the curation provenance)
    citation: str | None  # the authoritative source to cite (the grounding target)
    groundings: tuple[tuple[str, str], ...]  # (relation label, target IRI)
    sysml_anchor: str | None  # None == "canon-only" (no structural anchor)
    nrm_note: str | None


@dataclass(frozen=True)
class SchemeView:
    """The whole scheme as the View presents it under a chosen text license.

    ``attested_by`` is set when a noncommercial attestation unlocked the verbatim (D3a);
    in that case ``text_license`` is the PROPAGATED CC BY-NC-SA, whatever was requested —
    the derivative is correctly licensed at rest, never mislabeled permissive (D3b).
    """

    title: str
    text_license: str
    renders_restricted_canon: bool  # whether verbatim canon is embedded (vs cite-only)
    terms: tuple[TermView, ...]
    attested_by: str | None = None


_CITATION_PREFERENCE = (SKOS.exactMatch, SKOS.closeMatch, SKOS.broadMatch,
                        SKOS.narrowMatch, SKOS.relatedMatch, RDFS.subClassOf)


def _citation_for(g: Graph, term: URIRef) -> str | None:
    """The authoritative source to cite: the strongest grounding target available.

    Cite-only is the always-available floor (D4, live-QA 2026-08-02) — a term whose only
    grounding is a close/broad/related match still cites it, so a reader under a
    permissive license is pointed at the source, never left blind."""
    for pred in _CITATION_PREFERENCE:
        targets = sorted(str(o) for o in g.objects(term, pred))
        if targets:
            return targets[0]
    return None


def scheme_view(
    graph: Graph,
    *,
    title: str,
    text_license: str = TextLicense.CC_BY_NC_SA,
    attestation: Attestation | None = None,
) -> SchemeView:
    """Project the built scheme graph into a license-resolved View.

    When ``text_license`` is not SEBoK-compatible, the restricted verbatim definitions are withheld
    and the View carries citations only — never the text. A noncommercial ``attestation``
    (D3, live-QA 2026-08-02) unlocks the verbatim and COERCES the effective license to
    CC BY-NC-SA: the attester cleared NonCommercial by taking responsibility; the
    propagation clears ShareAlike by construction. Recording the attestation (who/when,
    hash-chained) is the caller's obligation — see ``cds render``.
    """
    renders = sebok_renderable(text_license)
    attested_by: str | None = None
    if attestation is not None:
        renders = True
        attested_by = attestation.attester
        text_license = TextLicense.CC_BY_NC_SA.value  # SA propagated, never mislabeled
    terms: list[TermView] = []
    for term in graph.subjects(RDF.type, CDS.Term):
        if not isinstance(term, URIRef):
            continue
        definition = graph.value(term, SKOS.definition)
        groundings = tuple(
            sorted(
                (label, str(o))
                for pred, label in _GROUNDING_LABEL.items()
                for o in graph.objects(term, pred)
            )
        )
        pref = graph.value(term, SKOS.prefLabel)
        source = graph.value(term, CDS.definitionSource)
        sysml = graph.value(term, CDS.sysmlConstruct)
        nrm = graph.value(term, CDS.nrmCanon)
        terms.append(
            TermView(
                iri=str(term),
                pref_label=str(pref) if pref is not None else str(term),
                alt_labels=tuple(sorted(str(a) for a in graph.objects(term, SKOS.altLabel))),
                definition=str(definition) if (definition is not None and renders) else None,
                cite_only=definition is not None and not renders,
                definition_source=str(source) if source is not None else None,
                citation=_citation_for(graph, term),
                groundings=groundings,
                sysml_anchor=str(sysml) if sysml is not None else None,
                nrm_note=str(nrm) if nrm is not None else None,
            )
        )
    terms.sort(key=lambda t: t.iri)  # deterministic order
    return SchemeView(
        title=title,
        text_license=str(text_license),
        renders_restricted_canon=renders,
        terms=tuple(terms),
        attested_by=attested_by,
    )
