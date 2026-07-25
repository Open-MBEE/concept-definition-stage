"""Guard the third-party attribution against silent drift.

The redistribution decision (project lead, 2026-07-25) is to ship the verbatim canon *fully cited*.
That makes the attribution load-bearing: `NOTICE` + `THIRD_PARTY_LICENSES.md` must stay factually
in sync with the sources actually reproduced. These tests pin the invariants that drifted before
(SEBoK version, GtWR title) and, generically, that *every* reproduced source is documented.
"""

from __future__ import annotations

from pathlib import Path

from cds.core.licenses import GTWR_LICENSE
from cds.stages.concept_definition.seed import seed_sources

_ROOT = Path(__file__).resolve().parents[2]
_NOTICE = (_ROOT / "NOTICE").read_text()
_THIRD_PARTY = (_ROOT / "THIRD_PARTY_LICENSES.md").read_text()


def test_notice_points_at_the_third_party_manifest_and_apache() -> None:
    assert "THIRD_PARTY_LICENSES.md" in _NOTICE
    assert "Apache License" in _NOTICE


def test_every_reproduced_source_license_is_documented() -> None:
    # the drift-proof invariant: whatever seed sources declare as their license id (an SPDX id or a
    # LicenseRef) must appear verbatim in the manifest — add a reproduced source, document it.
    for src in seed_sources():
        assert src.license is not None, f"{src.id}: reproduced source declares no license"
        assert src.license in _THIRD_PARTY, f"{src.id}: license {src.license!r} not in manifest"


def test_sebok_version_matches_the_seed_not_a_stale_paraphrase() -> None:
    # regression: the manifest once claimed CC BY-NC-SA 4.0 while the seed pins 3.0.
    sebok = next(s for s in seed_sources() if "sebok" in s.id)
    assert sebok.license == "CC-BY-NC-SA-3.0"
    assert "CC-BY-NC-SA-3.0" in _THIRD_PARTY
    assert "by-nc-sa/4.0" not in _THIRD_PARTY  # the wrong-version URL must not creep back


def test_gtwr_is_named_the_guide_to_writing_requirements() -> None:
    # regression: the manifest once mislabeled GtWR as "Guide to the Roadmap".
    assert "Guide to Writing Requirements" in _THIRD_PARTY
    assert "Guide to the Roadmap" not in _THIRD_PARTY
    assert GTWR_LICENSE.ref in _THIRD_PARTY  # the LicenseRef is what the model tracks


def test_manifest_states_the_mixed_licensing_split() -> None:
    # the code/canon split must be explicit: Apache tooling vs. source-licensed embedded canon.
    assert "Apache-2.0" in _THIRD_PARTY
    assert "retains its upstream source license" in _THIRD_PARTY
