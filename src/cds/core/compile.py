"""Deterministic RDF → Markdown brief — the human-readable View of a user's mapping.

Ports ant-rdf's compiler pattern: read the instance graph, emit a byte-stable Markdown document
(everything ``sorted``; no timestamps in the body) so re-compiling is identical and diff-friendly.
This is the "record" side of the calm-tech loop — the human reviews the brief, revisions loop back
through the CLI.
"""

from __future__ import annotations

from collections import defaultdict

from rdflib import RDF, RDFS, Graph, URIRef
from rdflib.term import Node

from cds.core.model.instances import KIND_TERM
from cds.core.namespaces import CDS, CDS_TERM, DCTERMS

# Ordered sections of the Business / Mission Analysis half.
_ANALYSIS_KINDS: tuple[tuple[str, str], ...] = (
    ("problem", "Problem"),
    ("opportunity", "Opportunity"),
    ("mission", "Mission"),
    ("goal", "Goals"),
    ("objective", "Objectives"),
    ("driver", "Drivers"),
    ("constraint", "Constraints"),
    ("moe", "Measures of Effectiveness"),
)


def _local(node: Node) -> str:
    return str(node).rsplit("/", 1)[-1]


def _label(g: Graph, s: Node) -> str:
    v = g.value(s, RDFS.label)
    return str(v) if v is not None else _local(s)


def _desc(g: Graph, s: Node) -> str:
    v = g.value(s, DCTERMS.description)
    return str(v) if v is not None else ""


def _records(g: Graph, kind: str) -> list[Node]:
    """Instances of ``kind``, sorted by IRI for determinism."""
    return sorted(g.subjects(RDF.type, CDS_TERM[KIND_TERM[kind]]), key=str)


def _refs(g: Graph, s: Node, pred: Node) -> str:
    names = sorted(_local(o) for o in g.objects(s, pred))
    return ", ".join(names)


def _supersedes(g: Graph, s: Node) -> str:
    names = sorted(_local(o) for o in g.objects(s, CDS.supersedes))
    return f" _(supersedes: {', '.join(names)})_" if names else ""


def _md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    def esc(cell: str) -> str:
        return cell.replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(esc(c) for c in row) + " |" for row in rows]
    return out


def compile_brief(graph: Graph, *, base: str, include_history: bool = False,
                  synthesis: str | None = None) -> str:
    """Render the mapping to a deterministic Markdown brief.

    The body renders the **current view** (ADR-9): superseded/retracted records are history.
    ``include_history=True`` adds the deterministic "Superseded & retracted" appendix — off
    by default because the model, not any one rendered document, is canon; the changelog is
    never lost by not being displayed (markers + git hold it).

    ``synthesis=<slug>`` scopes the brief to one mapping (records whose ``cds:inSynthesis``
    points there, plus that container) — no cross-synthesis bleed (G-5). Default: everything.
    """
    from cds.core.view import current_view

    full = graph
    graph = current_view(graph)
    if synthesis is not None:
        graph = _scope_to_synthesis(graph, base=base, synthesis=synthesis)
        full = _scope_to_synthesis(full, base=base, synthesis=synthesis)
    lines: list[str] = []
    syntheses = sorted(graph.subjects(RDF.type, CDS.Synthesis), key=str)
    title = _label(graph, syntheses[0]) if syntheses else "Concept Definition"
    lines.append(f"# {title}")
    lines.append("")
    lines.append("*Concept Definition: Business Analysis & Stakeholder Needs*")
    lines.append("")

    # ---- Business / Mission Analysis
    lines.append("## Business / Mission Analysis")
    lines.append("")
    for kind, heading in _ANALYSIS_KINDS:
        recs = _records(graph, kind)
        if not recs:
            continue
        lines.append(f"### {heading}")
        lines.append("")
        for s in recs:
            extra = ""
            if kind == "objective":
                refines = _refs(graph, s, CDS.refines)
                extra = f" _(refines: {refines})_" if refines else ""
            elif kind == "goal":
                addresses = _refs(graph, s, CDS.addresses)
                extra = f" _(addresses: {addresses})_" if addresses else ""
            sup = _supersedes(graph, s)
            lines.append(f"- **{_label(graph, s)}**: {_desc(graph, s)}{extra}{sup}")
        lines.append("")

    # ---- Stakeholders
    stakeholders = _records(graph, "stakeholder")
    if stakeholders:
        lines.append("## Stakeholders")
        lines.append("")
        rows = [
            [
                _label(graph, s),
                str(graph.value(s, CDS.segment) or ""),
                str(graph.value(s, CDS.interest) or ""),
                str(graph.value(s, CDS.influence) or ""),
                _desc(graph, s),
            ]
            for s in stakeholders
        ]
        lines += _md_table(["Stakeholder", "Segment", "Interest", "Influence", "Description"], rows)
        lines.append("")

    # ---- Integrated set of needs
    needs = _records(graph, "need")
    if needs:
        lines.append("## Integrated Set of Needs")
        lines.append("")
        for s in needs:
            who = _refs(graph, s, CDS.forStakeholder)
            serves = _refs(graph, s, CDS.servesGoal)
            tags = []
            if who:
                tags.append(f"stakeholder: {who}")
            if serves:
                tags.append(f"serves: {serves}")
            suffix = f" _({'; '.join(tags)})_" if tags else ""
            lines.append(
                f"- **{_label(graph, s)}**: {_desc(graph, s)}{suffix}{_supersedes(graph, s)}"
            )
        lines.append("")

    # ---- perspectives (X2-lite): stakeholder positions on shared frame objects
    _positions_section(lines, graph)

    # ---- side ledgers
    _tensions_section(lines, graph)
    _section(lines, graph, CDS.ParkedItem, "Parking-lot")
    _queue_section(lines, graph)

    if include_history:
        _history_appendix(lines, full)

    return "\n".join(lines).rstrip("\n") + "\n"


