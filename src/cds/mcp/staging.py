"""Session staging: candidates land in a scratch DATA_ROOT, never canonical. P2 (K2/ADR-5)."""
from __future__ import annotations


def new_session_project(base_iri: str):
    """Create a scratch cds Project (temp DATA_ROOT) for one session's candidates."""
    raise NotImplementedError("P2: create a scratch staging Project (ADR-5)")
