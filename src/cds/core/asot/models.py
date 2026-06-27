"""ASoT domain models (Pydantic).

Authority / Source (boundary object) / Citation / Synthesis. These Pydantic models are
the tool's **write-scope guardrails** (the C layer): they constrain what the CLI may write,
independent of the RDF SHACL layer. Models grow as tests drive them.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, model_validator


class SourceType(str, Enum):
    """The kind of artifact a boundary object points at."""

    WEB_PAGE = "web-page"
    PDF = "pdf"
    TRANSCRIPT = "transcript"
    NOTES = "notes"
    IMAGE = "image"


class CaptureTier(str, Enum):
    """How faithfully a source is captured.

    ``REFERENCE`` — not vendored: locator + content hash + timestamps only (e.g. live SEBoK
    wiki, paywalled standards we don't hold).
    ``SNAPSHOT`` — a content-addressed local copy is held (e.g. the GtWR/SEBoK PDFs, and
    private/ephemeral sources like transcripts and meeting notes).
    """

    REFERENCE = "reference"
    SNAPSHOT = "snapshot"


class Source(BaseModel):
    """A boundary object: a specific artifact held by an authority, with provenance.

    Tiered-capture invariant (enforced here, not in SHACL): a ``REFERENCE`` source is never
    vendored (no snapshot); a ``SNAPSHOT`` source must hold a content-addressed copy.
    """

    id: str
    from_authority: str
    locator: str
    source_type: SourceType
    tier: CaptureTier
    content_hash: str | None = None
    snapshot: str | None = None
    retrieved_at: datetime | None = None
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def _enforce_tier(self) -> Source:
        if self.tier is CaptureTier.REFERENCE and self.snapshot is not None:
            raise ValueError(
                "REFERENCE-tier source is not vendored — it must not carry a snapshot"
            )
        if self.tier is CaptureTier.SNAPSHOT and self.snapshot is None:
            raise ValueError("SNAPSHOT-tier source must hold a content-addressed snapshot")
        return self
