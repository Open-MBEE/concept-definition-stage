<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Model datastore (contract; Flexo target)

> **Honest limits (P1):** no standalone store service runs yet — this page documents the
> **contract** that keeps it swappable, per the deferral discipline (spec §11 D9): what /
> why deferred / trigger / interface preserved.

The datastore is the component that **stores model instances** per branch. Its contract is
`cds.contracts.ModelStore` — a re-export of the existing `cds.core.flexo.FlexoBackend`
Protocol, deliberately *not* a divergent copy:

```python
class ModelStore(Protocol):
    def commit(self, *, branch: str, graph: Graph) -> None: ...
    def read_graph(self, *, branch: str) -> Graph: ...
```

## Implementations

| Implementation | Status | Role |
|---|---|---|
| `InMemoryFlexoBackend` (`cds.core.flexo`) | now | tests / ephemeral sessions |
| git-TTL project layout (`concept-definition/instances/*.ttl`) | now | **the durable record** — git is the system of record (ADR-7a); P2's session staging binds it |
| `FlexoHttpClient` → **Flexo MMS** (`cds.core.flexo`) | deferred → **ROADMAP T6** | the deployed datastore *service* (branches / named graphs, remote collaboration) |

**Trigger & acceptance (D9/T6):** the store service goes live when T6's live round-trip
passes — commit the scheme to a Starforge Layer-1 branch, read it back isomorphic, and
validate a git ↔ Flexo sync of the same graph. Until then, git-TTL *is* the store, and
Oxigraph (ADR-7a) remains a derived, rebuildable read index — if store and git disagree,
git wins.

## Consumers

- **MCP server / facilitator service** — session staging (P2) binds a local store; the
  commit gate merges staging → canonical git-TTL.
- **Web app tier (P5/P6)** — reads via the store contract (or the Oxigraph read index).

## Related docs

[MCP server](mcp-server.md) · [Facilitator service](facilitator.md) ·
[Conformance oracle](conformance-oracle.md) · [Architecture spec](../architecture/cds-web-app.md) ·
[Factoring](../architecture/factoring.md)
