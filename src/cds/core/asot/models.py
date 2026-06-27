"""ASoT domain models (Pydantic).

Authority / Source (boundary object) / Citation / Synthesis. These Pydantic models are
the tool's **write-scope guardrails** (the C layer): they constrain what the CLI may write,
independent of the RDF SHACL layer. Models grow as tests drive them.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, model_validator


class AuthorityKind(StrEnum):
    """The kind of authority that holds content (aligns to the stakeholder cast)."""

    CURATED_CANON = "curated-canon"  # SEBoK
    STANDARD = "standard"  # ISO / INCOSE
    SPONSOR = "sponsor"
    CONSULTED_STAKEHOLDER = "consulted-stakeholder"
    DOMAIN_EXPERT = "domain-expert"
    REGULATORY = "regulatory"
    INFORMAL = "informal"


class SourceType(StrEnum):
    """The kind of artifact a boundary object points at."""

    WEB_PAGE = "web-page"
    PDF = "pdf"
    TRANSCRIPT = "transcript"
    NOTES = "notes"
    IMAGE = "image"


class CaptureTier(StrEnum):
    """How faithfully a source is captured.

    ``REFERENCE`` — not vendored: locator + content hash + timestamps only (e.g. live SEBoK
    wiki, paywalled standards we don't hold).
    ``SNAPSHOT`` — a content-addressed local copy is held (e.g. the GtWR/SEBoK PDFs, and
    private/ephemeral sources like transcripts and meeting notes).
    """

    REFERENCE = "reference"
    SNAPSHOT = "snapshot"


class RetrievalStatus(StrEnum):
    """Construction-order stages 2-3: a source must reach ``VERIFIED`` before a term builds."""

    PENDING = "pending"
    PROVIDED = "provided"
    VERIFIED = "verified"


class Authority(BaseModel):
    """An entity holding authoritative content (``prov:Agent``)."""

    id: str
    kind: AuthorityKind
    label: str


class Source(BaseModel):
    """A boundary object: a specific artifact held by an authority, with provenance.

    Invariants (enforced here, not in SHACL):

    * Tier — a ``REFERENCE`` source is never vendored (no snapshot); a ``SNAPSHOT`` source
      must hold a content-addressed copy.
    * Retrieval — ``PROVIDED``/``VERIFIED`` require a ``content_hash``; ``VERIFIED`` also
      requires a ``verified_at`` timestamp.
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
    retrieval_status: RetrievalStatus = RetrievalStatus.PENDING
    retrieval_issue: str | None = None

    @model_validator(mode="after")
    def _enforce_invariants(self) -> Source:
        if self.tier is CaptureTier.REFERENCE and self.snapshot is not None:
            raise ValueError(
                "REFERENCE-tier source is not vendored — it must not carry a snapshot"
            )
        if self.tier is CaptureTier.SNAPSHOT and self.snapshot is None:
            raise ValueError("SNAPSHOT-tier source must hold a content-addressed snapshot")
        needs_hash = self.retrieval_status in (RetrievalStatus.PROVIDED, RetrievalStatus.VERIFIED)
        if needs_hash and self.content_hash is None:
            raise ValueError(f"{self.retrieval_status.value} source requires a content_hash")
        if self.retrieval_status is RetrievalStatus.VERIFIED and self.verified_at is None:
            raise ValueError("verified source requires a verified_at timestamp")
        return self


class Citation(BaseModel):
    """A reified link ``concept -> cds:cites -> Source``, optionally carrying a verbatim quote.

    The quote is held locally for verification; for NC sources it is not redistributed.
    """

    id: str
    concept: str
    source: str
    quote: str | None = None


# NOTE: ``cds:Synthesis`` is **reserved** for the concept-definition artifact (the integrated
# set of needs synthesized from divergent stakeholder/sponsor/expert inputs) — a v0.2 thing.
# The v0.1 vocabulary is a provenance-tracked ``skos:ConceptScheme`` (reference canon), not a
# synthesis, so no Synthesis model is defined here yet.
