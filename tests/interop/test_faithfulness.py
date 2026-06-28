"""Faithfulness — the no-fabricated-canon guarantee, machine-verified against the actual sources.

Every `cds:Term` `skos:definition` must be *present in its cited source*. Normalization tolerates
the faithful authoring edits (lifted inline attributions / wiki-link artifacts, rejoined hard-wraps,
fixed PDF space-drops) by stripping parentheticals + all whitespace before the substring check —
while still catching any fabricated or altered text.

GtWR-cited terms check the **committed snapshot** (always runs). SEBoK-cited terms check the
operator-held REFERENCE-tier PDF (not vendored) — gated on `SEBOK_PDF_PATH` / the local copy, so it
runs for the operator and skips in CI. (The C1–C15 companion concepts are excluded — not `cds:Term`,
and their 2-column source defeats `pdftotext`; verified at author time by word-position extraction.)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from rdflib import RDF, URIRef

from cds.core.namespaces import CDS, SKOS
from cds.stages.concept_definition.build import build_concept_definition_graph
from cds.stages.concept_definition.seed import GTWR_SOURCE, SEBOK_SOURCE

_REPO = Path(__file__).resolve().parents[2]


def _flat(pdf: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True
    )
    return _norm(result.stdout)


def _norm(text: str) -> str:
    """Strip parentheticals + all whitespace + case — tolerant of the faithful authoring edits."""
    return re.sub(r"\s+", "", re.sub(r"\([^)]*\)", "", text)).lower()


def _sebok_pdf() -> Path | None:
    env = os.environ.get("SEBOK_PDF_PATH")
    if env and Path(env).exists():
        return Path(env)
    guess = _REPO.parent / "Guide_to_the_Systems_Engineering_Body_of_Knowledge_v2.14.pdf"
    return guess if guess.exists() else None


def _defined_terms_citing(source_id: str) -> list[URIRef]:
    g = build_concept_definition_graph()
    src = URIRef(source_id)
    terms = (t for t in g.subjects(CDS.cites, src) if isinstance(t, URIRef))
    return [t for t in terms if (t, RDF.type, CDS.Term) in g and (t, SKOS.definition, None) in g]


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_gtwr_term_definitions_are_faithful_to_the_committed_snapshot() -> None:
    g = build_concept_definition_graph()
    flat = _flat(_REPO / "sources" / str(GTWR_SOURCE.snapshot))
    terms = _defined_terms_citing(GTWR_SOURCE.id)
    assert terms, "expected GtWR-cited terms (need/requirement/integrated-set-of-needs)"
    for term in terms:
        definition = str(g.value(term, SKOS.definition))
        assert _norm(definition) in flat, f"definition not faithful to GtWR snapshot: {term}"


@pytest.mark.skipif(
    shutil.which("pdftotext") is None or _sebok_pdf() is None,
    reason="SEBoK PDF unavailable (REFERENCE tier — set SEBOK_PDF_PATH)",
)
def test_sebok_term_definitions_are_faithful_to_the_held_pdf() -> None:
    g = build_concept_definition_graph()
    pdf = _sebok_pdf()
    assert pdf is not None
    flat = _flat(pdf)
    terms = _defined_terms_citing(SEBOK_SOURCE.id)
    assert len(terms) >= 25, "expected the SEBoK glossary + in-prose terms"
    for term in terms:
        definition = str(g.value(term, SKOS.definition))
        assert _norm(definition) in flat, f"definition not faithful to the SEBoK PDF: {term}"
