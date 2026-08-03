"""Candidate -> canonical commit gate (K2). Approver-gated; runs FULL verify. P2/P5."""
from __future__ import annotations


def commit(staging_project: object, *, approver_roles: frozenset[str]) -> object:
    """Merge staging -> canonical (full verify, held-out filter, PROV-O, git). K2."""
    raise NotImplementedError("P2: implement the approver-gated commit (K2/ADR-6)")
