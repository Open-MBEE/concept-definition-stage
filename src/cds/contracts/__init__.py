"""Cross-component interface contracts — the modularity keystone (spec §6.0/§8.3).

Six components, each a would-be distribution, joined only by the typed seams in this module
(which imports ONLY ``cds.core`` — enforced by ``tests/unit/test_factoring.py``):

1. the modeling-family package (``cds.core`` + ``cds.stages`` + CLI),
2. the conformance oracle service (``cds.oracle`` — verification, "build it right"),
3. the facilitator service (``cds.facilitator`` — correct-by-construction authoring),
4. the model datastore service (contract here; Flexo MMS target, ROADMAP T6),
5. the MCP tool server (``cds.mcp`` — composes 1 + 2 + 4 behind the K1 whitelist),
6. the web app (``cds.app`` — drives the facilitator).

The rule: any component can move out-of-process without changing its consumers — a consumer
holds a Protocol from here, never a sibling import.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from rdflib import Graph

from cds.core.flexo import FlexoBackend
from cds.core.verify import VerifyResult, verify

__all__ = ["ConformanceOracle", "InProcessOracle", "ModelStore"]


@runtime_checkable
class ConformanceOracle(Protocol):
    """The verification seam ("build it right" — machine, never fitness-for-purpose).

    A model *instance* graph goes in; a tri-severity :class:`~cds.core.verify.VerifyResult`
    comes out, each finding carrying the named ``rule``, the ``focus`` node, and an authored
    ``message`` — the raw material of remediation. Stateless by contract.
    """

    def check(self, data: Graph, *, check_conflicts: bool = True) -> VerifyResult: ...


@dataclass(frozen=True)
class InProcessOracle:
    """Reference oracle: ``cds.core.verify`` in-process.

    DEFERRED (spec §11 D8): an HTTP client implementation consuming the ``cds-oracle``
    service's ``POST /verify`` — trigger: an out-of-process consumer (the P5/P6 app tier).
    It drops in behind this same Protocol without touching any consumer.
    """

    def check(self, data: Graph, *, check_conflicts: bool = True) -> VerifyResult:
        return verify(data, check_conflicts=check_conflicts)


# The datastore seam (spec §6.0 C4, §8.3): per-branch model-instance storage.
#
# ``cds.core.flexo.FlexoBackend`` — ``commit(*, branch, graph)`` / ``read_graph(*, branch)`` —
# already IS that contract; re-exported under the component name rather than duplicated.
# Implementations today: ``InMemoryFlexoBackend`` (tests) and the git-TTL project layout (the
# durable record, ADR-7a; P2's session staging binds it). DEFERRED (spec §11 D9): the
# Flexo-MMS-backed store service via ``FlexoHttpClient`` — trigger: ROADMAP T6 acceptance.
ModelStore = FlexoBackend
