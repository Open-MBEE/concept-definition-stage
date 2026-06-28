"""Optional Flexo MMS interop — loosely coupled, never a hard dependency.

`cds` is local-first: absent Flexo, everything runs on in-memory rdflib + local TTL. This adapter
lets the canonical scheme round-trip through a Flexo named graph and back, confirming the vocabulary
is consumable by `flexo-rtm` downstream via the shared SysML v2 anchor.

Modeled on the flexo-rtm storage pattern (a `FlexoBackend` Protocol with an in-memory implementation
for tests + a creds-gated HTTP client for a live Flexo MMS Layer-1). **A Flexo branch IS the named
graph** (Layer-1 semantics), so writes are bare triples on a branch. The adapter is creds-gated, not
a hard import: `flexo_config_from_env()` returns None when no Flexo is configured, and interop tests
auto-skip — exactly like flexo-rtm's Flexo tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from rdflib import Graph


class FlexoError(RuntimeError):
    """A Flexo interop failure (unknown branch, transport error, ...)."""


@runtime_checkable
class FlexoBackend(Protocol):
    """The minimal round-trip contract: commit a graph to a branch, read it back."""

    def commit(self, *, branch: str, graph: Graph) -> None: ...

    def read_graph(self, *, branch: str) -> Graph: ...


class InMemoryFlexoBackend:
    """A local stand-in for Flexo MMS (the local-first path). A branch is a named graph."""

    def __init__(self, branches: tuple[str, ...] = ("main",)) -> None:
        self._branches = set(branches)
        self._store: dict[str, Graph] = {b: Graph() for b in branches}

    def commit(self, *, branch: str, graph: Graph) -> None:
        if branch not in self._branches:
            raise FlexoError(f"unknown branch: {branch!r}")
        target = self._store[branch]
        for triple in graph:
            target.add(triple)

    def read_graph(self, *, branch: str) -> Graph:
        if branch not in self._branches:
            raise FlexoError(f"unknown branch: {branch!r}")
        out = Graph()
        for triple in self._store[branch]:
            out.add(triple)
        return out


@dataclass(frozen=True)
class FlexoConfig:
    """Connection config for a live Flexo MMS Layer-1 (a branch is a named graph)."""

    base_url: str
    org: str
    repo: str
    token: str
    timeout_seconds: float = 60.0


def flexo_config_from_env() -> FlexoConfig | None:
    """Build a config from ``FLEXO_*`` env vars, or None if Flexo is not configured (→ skip)."""
    try:
        return FlexoConfig(
            base_url=os.environ["FLEXO_BASE_URL"],
            org=os.environ["FLEXO_ORG"],
            repo=os.environ["FLEXO_REPO"],
            token=os.environ["FLEXO_TOKEN"],
        )
    except KeyError:
        return None


class FlexoHttpClient:
    """A live Flexo MMS Layer-1 client over SPARQL (POST update / query).

    Only constructed when a ``FlexoConfig`` is present (creds-gated); the in-memory backend is the
    default. Writes flatten to bare ``INSERT DATA`` triples (Layer-1 rejects GRAPH clauses — the
    branch is the graph); reads issue a ``CONSTRUCT``. The exact Flexo REST nuances are exercised by
    the live, skip-if-no-creds interop test, not in offline CI.
    """

    def __init__(self, config: FlexoConfig) -> None:
        self._config = config

    def _post(self, path: str, body: str, content_type: str) -> bytes:
        import urllib.request

        url = f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"
        request = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._config.token}",
                "Content-Type": content_type,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._config.timeout_seconds) as resp:
                return resp.read()  # type: ignore[no-any-return]
        except OSError as exc:  # transport / HTTP error
            raise FlexoError(f"Flexo request failed: {exc}") from exc

    def _branch_path(self, branch: str, verb: str) -> str:
        return f"orgs/{self._config.org}/repos/{self._config.repo}/branches/{branch}/{verb}"

    def commit(self, *, branch: str, graph: Graph) -> None:
        triples = "\n".join(
            f"{s.n3()} {p.n3()} {o.n3()} ." for s, p, o in graph  # no blank nodes in our graphs
        )
        self._post(
            self._branch_path(branch, "update"),
            f"INSERT DATA {{\n{triples}\n}}",
            "application/sparql-update",
        )

    def read_graph(self, *, branch: str) -> Graph:
        body = self._post(
            self._branch_path(branch, "query"),
            "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
            "application/sparql-query",
        )
        g = Graph()
        g.parse(data=body, format="turtle")
        return g
