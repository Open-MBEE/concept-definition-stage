"""REQ-K5.4 — a term citing a non-'verified' source is held out of commit. (P2, red)"""
from cds.app.commit_gate import (  # type: ignore[attr-defined]  # noqa: F401  (red until P2)
    filter_held_out,
)


def test_held_out_helper_exists() -> None:
    assert callable(filter_held_out)
