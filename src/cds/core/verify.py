"""Tri-severity verification with first-class (RDF) waivers — the local-first ``cds verify``.

This module gives a **Pythonic** surface over a semantic-web engine: SHACL/pyshacl run underneath,
but callers see plain ``Finding`` / ``VerifyResult`` / ``Waiver`` objects and a ``Severity`` enum —
never the pyshacl results graph or SHACL constraint-component vocabulary.

Two concerns are kept distinct (they are *not* the same thing):

* **SHACL conformance** = "is the construction structurally correct?" — pyshacl computes this as
  ``conforms`` (with warnings/infos allowed, it is exactly "no T1 violation"). That is the gate:
  ``VerifyResult.passed`` *is* ``conforms``. We do not re-derive or second-guess it.
* **Our tri-severity reporting + waiver policy** sits *on top* for human triage: T2/T3 findings are
  surfaced, and an operator may **waive** a T2/T3 (with a recorded reason). **T1 is never waivable**
  — a waiver that selects a Violation has no effect on it, and waivers never touch ``conforms``.

Severity maps to SHACL's native levels: **T1 = ``sh:Violation``**, **T2 = ``sh:Warning``**,
**T3 = ``sh:Info``**. Waivers are **first-class RDF data** (``cds:Waiver``) carried in the graph,
not a side-car config file — the audit trail of what was accepted is versioned with the rest.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

import pyshacl
from pydantic import BaseModel
from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import SH, XSD
from rdflib.term import Node

from cds.core.namespaces import CDS, DCTERMS, PROV
from cds.core.workspace import shapes_dir as _shapes_dir

SHAPES_DIR = _shapes_dir()


class Severity(StrEnum):
    """The tri-severity ladder (ant-rdf lineage), mapped to SHACL's native levels."""

    VIOLATION = "violation"  # T1 — fails the build
    WARNING = "warning"  # T2 — surfaced, does not fail
    INFO = "info"  # T3 — lint


_FROM_SHACL: dict[Node, Severity] = {
    SH.Violation: Severity.VIOLATION,
    SH.Warning: Severity.WARNING,
    SH.Info: Severity.INFO,
}
_RANK: dict[Severity, int] = {Severity.VIOLATION: 0, Severity.WARNING: 1, Severity.INFO: 2}
_TIER: dict[Severity, str] = {Severity.VIOLATION: "T1", Severity.WARNING: "T2", Severity.INFO: "T3"}


def _local_name(iri: str) -> str:
    """The trailing name of an IRI (after the last ``#`` or ``/``)."""
    for sep in ("#", "/"):
        if sep in iri:
            iri = iri.rsplit(sep, 1)[-1]
    return iri


@dataclass(frozen=True)
class Finding:
    """One check result, in cds terms — no SHACL plumbing leaks through.

    ``rule`` is the stable identity of the check that fired (each shape is named); ``focus`` is the
    node it fired on; ``message`` is the check's authored explanation.
    """

    severity: Severity
    rule: str
    focus: str
    message: str

    @property
    def tier(self) -> str:
        return _TIER[self.severity]


@dataclass(frozen=True)
class VerifyResult:
    """The outcome of a verification.

    ``conforms`` is SHACL's structural verdict (the gate); ``findings`` are the kept (unwaived)
    tri-severity results for human triage.
    """

    conforms: bool
    findings: tuple[Finding, ...]

    @property
    def passed(self) -> bool:
        """The build gate — identically SHACL conformance (no T1 violation)."""
        return self.conforms

    @property
    def violations(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.VIOLATION)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.WARNING)

    @property
    def infos(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.INFO)


class Waiver(BaseModel):
    """A first-class, conscious acceptance of a non-Violation finding.

    Selects the finding by its ``rule`` (the check's stable name) and, optionally, a specific
    ``focus`` node. ``reason`` is mandatory. Waivers are **append-only audit data** — round-tripped
    to/from RDF (``cds:Waiver``) — and **T1 is never waivable**.
    """

    id: str
    rule: str
    reason: str
    focus: str | None = None
    by: str | None = None  # operator who accepted it (provenance)
    waived_on: date | None = None  # when accepted (a stable input, never build-time now())

    def matches(self, finding: Finding) -> bool:
        if self.rule != finding.rule:
            return False
        return self.focus is None or self.focus == finding.focus


