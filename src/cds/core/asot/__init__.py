"""ASoT: Authority / Source (boundary object) / Citation / Synthesis (PROV-O).

The stage-spanning provenance core: a reference is never a bare URI but a boundary object
carrying which authority it draws on and when it was retrieved/verified.
"""

from __future__ import annotations

from cds.core.asot.hashing import content_hash
from cds.core.asot.models import (
    Authority,
    AuthorityKind,
    CaptureTier,
    Citation,
    RetrievalStatus,
    Source,
    SourceType,
    Synthesis,
)
from cds.core.asot.rdf import to_graph
from cds.core.asot.registry import (
    INCOSE_AUTHORITY,
    SEBOK_AUTHORITY,
    register_pdf_source,
)
from cds.core.asot.snapshot import write_snapshot

__all__ = [
    "INCOSE_AUTHORITY",
    "SEBOK_AUTHORITY",
    "Authority",
    "AuthorityKind",
    "CaptureTier",
    "Citation",
    "RetrievalStatus",
    "Source",
    "SourceType",
    "Synthesis",
    "content_hash",
    "register_pdf_source",
    "to_graph",
    "write_snapshot",
]
