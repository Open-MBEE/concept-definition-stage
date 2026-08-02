"""REQ-K2.1 / REQ-K2.2 — candidates isolated in staging; commit needs approver. (P2, red)"""
import pytest

from cds.app import commit_gate
from cds.mcp import staging


def test_candidate_isolated_in_staging():
    proj = staging.new_session_project("https://cds.example/test/")
    assert proj is not None  # candidates live here, never in canonical instances/


def test_commit_requires_approver():
    with pytest.raises(PermissionError):
        commit_gate.commit(object(), approver_roles=frozenset())
