"""v0.1 seed: registered authorities + the captured GtWR boundary object."""

from __future__ import annotations

from pathlib import Path

from cds.core.asot.hashing import content_hash
from cds.core.asot.models import RetrievalStatus
from cds.core.asot.registry import INCOSE_AUTHORITY
from cds.core.licenses import GTWR_LICENSE
from cds.stages.concept_definition.seed import (
    GTWR_SOURCE,
    seed_authorities,
    seed_licenses,
    seed_sources,
)

_GTWR_HASH = "sha256:0bf5918db034757fb63fb81a677263ebe36323eee95e51fbd0197aecdd574176"


def test_gtwr_is_a_verified_incose_snapshot() -> None:
    assert GTWR_SOURCE.from_authority == INCOSE_AUTHORITY.id
    assert GTWR_SOURCE.retrieval_status is RetrievalStatus.VERIFIED
    assert GTWR_SOURCE.content_hash == _GTWR_HASH


def test_gtwr_snapshot_file_matches_its_recorded_hash() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assert GTWR_SOURCE.snapshot is not None
    snap = repo_root / "sources" / GTWR_SOURCE.snapshot
    assert snap.exists(), f"GtWR snapshot missing: {snap}"
    assert content_hash(snap.read_bytes()) == GTWR_SOURCE.content_hash


def test_seed_registers_sebok_and_incose_and_the_gtwr_source() -> None:
    auth_ids = {a.id for a in seed_authorities()}
    assert "https://w3id.org/cds/auth/sebok" in auth_ids
    assert "https://w3id.org/cds/auth/incose" in auth_ids
    assert GTWR_SOURCE in seed_sources()


def test_gtwr_source_carries_its_custom_license_reference() -> None:
    assert GTWR_SOURCE.license == GTWR_LICENSE.ref
    assert GTWR_LICENSE in seed_licenses()
