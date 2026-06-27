"""ASoT Pydantic models — tiered-capture write-scope guardrails."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from cds.core.asot.models import (
    Authority,
    AuthorityKind,
    CaptureTier,
    Citation,
    RetrievalStatus,
    Source,
    SourceType,
    Verification,
    VerificationMethod,
)

_T = datetime(2026, 6, 27, 17, 22, tzinfo=UTC)


def _ref_kwargs(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = dict(
        id="https://w3id.org/cds/src/sebok-soi",
        from_authority="https://w3id.org/cds/auth/sebok",
        locator="https://sebokwiki.org/wiki/System-of-Interest_(glossary)",
        source_type=SourceType.WEB_PAGE,
        tier=CaptureTier.REFERENCE,
        content_hash="sha256:abc",
        retrieved_at=_T,
    )
    base.update(over)
    return base


def test_reference_tier_source_is_not_vendored() -> None:
    s = Source(**_ref_kwargs())
    assert s.snapshot is None


def test_reference_tier_rejects_a_snapshot() -> None:
    with pytest.raises(ValidationError, match="REFERENCE"):
        Source(**_ref_kwargs(snapshot="sources/sebok-soi.html"))


def test_snapshot_tier_requires_a_held_copy() -> None:
    with pytest.raises(ValidationError, match="SNAPSHOT"):
        Source(**_ref_kwargs(tier=CaptureTier.SNAPSHOT, snapshot=None))


def test_snapshot_tier_with_copy_is_valid() -> None:
    s = Source(
        **_ref_kwargs(
            tier=CaptureTier.SNAPSHOT,
            source_type=SourceType.PDF,
            snapshot="sources/gtwr-v4.pdf",
        )
    )
    assert s.tier is CaptureTier.SNAPSHOT
    assert s.snapshot == "sources/gtwr-v4.pdf"


# --- retrieval state machine (construction-order stages 2-3) ---


def test_source_defaults_to_pending() -> None:
    assert Source(**_ref_kwargs()).retrieval_status is RetrievalStatus.PENDING


def test_provided_source_requires_content_hash() -> None:
    with pytest.raises(ValidationError, match="content_hash"):
        Source(**_ref_kwargs(content_hash=None, retrieval_status=RetrievalStatus.PROVIDED))


def test_verified_source_requires_a_verification() -> None:
    with pytest.raises(ValidationError, match="verification"):
        Source(**_ref_kwargs(retrieval_status=RetrievalStatus.VERIFIED))


def test_verified_source_with_a_verification_is_valid() -> None:
    s = Source(
        **_ref_kwargs(
            retrieval_status=RetrievalStatus.VERIFIED,
            verifications=[
                Verification(
                    method=VerificationMethod.CHECKSUM,
                    verified_at=_T,
                    note="sha256 content-addressed match",
                )
            ],
        )
    )
    assert s.retrieval_status is RetrievalStatus.VERIFIED
    assert s.verifications[0].method is VerificationMethod.CHECKSUM


def test_a_retrieval_can_be_reverified_without_recapture() -> None:
    # one capture, several verifications over time (e.g. a later re-check)
    s = Source(
        **_ref_kwargs(
            retrieval_status=RetrievalStatus.VERIFIED,
            verifications=[
                Verification(method=VerificationMethod.CHECKSUM, verified_at=_T),
                Verification(
                    method=VerificationMethod.MACHINE_VISUAL,
                    verified_at=_T,
                    note="LLM screenshot parse re-confirmed the rendered text",
                ),
            ],
        )
    )
    assert len(s.verifications) == 2
    assert s.verifications[1].method is VerificationMethod.MACHINE_VISUAL


# --- Authority / Citation / Synthesis ---


def test_authority_carries_kind_and_label() -> None:
    a = Authority(
        id="https://w3id.org/cds/auth/sebok",
        kind=AuthorityKind.CURATED_CANON,
        label="SEBoK",
    )
    assert a.kind is AuthorityKind.CURATED_CANON
    assert a.label == "SEBoK"


def test_citation_links_concept_to_source_with_optional_quote() -> None:
    c = Citation(
        id="https://w3id.org/cds/cite/soi-1",
        concept="https://w3id.org/cds/term/system-of-interest",
        source="https://w3id.org/cds/src/sebok-soi",
        quote="The system whose life cycle is under consideration.",
    )
    assert c.source.endswith("sebok-soi")
    assert c.quote is not None and c.quote.startswith("The system")
