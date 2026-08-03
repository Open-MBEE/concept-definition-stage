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

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import pyshacl
from pydantic import BaseModel
from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import SH, XSD
from rdflib.term import Node

from cds.core.model.instances import KIND_TERM
from cds.core.namespaces import CDS, CDS_TERM, DCTERMS, PROV
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


@dataclass(frozen=True)
class RawReport:
    """Engine-agnostic raw validation output — the ADR-7c backend contract's return type."""

    conforms: bool
    report: Graph


class VerifierBackend(Protocol):
    """The swappable verification engine seam (ADR-7c).

    ``verify()``'s public signature is the frozen caller contract; this Protocol is the frozen
    *engine* contract behind it. pyshacl (``PyShaclBackend``) is the reference implementation and
    current default. A future engine (e.g. a Rust SHACL validator or a SHACL→SPARQL-on-Oxigraph
    compiler — deferred, spec §11 D1) drops in here, and only after passing the W3C-suite +
    differential-vs-pyshacl parity harness (REQ-VB.1).

    ``focus`` / ``shape_subset`` support targeted "staging-delta" validation (spec ADR-7b): verify
    only the touched focus nodes against a subset of shapes for interactive-latency feedback.
    """

    def validate(
        self,
        data: Graph,
        shapes: Graph,
        *,
        focus: Iterable[str] | None = None,
        shape_subset: Iterable[str] | None = None,
    ) -> RawReport: ...


class PyShaclBackend:
    """Reference implementation and current default engine (ADR-7c): pyshacl, ``advanced=True``."""

    def validate(
        self,
        data: Graph,
        shapes: Graph,
        *,
        focus: Iterable[str] | None = None,
        shape_subset: Iterable[str] | None = None,
    ) -> RawReport:
        conforms, report, _text = pyshacl.validate(
            data,
            shacl_graph=shapes,
            advanced=True,  # sh:sparql + sh:prefixes
            inference="none",
            allow_infos=True,
            allow_warnings=True,
            focus_nodes=list(focus) if focus is not None else None,
            use_shapes=list(shape_subset) if shape_subset is not None else None,
        )
        return RawReport(conforms=bool(conforms), report=report)


_DEFAULT_BACKEND: VerifierBackend = PyShaclBackend()


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


_SHALL = re.compile(r"\bshall\b", re.IGNORECASE)

#: The cross-record conflict checks and the severities they emit (keep in sync with
#: ``_check_conflicts`` below — these are not SHACL shapes, so they are enumerated here).
_CONFLICT_RULE_SEVERITIES: dict[str, Severity] = {
    "NeedFormShall": Severity.WARNING,
    "NeedWithoutStakeholder": Severity.WARNING,
    "NeedServesNoGoal": Severity.INFO,
    "DuplicateStatement": Severity.WARNING,
    "SynthesisWithoutNeeds": Severity.INFO,
    "DanglingReference": Severity.WARNING,
    "ReferenceToRetracted": Severity.WARNING,
    "DivergingPositions": Severity.INFO,
    "UnresolvedCitation": Severity.WARNING,
}


def rule_severities(shapes: Graph | None = None) -> dict[str, Severity]:
    """Every known rule name → its severity: the named SHACL shapes (default Violation per
    the SHACL spec) plus the conflict checks. The waiver gate's ground truth — a waiver
    naming an unknown rule is a dead waiver; one naming a Violation-class rule is refused."""
    shapes = shapes if shapes is not None else load_shapes()
    out: dict[str, Severity] = dict(_CONFLICT_RULE_SEVERITIES)
    for cls in (SH.NodeShape, SH.PropertyShape):
        for s in shapes.subjects(RDF.type, cls):
            if not isinstance(s, URIRef):
                continue
            sev = shapes.value(s, SH.severity)
            out[_local_name(str(s))] = _FROM_SHACL.get(sev, Severity.VIOLATION) if sev \
                else Severity.VIOLATION
    return out


