"""ASoT Pydantic models — tiered-capture write-scope guardrails."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from cds.core.asot.models import CaptureTier, Source, SourceType

_T = datetime(2026, 6, 27, 17, 22, tzinfo=timezone.utc)


def _ref_kwargs(**over: object) -> dict[str, object]:
    base: dict[str, object] = dict(
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
