"""REQ-K5.4 — a term citing a non-'verified' source is held out of commit. (P2, red)"""
from cds.app.commit_gate import filter_held_out  # noqa: F401  (green as of P2-b)


def test_held_out_helper_exists() -> None:
    assert callable(filter_held_out)
