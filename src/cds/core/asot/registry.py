"""The first registered authorities and a helper to register held PDFs as snapshot sources.

SEBoK and INCOSE are the v0.1 authorities. ``register_pdf_source`` snapshots a held PDF
(content-addressed) and builds a verified ``SNAPSHOT``-tier boundary object — the capability
used to register the GtWR summary (and, externally, the SEBoK v2.14 PDF) during capture.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from cds.core.asot.hashing import content_hash
from cds.core.asot.models import (
    Authority,
    AuthorityKind,
    CaptureTier,
    RetrievalStatus,
    Source,
    SourceType,
)
from cds.core.asot.snapshot import write_snapshot

SEBOK_AUTHORITY = Authority(
    id="https://w3id.org/cds/auth/sebok",
    kind=AuthorityKind.CURATED_CANON,
    label="SEBoK (Guide to the Systems Engineering Body of Knowledge)",
)

INCOSE_AUTHORITY = Authority(
    id="https://w3id.org/cds/auth/incose",
    kind=AuthorityKind.STANDARD,
    label="INCOSE (International Council on Systems Engineering)",
)


def register_pdf_source(
    *,
    id: str,
    authority: Authority,
    locator: str,
    pdf_path: Path,
    sources_root: Path,
    verified_at: datetime,
) -> Source:
    """Snapshot a held PDF and return a verified ``SNAPSHOT``-tier boundary object."""
    data = pdf_path.read_bytes()
    snapshot = write_snapshot(data, root=sources_root, suffix=".pdf")
    return Source(
        id=id,
        from_authority=authority.id,
        locator=locator,
        source_type=SourceType.PDF,
        tier=CaptureTier.SNAPSHOT,
        content_hash=content_hash(data),
        snapshot=str(snapshot),
        retrieved_at=verified_at,
        verified_at=verified_at,
        retrieval_status=RetrievalStatus.VERIFIED,
    )