def unresolved_citations(data: Graph, full: Graph | None = None) -> list[tuple[URIRef, URIRef]]:
    """(record, cited IRI) pairs where a project-local citation (/src/ path) resolves to
    nothing in ``full``. One condition, two consumers: the ``UnresolvedCitation`` T2
    finding here, and the commit gate's unverified-source hold (S1, live-QA 2026-08-02) —
    shared so the finding and the hold can never drift apart."""
    full = full if full is not None else data
    pairs: list[tuple[URIRef, URIRef]] = []
    for subj, cited in data.subject_objects(CDS.cites):
        if isinstance(subj, URIRef) and isinstance(cited, URIRef) \
                and "/src/" in str(cited) and (cited, None, None) not in full:
            pairs.append((subj, cited))
    return sorted(pairs, key=lambda p: (str(p[0]), str(p[1])))


def _check_conflicts(data: Graph) -> list[Finding]:
    """Cross-record consistency checks over an *instance* graph (not expressible per-record SHACL).

    Adapts ant-rdf's ``_check_crossrefs`` shape — iterate a curated set of relations, cross-check an
    index built from the graph, and emit findings in the same shape SHACL produces. All are surfaced
    (T2/T3), not gate-failing; they flag rather than block, per the elicitation ethos.

    Record-level checks run over the **current view** (ADR-9): superseded/retracted records
    are history, not live statements — a supersession must not read as a DuplicateStatement.
    Link *targets* resolve against the FULL graph (a link to a non-current record is not
    dangling); a current record referencing a retracted one is surfaced as
    ``ReferenceToRetracted`` (T2), with the lifecycle links themselves exempt.
    """
    from cds.core.view import current_view

    full = data
    data = current_view(data)
    findings: list[Finding] = []
    needs = list(data.subjects(RDF.type, CDS_TERM["need"]))

    for need in needs:
        desc = data.value(need, DCTERMS.description)
        if desc is not None and _SHALL.search(str(desc)):
            findings.append(Finding(Severity.WARNING, "NeedFormShall", str(need),
                "need uses 'shall' — write it in need-form instead, "
                "e.g. 'the <stakeholder> needs the system to …' (requirements come later)"))
        if not any(data.objects(need, CDS.forStakeholder)):
            findings.append(Finding(Severity.WARNING, "NeedWithoutStakeholder", str(need),
                "need is not linked to any stakeholder (orphan need)"))
        if not any(data.objects(need, CDS.servesGoal)):
            findings.append(Finding(Severity.INFO, "NeedServesNoGoal", str(need),
                "need serves no goal (not linked to any goal it advances)"))

    # duplicate statements: same semantic type + normalized description
    by_key: dict[tuple[str, str], list[str]] = defaultdict(list)
    for s in data.subjects(RDF.type, CDS.Instance):
        desc = data.value(s, DCTERMS.description)
        if desc is None:
            continue
        types = sorted(str(t) for t in data.objects(s, RDF.type) if t != CDS.Instance)
        by_key[("|".join(types), " ".join(str(desc).lower().split()))].append(str(s))
    for _key, subs in sorted(by_key.items()):
        if len(subs) > 1:
            findings.append(Finding(Severity.WARNING, "DuplicateStatement", sorted(subs)[0],
                f"duplicate statement shared by: {', '.join(sorted(subs))}"))

    # set-level completeness: a mapping with no needs yet
    for syn in data.subjects(RDF.type, CDS.Synthesis):
        if not any((need, CDS.inSynthesis, syn) in data for need in needs):
            findings.append(Finding(Severity.INFO, "SynthesisWithoutNeeds", str(syn),
                "mapping has no needs yet (integrated set is empty)"))

    # dangling references: a project-internal link whose target record doesn't exist. Matched by
    # slug (not exact IRI), so a link built with a hard-coded target kind still resolves.
    # Targets come from the FULL graph: linking to a superseded/retracted record is not dangling.
    existing = {str(s).rsplit("/", 1)[-1] for s in full.subjects(RDF.type, CDS.Instance)}
    existing |= {str(s).rsplit("/", 1)[-1] for s in full.subjects(RDF.type, CDS.Synthesis)}
    marks = tuple(f"/{kind}/" for kind in (*KIND_TERM, "synthesis"))
    link_props = (CDS.forStakeholder, CDS.servesGoal, CDS.refines, CDS.addresses,
                  CDS.supersedes, CDS.supersededBy, CDS.inSynthesis,
                  CDS.characterizes, CDS.heldBy)
    # referential integrity is checked over the FULL graph — a non-current record's dangling
    # marker (e.g. supersededBy pointing nowhere) is still a defect of the record.
    seen: set[tuple[str, str]] = set()
    for prop in link_props:
        for subj, obj in full.subject_objects(prop):
            text = str(obj)
            if not isinstance(obj, URIRef) or not any(m in text for m in marks):
                continue  # external IRI (e.g. a cited source) — not a project link
            if text.rsplit("/", 1)[-1] in existing or (str(subj), text) in seen:
                continue
            seen.add((str(subj), text))
            findings.append(Finding(Severity.WARNING, "DanglingReference", str(subj),
                f"links to a record that doesn't exist: {'/'.join(text.rsplit('/', 2)[-2:])}"))

    # a project-local citation (/src/ path) that resolves to nothing in the graph — the
    # retrieval workflow should know about it before it reaches a commit (LARP#3 H-5)
    for subj, cited in unresolved_citations(data, full):
        text = str(cited)
        findings.append(Finding(Severity.WARNING, "UnresolvedCitation", str(subj),
            f"cites a source record that doesn't exist: "
            f"{'/'.join(text.rsplit('/', 2)[-2:])} — register/secure it "
            "(retrieval queue) before commit"))

    # positions diverging on the same target (X2-lite, ADR-9 R7): a FINDING, never a
    # violation — perspectives may validly conflict; both are retained and surfaced.
    by_target: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for pos in data.subjects(RDF.type, CDS.Position):
        target = data.value(pos, CDS.characterizes)
        stance = data.value(pos, CDS.stance)
        if target is None or stance is None:
            continue
        holder = data.value(pos, CDS.heldBy)
        holder_name = str(holder).rsplit("/", 1)[-1] if holder is not None else "?"
        by_target[str(target)].append((holder_name, str(stance)))
    for target_iri, entries in sorted(by_target.items()):
        stances = {st for _h, st in entries}
        if len(entries) > 1 and len(stances) > 1:
            detail = "; ".join(f"{h}: {st}" for h, st in sorted(entries))
            findings.append(Finding(Severity.INFO, "DivergingPositions", target_iri,
                f"perspectives diverge — {detail} (all retained; divergence is valid)"))

    # a CURRENT record leaning on a RETRACTED one (lifecycle links exempt — they are history)
    content_links = tuple(p for p in link_props if p not in (CDS.supersedes, CDS.supersededBy))
    for prop in content_links:
        for subj, obj in data.subject_objects(prop):
            if not isinstance(obj, URIRef):
                continue
            if (obj, CDS.retracted, Literal(True)) in full:
                findings.append(Finding(Severity.WARNING, "ReferenceToRetracted", str(subj),
                    f"references retracted record {'/'.join(str(obj).rsplit('/', 2)[-2:])} — "
                    "update the link or retract this record too"))

    return findings


