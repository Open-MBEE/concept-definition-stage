"""D3+D4 (live-QA 2026-08-02 @ bb2d4a7): licensing that is never a dead-end.

The guiding principle: "you cannot follow engineering best practices if you cannot see
them ... these are not documents at all, they are computational models." Two prongs make
verbatim SEBoK usable lawfully instead of blocked:

(a) a **noncommercial attestation** — an explicit, recorded, responsibility-taking act
    that unlocks verbatim rendering (clears the NC prong); and
(b) **license propagation** — an attested or verbatim rendering carries CC BY-NC-SA at
    rest, automatically, so the derivative is correctly licensed rather than mislabeled
    permissive (clears the ShareAlike prong).

Cite-only-with-grounding stays the always-available floor (an engineer is never fully
blind), and the anti-fabrication dead-end in the AICC loop stays orthogonal to license
logic (prong c).
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cds.core.cli import app
from cds.core.licenses import (
    NONCOMMERCIAL_ATTESTATION_STATEMENT,
    Attestation,
    TextLicense,
)
from cds.core.render.view import scheme_view
from cds.stages.concept_definition.build import build_concept_definition_graph

runner = CliRunner()

_ATTESTER = "https://example.org/people/z"


def test_nc_sa_license_renders_every_definition_verbatim() -> None:
    """(d) regression, lifted from the QA run's verified harness: 36/36 verbatim."""
    view = scheme_view(build_concept_definition_graph(), title="CD",
                       text_license=TextLicense.CC_BY_NC_SA)
    assert view.renders_restricted_canon
    with_def = [t for t in view.terms if t.definition is not None]
    assert len(with_def) == len(view.terms) > 0
    assert not any(t.cite_only for t in view.terms)


def test_permissive_license_is_cite_only_but_never_blind() -> None:
    """(d): the floor — no verbatim, but term + citation + structure always render."""
    view = scheme_view(build_concept_definition_graph(), title="CD",
                       text_license=TextLicense.CC_BY)
    assert not view.renders_restricted_canon
    assert all(t.definition is None for t in view.terms)
    cite_only = [t for t in view.terms if t.cite_only]
    assert len(cite_only) == len(view.terms)
    assert all(t.citation for t in cite_only)  # never fully blind


def test_attestation_unlocks_verbatim_and_propagates_the_license() -> None:
    """(a)+(b): attesting noncommercial use renders verbatim, and the view's license
    becomes CC BY-NC-SA regardless of what was requested — abide by construction."""
    att = Attestation(attester=_ATTESTER, context="ABET senior design project")
    view = scheme_view(build_concept_definition_graph(), title="CD",
                       text_license=TextLicense.CC_BY, attestation=att)
    assert view.renders_restricted_canon
    assert view.text_license == TextLicense.CC_BY_NC_SA.value  # SA propagated
    assert view.attested_by == _ATTESTER
    assert all(t.definition is not None for t in view.terms)


def test_attested_typst_document_carries_the_propagated_license() -> None:
    from cds.core.render.typst import typst_document

    att = Attestation(attester=_ATTESTER, context="classroom use")
    view = scheme_view(build_concept_definition_graph(), title="CD",
                       text_license=TextLicense.CC_BY, attestation=att)
    doc = typst_document(view)
    assert "CC-BY-NC-SA-4.0" in doc
    assert _ATTESTER in doc  # the responsibility-taker is on the artifact


def test_render_cli_attestation_records_the_legal_assertion(tmp_path: Path,
                                                           monkeypatch: object) -> None:
    """The attestation is audited like an approver act: who, context, statement,
    hash-chained so it cannot be quietly rewritten."""
    import os

    from cds.core.init import init_project
    from cds.mcp.provenance import AuditLog

    init_project(tmp_path, name="demo")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, [
            "render", "--text-license", "CC-BY-4.0", "--skip-pdf",
            "--attest-noncommercial", _ATTESTER,
            "--attest-context", "ABET senior design project",
        ])
        assert result.exit_code == 0, result.output
        assert "verbatim" in result.output.lower()
        typ = tmp_path / "views" / "concept-definition.typ"
        assert "CC-BY-NC-SA-4.0" in typ.read_text(encoding="utf-8")

        ledger = AuditLog(tmp_path / "views" / "attestations.jsonl")
        assert ledger.verify_chain()
        events = [e["event"] for e in ledger.replay()]
        assert events and events[-1]["action"] == "attest-noncommercial"
        assert events[-1]["attester"] == _ATTESTER
        assert events[-1]["statement"] == NONCOMMERCIAL_ATTESTATION_STATEMENT
    finally:
        os.chdir(cwd)


def test_unattested_permissive_render_stays_cite_only(tmp_path: Path) -> None:
    import os

    from cds.core.init import init_project

    init_project(tmp_path, name="demo")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["render", "--text-license", "CC-BY-4.0",
                                     "--skip-pdf"])
        assert result.exit_code == 0, result.output
        assert "cite-only" in result.output.lower()
        typ = (tmp_path / "views" / "concept-definition.typ").read_text(encoding="utf-8")
        assert "The system whose life cycle is under consideration." not in typ
    finally:
        os.chdir(cwd)


def test_attestation_statement_is_plain_and_takes_responsibility() -> None:
    text = NONCOMMERCIAL_ATTESTATION_STATEMENT
    assert "noncommercial" in text.lower()
    assert "responsib" in text.lower()  # the user owns the call
    assert "—" not in text


def test_k5_dead_end_stays_orthogonal_to_licensing() -> None:
    """(c): the anti-fabrication guard must not consult license or attestation state."""
    import inspect

    from cds.facilitator import aicc, decode

    for mod in (aicc, decode):
        source = inspect.getsource(mod)
        assert "attest" not in source.lower()
        assert "text_license" not in source
