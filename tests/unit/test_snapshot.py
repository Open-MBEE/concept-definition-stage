"""Content-addressed snapshot store for SNAPSHOT-tier sources."""

from __future__ import annotations

from pathlib import Path

from cds.core.asot.hashing import content_hash
from cds.core.asot.snapshot import write_snapshot


def test_write_snapshot_is_content_addressed(tmp_path: Path) -> None:
    data = b"%PDF-1.7 held canon"
    rel = write_snapshot(data, root=tmp_path, suffix=".pdf")
    digest = content_hash(data).split(":", 1)[1]
    # path encodes the digest, and the bytes are written
    assert digest in rel.name
    assert (tmp_path / rel).read_bytes() == data


def test_write_snapshot_is_idempotent(tmp_path: Path) -> None:
    data = b"agreed-to obligation"
    first = write_snapshot(data, root=tmp_path)
    second = write_snapshot(data, root=tmp_path)
    assert first == second