def verify(
    data: Graph,
    *,
    shapes: Graph | None = None,
    waivers: Iterable[Waiver] | None = None,
    check_conflicts: bool = False,
) -> VerifyResult:
    """Validate ``data`` against the cds shapes.

    ``conforms`` (SHACL's verdict) is the gate. Waivers default to those carried *in* ``data`` (they
    are first-class RDF); pass ``waivers`` explicitly to override. Waivers only ever drop a
    surfaced T2/T3 — never a T1. Set ``check_conflicts`` to add the cross-record consistency pass
    (need-form, orphan/duplicate, set-level) — used when verifying a user's authored mapping.
    """
    shapes = shapes if shapes is not None else load_shapes()
    raw = _DEFAULT_BACKEND.validate(data, shapes)
    pool = list(_findings(raw.report))
    if check_conflicts:
        pool.extend(_check_conflicts(data))
    waiver_list = list(waivers) if waivers is not None else waivers_from_graph(data)
    kept = tuple(
        sorted(
            (
                f
                for f in pool
                if f.severity is Severity.VIOLATION or not any(w.matches(f) for w in waiver_list)
            ),
            key=lambda f: (_RANK[f.severity], f.rule, f.focus, f.message),
        )
    )
    return VerifyResult(conforms=raw.conforms, findings=kept)
