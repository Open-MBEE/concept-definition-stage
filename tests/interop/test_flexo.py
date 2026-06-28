"""Slice 9 — Flexo MMS interop: the canonical scheme round-trips through a Flexo branch losslessly.

The in-memory round-trip runs always (local-first, no creds); the live Flexo round-trip auto-skips
without ``FLEXO_*`` credentials, like flexo-rtm's Flexo tests. Lossless = isomorphic (our graphs
have no blank nodes, so this is exact triple-set equality) — confirming flexo-rtm can consume the
vocabulary downstream via the shared SysML v2 anchor.
"""

from __future__ import annotations

import pytest
from rdflib.compare import isomorphic

from cds.core.flexo import (
    FlexoHttpClient,
    InMemoryFlexoBackend,
    flexo_config_from_env,
)
from cds.stages.concept_definition.build import build_concept_definition_graph


def test_scheme_round_trips_through_an_in_memory_flexo_branch() -> None:
    scheme = build_concept_definition_graph()
    backend = InMemoryFlexoBackend(branches=("main",))
    backend.commit(branch="main", graph=scheme)
    read_back = backend.read_graph(branch="main")
    assert isomorphic(read_back, scheme)  # lossless round-trip


def test_unknown_branch_is_an_error() -> None:
    from cds.core.flexo import FlexoError

    with pytest.raises(FlexoError):
        InMemoryFlexoBackend(branches=("main",)).read_graph(branch="nope")


@pytest.mark.skipif(flexo_config_from_env() is None, reason="no FLEXO_* credentials configured")
def test_scheme_round_trips_through_a_live_flexo() -> None:
    config = flexo_config_from_env()
    assert config is not None
    client = FlexoHttpClient(config)
    scheme = build_concept_definition_graph()
    client.commit(branch="main", graph=scheme)
    assert isomorphic(client.read_graph(branch="main"), scheme)
