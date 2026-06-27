"""Deterministic content hashing for ASoT boundary objects and content-addressed snapshots."""

from __future__ import annotations

import hashlib


def content_hash(data: bytes | str) -> str:
    """Return the SHA-256 of ``data`` as ``sha256:<hex>``.

    Strings are encoded as UTF-8. The algorithm prefix keeps the digest
    self-describing on the wire (and in the RDF ``cds:contentHash``).
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()
