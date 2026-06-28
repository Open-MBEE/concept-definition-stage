"""Slice 8 — the View layer: the license-keyed cite-vs-reproduce discipline + Typst rendering.

The heart of the standards-in-code resolution: M holds the verbatim, but the View only *emits* it
when the operator's text license is SEBoK-compatible — otherwise it cites the source and the text
never appears in the output.
"""

from __future__ import annotations

import shutil

import pytest
from typer.testing import CliRunner

from cds.core.cli import app
from cds.core.render.typst import typst_document
from cds.core.render.view import SchemeView, scheme_view
from cds.stages.concept_definition.build import build_concept_definition_graph

# a real verbatim SEBoK definition that must appear / disappear depending on the license
_SOI_VERBATIM = "The system whose life cycle is under consideration."


def _view(text_license: str) -> SchemeView:
    return scheme_view(
        build_concept_definition_graph(),
        title="Concept Definition Vocabulary",
        text_license=text_license,
    )


def test_view_embeds_verbatim_under_a_sebok_compatible_license() -> None:
    view = _view("CC-BY-NC-SA-4.0")  # the default — ShareAlike-compatible with SEBoK
    assert view.renders_restricted_canon
    soi = next(t for t in view.terms if t.iri.endswith("/system-of-interest"))
    assert soi.definition == _SOI_VERBATIM
    assert not soi.cite_only


def test_view_is_cite_only_under_a_permissive_license() -> None:
    view = _view("CC-BY-4.0")  # permissive — embedding NC text would be non-compliant
    assert not view.renders_restricted_canon
    soi = next(t for t in view.terms if t.iri.endswith("/system-of-interest"))
    assert soi.definition is None  # the text is withheld
    assert soi.cite_only
    assert soi.citation is not None  # but the authoritative source is still cited


def test_typst_output_reproduces_or_withholds_the_text_accordingly() -> None:
    embedded = typst_document(_view("CC-BY-NC-SA-4.0"))
    cite_only = typst_document(_view("CC-BY-4.0"))
    assert _SOI_VERBATIM in embedded  # verbatim present under the compatible license
    assert _SOI_VERBATIM not in cite_only  # and ABSENT under the permissive one
    assert "sebokwiki.org/wiki/System-of-Interest" in cite_only  # cited instead
    assert "ShareAlike" in embedded


def test_typst_source_is_deterministic() -> None:
    assert typst_document(_view("CC-BY-NC-SA-4.0")) == typst_document(_view("CC-BY-NC-SA-4.0"))


def test_every_term_appears_in_the_view() -> None:
    view = _view("CC-BY-NC-SA-4.0")
    assert len(view.terms) == 25  # the full glossary


def test_committed_typ_is_the_default_license_generation() -> None:
    from pathlib import Path

    committed = Path(__file__).resolve().parents[2] / "views" / "concept-definition.typ"
    assert committed.read_text() == typst_document(_view("CC-BY-NC-SA-4.0"))


@pytest.mark.skipif(shutil.which("typst") is None, reason="typst CLI not installed")
def test_cds_render_produces_a_pdf() -> None:
    result = CliRunner().invoke(app, ["render"])
    assert result.exit_code == 0, result.output
