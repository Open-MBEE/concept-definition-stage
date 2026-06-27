"""Authority registry (SEBoK + INCOSE) and PDF snapshot-source registration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cds.core.asot.models import AuthorityKind, CaptureTier, RetrievalStatus, SourceType
from cds.core.asot.registry import INCOSE_AUTHORITY, SEBOK_AUTHORITY, register_pdf_source


def test_sebok_is_curated_canon_and_incose_is_a_standard() -> None:
    assert SEBOK_AUTHORITY.kind is AuthorityKind.CURATED_CANON
    assert "SEBoK" in SEBOK_AUTHORITY.label
    assert INCOSE_AUTHORITY.kind is AuthorityKind.STANDARD


def test_register_pdf_source_snapshots_hashes_and_verifies(tmp_path: Path) -> None:
    pdf = tmp_path / "gtwr.pdf"
    pdf.write_bytes(b"%PDF-1.7 GtWR v4 summary")
    sources_root = tmp_path / "sources"

    src = register_pdf_source(
        id="https://w3id.org/cds/src/gtwr-v4-summary",
        authority=INCOSE_AUTHORITY,
        locator="INCOSE-TP-2010-006-04",
        pdf_path=pdf,
        sources_root=sources_root,
        verified_at=datetime(2026, 6, 27, tzinfo=UTC),
    )

    assert src.from_authority == INCOSE_AUTHORITY.id
    assert src.source_type is SourceType.PDF
    assert src.tier is CaptureTier.SNAPSHOT
    assert src.retrieval_status is RetrievalStatus.VERIFIED
    assert src.content_hash is not None and src.content_hash.startswith("sha256:")
    # the snapshot was actually written, content-addressed, under sources_root
    assert src.snapshot is not None
    assert (sources_root / src.snapshot).read_bytes() == pdf.read_bytes()
