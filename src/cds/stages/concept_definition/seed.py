"""v0.1 seed data: the registered authorities and the captured GtWR boundary object.

SEBoK and INCOSE are the v0.1 authorities. The GtWR v4 summary (INCOSE-TP-2010-006-04) is
held as a verified ``SNAPSHOT`` source — its PDF is content-addressed under ``sources/`` and
its integrity is checked against ``content_hash`` in the tests. Timestamps are stable inputs
(capture date), never build-time ``now()``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from cds.core.asot.models import (
    Authority,
    CaptureTier,
    RetrievalStatus,
    Source,
    SourceType,
    Verification,
    VerificationMethod,
)
from cds.core.asot.registry import INCOSE_AUTHORITY, SEBOK_AUTHORITY
from cds.core.licenses import GTWR_LICENSE, CustomLicense

_CAPTURED_AT = datetime(2026, 6, 27, tzinfo=UTC)
_GTWR_SHA256 = "0bf5918db034757fb63fb81a677263ebe36323eee95e51fbd0197aecdd574176"
_SEBOK_SHA256 = "251668f0ed4eca5a7c36755c6c56a07d663ef8a2bd66addd41e595eabcf0dce2"

# SEBoK v2.14 — the verbatim source of record for the glossary terms. Registered as a REFERENCE-tier
# source: public curated canon (the tiering rule keeps public canon to hash + locator, NOT vendored)
# and BY-NC-SA — vendoring the whole 14.7 MB work into a public repo would be redistribution. The
# content hash pins the version; the verbatim *definitions* (a small excerpt) live in the built M as
# the hallucination guard — a different question (Delta D2). The operator holds the PDF.
SEBOK_SOURCE = Source(
    id="https://w3id.org/cds/src/sebok-v2-14",
    from_authority=SEBOK_AUTHORITY.id,
    locator="https://sebokwiki.org/wiki/Guide_to_the_Systems_Engineering_Body_of_Knowledge_(SEBoK)",
    source_type=SourceType.PDF,
    tier=CaptureTier.REFERENCE,
    content_hash=f"sha256:{_SEBOK_SHA256}",
    license="CC-BY-NC-SA-3.0",
    retrieved_at=_CAPTURED_AT,
    retrieval_status=RetrievalStatus.VERIFIED,
    verifications=[
        Verification(
            method=VerificationMethod.CHECKSUM,
            verified_at=_CAPTURED_AT,
            note="sha256 of the operator-held SEBoK v2.14 PDF; reference tier, not vendored",
        )
    ],
)

GTWR_SOURCE = Source(
    id="https://w3id.org/cds/src/incose-gtwr-v4-summary",
    from_authority=INCOSE_AUTHORITY.id,
    locator="INCOSE-TP-2010-006-04",
    source_type=SourceType.PDF,
    tier=CaptureTier.SNAPSHOT,
    content_hash=f"sha256:{_GTWR_SHA256}",
    snapshot=f"{_GTWR_SHA256}.pdf",
    license=GTWR_LICENSE.ref,
    retrieved_at=_CAPTURED_AT,
    retrieval_status=RetrievalStatus.VERIFIED,
    verifications=[
        Verification(
            method=VerificationMethod.CHECKSUM,
            verified_at=_CAPTURED_AT,
            note="content-addressed snapshot; sha256 matches the held file",
        )
    ],
)


def seed_authorities() -> list[Authority]:
    """The authorities registered for v0.1."""
    return [SEBOK_AUTHORITY, INCOSE_AUTHORITY]


def seed_sources() -> list[Source]:
    """The boundary objects held/registered for v0.1."""
    return [GTWR_SOURCE, SEBOK_SOURCE]


def seed_licenses() -> list[CustomLicense]:
    """Custom (LicenseRef-) licenses referenced by the seed, for self-describing emission."""
    return [GTWR_LICENSE]
