"""Typed wrappers over cds.core (authoring/verify/explain/compile) — P1 (K1).

Each tool maps to a real cds function and produces CANDIDATES (never canonical state).
"""
from __future__ import annotations


def not_built(name: str) -> None:
    raise NotImplementedError(f"P1: implement MCP tool {name!r}")
