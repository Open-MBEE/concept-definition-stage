"""PROV-O stamping + append-only audit for LLM actions and commits. P3 (K4)."""
from __future__ import annotations


def stamp(triples: object, *, user: str, session: str, model: str) -> object:
    raise NotImplementedError("P3: attach PROV-O attribution (K4)")
