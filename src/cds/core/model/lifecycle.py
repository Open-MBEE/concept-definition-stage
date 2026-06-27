"""The top-level abstract base for modeling a system through its whole life cycle.

A lifecycle model **necessarily starts with the Concept Definition stage**; later stages
(System Definition, …) specialize the same base. The base carries an ``ip_status`` flag that
governs the View layer's licensing override.

IP-status override (consumed by the View, slice 8):

* ``OPEN`` (default) — the View does **not** render restricted (e.g. NC) canon; it cites the
  authoritative source. Outputs are unencumbered.
* ``NC`` — the **operator** asserts the use case complies with CC-BY-NC-SA (e.g. non-commercial
  education). The View **may** render restricted canon (e.g. SEBoK definitions), and any report
  rendered with the flag on is itself licensed **CC-BY-NC-SA** (ShareAlike propagates).

The *operator*, not the tool, is responsible for determining whether the circumstances qualify.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel
from rdflib import RDF, RDFS, Graph, Literal, URIRef

from cds.core.namespaces import CDS


class IpStatus(StrEnum):
    """The IP regime a lifecycle model's rendered outputs operate under."""

    OPEN = "open"  # default: no restricted canon rendered; cite the source
    NC = "nc"  # operator-asserted CC-BY-NC-SA use: render restricted canon; reports are CC-BY-NC-SA


class LifecycleModel(BaseModel):
    """A model of a system across its life cycle (abstract base; stages specialize it)."""

    id: str
    label: str
    stage: str
    ip_status: IpStatus = IpStatus.OPEN


def lifecycle_to_graph(model: LifecycleModel) -> Graph:
    """Emit the lifecycle model resource (typed, labelled, with its IP status)."""
    from cds.core.controlled import controlled_concept  # local: avoids an import cycle

    g = Graph()
    s = URIRef(model.id)
    g.add((s, RDF.type, CDS.LifecycleModel))
    g.add((s, RDFS.label, Literal(model.label)))
    g.add((s, CDS.stage, Literal(model.stage)))
    g.add((s, CDS.ipStatus, controlled_concept(model.ip_status)))
    return g
