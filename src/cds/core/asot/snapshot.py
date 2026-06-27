"""Content-addressed snapshot store.

SNAPSHOT-tier sources (held PDFs, transcripts, notes) are written to ``sources/`` under a
content-addressed name so the same content always lands at the same path. NC-source verbatim
snapshots are gitignored (Redistribution policy); this module only handles the bytes.
"""

from __future__ import annotations

from pathlib import Path

from cds.core.asot.hashing import content_hash


def write_snapshot(data: bytes, *, root: Path, suffix: str = "") -> Path:
    """Write ``data`` to a content-addressed file under ``root`` and return its relative path.

    Idempotent: identical content yields the same path and is not rewritten.
    """
    digest = content_hash(data).split(":", 1)[1]
    rel = Path(f"{digest}{suffix}")
    target = root / rel
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return rel
