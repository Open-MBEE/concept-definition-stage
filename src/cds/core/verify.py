"""Tri-severity SHACL verification with append-only waivers (the local-first ``cds verify``).

Severity maps to SHACL's native levels — **T1 = ``sh:Violation``**, **T2 = ``sh:Warning``**,
**T3 = ``sh:Info``** — and ``cds verify`` exits non-zero iff any unwaived **T1** remains. The
shapes (``ontology/shapes/*.ttl``) encode the **construction order** structurally: a stage's
triples are invalid until the prior stage's preconditions hold (authority before source; verbatim
only on a verified source — the hallucination guard; cite + ground + admit before a term is sound).

**Waivers are append-only and T1 is never waivable.** A waiver can only ever suppress a Warning or
an Info; a waiver that happens to select a Violation has no effect on it — process integrity is not
negotiable away.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pyshacl
import yaml
from pydantic import BaseModel, model_validator
from rdflib import RDF, Graph
from rdflib.namespace import SH
from rdflib.term import Node

SHAPES_DIR = Path(__file__).resolve().parents[3] / "ontology" / "shapes"


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
    """The trailing name of an IRI (after the last ``#`` or ``/``); pass blank nodes through."""
    for sep in ("#", "/"):
        if sep in iri:
            iri = iri.rsplit(sep, 1)[-1]
    return iri


@dataclass(frozen=True)
class Finding:
    """One SHACL validation result, normalized to the cds tri-severity model."""

    severity: Severity
    shape: str  # the source shape IRI (a blank node for inline property shapes)
    focus: str  # the focus node the constraint fired on
    message: str
    component: str  # the SHACL constraint-component local name

    @property
    def shape_name(self) -> str:
        """The source shape's local name (stable for named node shapes)."""
        return _local_name(self.shape)

    @property
    def tier(self) -> str:
        return _TIER[self.severity]


@dataclass(frozen=True)
class VerifyResult:
    """The outcome of a verification: the kept (unwaived) findings + pass/fail."""

    findings: tuple[Finding, ...]

    @property
    def passed(self) -> bool:
        """True iff no unwaived Violation (T1) remains."""
        return not self.violations

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
    """An append-only waiver for a non-Violation finding.

    Selects by any combination of ``shape`` (local name), ``focus`` node, and ``message`` substring;
    all provided selectors must match. A blanket waiver (no selector) is rejected. ``reason`` is
    mandatory — a waiver records *why* a known T2/T3 is accepted. T1 is never waivable.
    """

    reason: str
    shape: str | None = None
    focus: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def _require_a_selector(self) -> Waiver:
        if self.shape is None and self.focus is None and self.message is None:
            raise ValueError(
                "a waiver must select by shape, focus, or message (no blanket waivers)"
            )
        return self

    def matches(self, finding: Finding) -> bool:
        if self.shape is not None and _local_name(self.shape) != finding.shape_name:
            return False
        if self.focus is not None and self.focus != finding.focus:
            return False
        return not (self.message is not None and self.message not in finding.message)


def load_shapes(shapes_dir: Path = SHAPES_DIR) -> Graph:
    """Load and merge every ``*.ttl`` shape file in ``shapes_dir`` into one graph."""
    g = Graph()
    for ttl in sorted(shapes_dir.glob("*.ttl")):
        g.parse(ttl, format="turtle")
    return g


def load_waivers(path: Path) -> list[Waiver]:
    """Load waivers from a YAML list file; a missing file yields no waivers."""
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text()) or []
    return [Waiver.model_validate(item) for item in raw]


def _findings(report: Graph) -> tuple[Finding, ...]:
    out: list[Finding] = []
    for result in report.subjects(RDF.type, SH.ValidationResult):
        sev = report.value(result, SH.resultSeverity)
        message = report.value(result, SH.resultMessage)
        component = report.value(result, SH.sourceConstraintComponent)
        out.append(
            Finding(
                severity=_FROM_SHACL.get(sev, Severity.VIOLATION) if sev else Severity.VIOLATION,
                shape=str(report.value(result, SH.sourceShape)),
                focus=str(report.value(result, SH.focusNode)),
                message=str(message) if message is not None else "",
                component=_local_name(str(component)) if component is not None else "",
            )
        )
    return tuple(sorted(out, key=lambda f: (_RANK[f.severity], f.shape, f.focus, f.message)))


def verify(
    data: Graph,
    *,
    shapes: Graph | None = None,
    waivers: Iterable[Waiver] = (),
) -> VerifyResult:
    """Validate ``data`` against the cds shapes, applying waivers (never to Violations)."""
    shapes = shapes if shapes is not None else load_shapes()
    _conforms, report, _text = pyshacl.validate(
        data,
        shacl_graph=shapes,
        advanced=True,  # sh:sparql + sh:prefixes
        inference="none",
        allow_infos=True,
        allow_warnings=True,
    )
    waiver_list = tuple(waivers)
    kept = tuple(
        f
        for f in _findings(report)
        if f.severity is Severity.VIOLATION or not any(w.matches(f) for w in waiver_list)
    )
    return VerifyResult(findings=kept)