def load_shapes(shapes_dir: Path = SHAPES_DIR) -> Graph:
    """Load and merge every ``*.ttl`` shape file in ``shapes_dir`` into one graph."""
    g = Graph()
    for ttl in sorted(shapes_dir.glob("*.ttl")):
        g.parse(ttl, format="turtle")
    return g


def waiver_to_graph(waiver: Waiver) -> Graph:
    """Emit a waiver as first-class RDF (``cds:Waiver``)."""
    g = Graph()
    s = URIRef(waiver.id)
    g.add((s, RDF.type, CDS.Waiver))
    g.add((s, CDS.waivesRule, Literal(waiver.rule)))
    g.add((s, CDS.waiverReason, Literal(waiver.reason)))
    if waiver.focus is not None:
        g.add((s, CDS.waivesFocus, URIRef(waiver.focus)))
    if waiver.by is not None:
        g.add((s, PROV.wasAttributedTo, URIRef(waiver.by)))
    if waiver.waived_on is not None:
        g.add((s, DCTERMS.date, Literal(waiver.waived_on.isoformat(), datatype=XSD.date)))
    return g


def waivers_from_graph(graph: Graph) -> list[Waiver]:
    """Read every ``cds:Waiver`` carried in ``graph`` — waivers are data, not config."""
    out: list[Waiver] = []
    for s in graph.subjects(RDF.type, CDS.Waiver):
        rule = graph.value(s, CDS.waivesRule)
        reason = graph.value(s, CDS.waiverReason)
        if rule is None or reason is None:
            continue
        focus = graph.value(s, CDS.waivesFocus)
        by = graph.value(s, PROV.wasAttributedTo)
        d = graph.value(s, DCTERMS.date)
        out.append(
            Waiver(
                id=str(s),
                rule=str(rule),
                reason=str(reason),
                focus=str(focus) if focus is not None else None,
                by=str(by) if by is not None else None,
                waived_on=date.fromisoformat(str(d)) if d is not None else None,
            )
        )
    return out


def _findings(report: Graph) -> tuple[Finding, ...]:
    out: list[Finding] = []
    for result in report.subjects(RDF.type, SH.ValidationResult):
        sev = report.value(result, SH.resultSeverity)
        shape = report.value(result, SH.sourceShape)
        message = report.value(result, SH.resultMessage)
        out.append(
            Finding(
                severity=_FROM_SHACL.get(sev, Severity.VIOLATION) if sev else Severity.VIOLATION,
                rule=_local_name(str(shape)) if shape is not None else "",
                focus=str(report.value(result, SH.focusNode)),
                message=str(message) if message is not None else "",
            )
        )
    return tuple(sorted(out, key=lambda f: (_RANK[f.severity], f.rule, f.focus, f.message)))


def verify(
    data: Graph,
    *,
    shapes: Graph | None = None,
    waivers: Iterable[Waiver] | None = None,
) -> VerifyResult:
    """Validate ``data`` against the cds shapes.

    ``conforms`` (SHACL's verdict) is the gate. Waivers default to those carried *in* ``data`` (they
    are first-class RDF); pass ``waivers`` explicitly to override. Waivers only ever drop a
    surfaced T2/T3 — never a T1.
    """
    shapes = shapes if shapes is not None else load_shapes()
    conforms, report, _text = pyshacl.validate(
        data,
        shacl_graph=shapes,
        advanced=True,  # sh:sparql + sh:prefixes
        inference="none",
        allow_infos=True,
        allow_warnings=True,
    )
    waiver_list = list(waivers) if waivers is not None else waivers_from_graph(data)
    kept = tuple(
        f
        for f in _findings(report)
        if f.severity is Severity.VIOLATION or not any(w.matches(f) for w in waiver_list)
    )
    return VerifyResult(conforms=bool(conforms), findings=kept)