def _scope_to_synthesis(graph: Graph, *, base: str, synthesis: str) -> Graph:
    """Subgraph of one mapping: its container + every subject with ``inSynthesis`` → it.

    Ledger items (parked/queue/tension) carry no synthesis membership and pass through —
    they are session hygiene, not mapping content.
    """
    syn_iri = URIRef(f"{base}synthesis/{synthesis}")
    instances = set(graph.subjects(RDF.type, CDS.Instance))
    containers = set(graph.subjects(RDF.type, CDS.Synthesis))
    keep = {syn_iri} | set(graph.subjects(CDS.inSynthesis, syn_iri))
    out = Graph()
    for s, p, o in graph:
        if s in keep or (s not in instances and s not in containers):
            out.add((s, p, o))
    return out


def _history_appendix(lines: list[str], full: Graph) -> None:
    """The non-current records with their lifecycle markers (ADR-9; deterministic)."""
    from cds.core.view import is_current

    entries: list[str] = []
    for s in sorted(full.subjects(RDF.type, CDS.Instance), key=str):
        if is_current(full, s):
            continue
        marks: list[str] = []
        by = sorted(_local(o) for o in full.objects(s, CDS.supersededBy))
        if by:
            marks.append(f"superseded by: {', '.join(by)}")
        if (s, CDS.retracted, None) in full:
            reason = full.value(s, CDS.retractionReason)
            marks.append(f"retracted{f': {reason}' if reason is not None else ''}")
        entries.append(f"- **{_label(full, s)}**: {_desc(full, s)} _({'; '.join(marks)})_")
    if not entries:
        return
    lines.append("## Superseded & retracted")
    lines.append("")
    lines += entries
    lines.append("")


def _positions_section(lines: list[str], graph: Graph) -> None:
    """Positions grouped per characterized subject, with a converge/diverge verdict.

    Divergence is a rendered finding, never an error — perspectives may validly conflict
    (ADR-9 R7); convergence is itself a finding worth seeing, not redundancy.
    """
    positions = sorted(graph.subjects(RDF.type, CDS.Position), key=str)
    if not positions:
        return
    by_target: dict[str, list[Node]] = defaultdict(list)
    for p in positions:
        target = graph.value(p, CDS.characterizes)
        if target is not None:
            by_target[str(target)].append(p)
    if not by_target:
        return
    lines.append("## Convergence & divergence")
    lines.append("")
    for target_iri in sorted(by_target):
        entries = sorted(by_target[target_iri], key=str)
        stances = {str(graph.value(p, CDS.stance) or "") for p in entries}
        if len(entries) == 1:
            verdict = "single voice"
        elif len(stances) > 1:
            verdict = "**diverge**"
        else:
            verdict = "converge"
        lines.append(f"### {_label(graph, URIRef(target_iri))}: {verdict}")
        lines.append("")
        for p in entries:
            holder = graph.value(p, CDS.heldBy)
            stance = str(graph.value(p, CDS.stance) or "")
            inv = graph.value(p, CDS.invarianceCriterion)
            inv_note = f" _(holds constant: {inv})_" if inv is not None else ""
            lines.append(f"- **{_local(holder) if holder else '?'}** {stance}: "
                         f"{_desc(graph, p)}{inv_note}")
        lines.append("")


def _section(lines: list[str], graph: Graph, cls: Node, heading: str) -> None:
    items = sorted(graph.subjects(RDF.type, cls), key=str)
    if not items:
        return
    lines.append(f"## {heading}")
    lines.append("")
    for s in items:
        desc = _desc(graph, s)
        lines.append(f"- **{_label(graph, s)}**" + (f": {desc}" if desc else ""))
    lines.append("")


def _tensions_section(lines: list[str], graph: Graph) -> None:
    # only OPEN tensions render; resolved ones drop out of the brief
    items = sorted(
        (
            s
            for s in graph.subjects(RDF.type, CDS.Tension)
            if str(graph.value(s, CDS.tensionStatus) or "open") != "resolved"
        ),
        key=str,
    )
    if not items:
        return
    lines.append("## Tensions")
    lines.append("")
    for s in items:
        desc = _desc(graph, s)
        lines.append(f"- **{_label(graph, s)}**" + (f": {desc}" if desc else ""))
    lines.append("")


def _queue_section(lines: list[str], graph: Graph) -> None:
    items = sorted(graph.subjects(RDF.type, CDS.RetrievalItem), key=str)
    if not items:
        return
    lines.append("## Open Items (Retrieval Queue)")
    lines.append("")
    for s in items:
        status = str(graph.value(s, CDS.retrievalStatus) or "pending")
        lines.append(f"- [{status}] {_label(graph, s)}")
    lines.append("")
