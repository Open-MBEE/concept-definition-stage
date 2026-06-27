"""ASoT content hashing — deterministic, prefixed digests for boundary objects."""

from __future__ import annotations

import hashlib

from cds.core.asot.hashing import content_hash


def test_content_hash_is_deterministic_prefixed_sha256() -> None:
    data = b"The system whose life cycle is under consideration."
    h = content_hash(data)
    # deterministic
    assert h == content_hash(data)
    # multibase-ish prefix so the algorithm is explicit on the wire
    assert h.startswith("sha256:")
    # is the real sha256
    assert h == "sha256:" + hashlib.sha256(data).hexdigest()


def test_content_hash_accepts_str_as_utf8() -> None:
    text = "agreed-to expectation"
    assert content_hash(text) == content_hash(text.encode("utf-8"))
