"""Deterministic RDF → Markdown brief — the human-readable View of a user's mapping.

Ports ant-rdf's compiler pattern: read the instance graph, emit a byte-stable Markdown document
(everything ``sorted``; no timestamps in the body) so re-compiling is identical and diff-friendly.
This is the "record" side of the calm-tech loop — the human reviews the brief, revisions loop back
through the CLI.
"""

from __future__ import annotations

from rdflib import RDF, RDFS, Graph
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


def _md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    def esc(cell: str) -> str:
        return cell.replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(esc(c) for c in row) + " |" for row in rows]
    return out


def compile_brief(graph: Graph, *, base: str) -> str:
    """Render the mapping to a deterministic Markdown brief."""
    lines: list[str] = []
    syntheses = sorted(graph.subjects(RDF.type, CDS.Synthesis), key=str)
    title = _label(graph, syntheses[0]) if syntheses else "Concept Definition"
    lines.append(f"# {title}")
    lines.append("")
    lines.append("*Concept Definition — Business Analysis & Stakeholder Needs*")
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
            lines.append(f"- **{_label(graph, s)}** — {_desc(graph, s)}{extra}")
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
            lines.append(f"- **{_label(graph, s)}** — {_desc(graph, s)}{suffix}")
        lines.append("")

    # ---- side ledgers
    _section(lines, graph, CDS.Tension, "Tensions")
    _section(lines, graph, CDS.ParkedItem, "Parking-lot")
    _queue_section(lines, graph)

    return "\n".join(lines).rstrip("\n") + "\n"


def _section(lines: list[str], graph: Graph, cls: Node, heading: str) -> None:
    items = sorted(graph.subjects(RDF.type, cls), key=str)
    if not items:
        return
    lines.append(f"## {heading}")
    lines.append("")
    for s in items:
        desc = _desc(graph, s)
        lines.append(f"- **{_label(graph, s)}**" + (f" — {desc}" if desc else ""))
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
