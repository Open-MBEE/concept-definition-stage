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
    return [GTWR_SOURCE]


def seed_licenses() -> list[CustomLicense]:
    """Custom (LicenseRef-) licenses referenced by the seed, for self-describing emission."""
    return [GTWR_LICENSE]
