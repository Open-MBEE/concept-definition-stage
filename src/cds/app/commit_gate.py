"""Candidate → canonical commit gate (K2/ADR-6/ADR-9) — the ONLY crossing into the record.

The gate composes the authoring primitives (it contains no RDF-writing logic of its own):

1. **Role**: refused without ``cds-reviewer`` (K2 — validation is human).
2. **Plan**: every change is enumerated in a :class:`ChangePlan` — adds, approver-confirmed
   same-IRI revisions, supersessions (inverse markers appended), retraction intents, and
   held-out records (X7). The plan's ``content_hash`` binds it to the staging state; a
   stale plan is refused.
3. **Held-out (X7)**: a staged record citing an in-graph source with no verification is
   excluded from the merge and surfaced — never committed, never failing the whole commit.
4. **Verify**: the merged current view must be T1-clean (unwaived Violations block).
5. **Apply**: appends only — new/revised subjects merge deterministically; supersession and
   retraction land as markers; nothing in the durable record is ever deleted.
6. **Artifact**: the plan is written unconditionally on commit, named by its content hash,
   stamped with the approver IRI. If the canonical root is a git repo, the commit is
   recorded there too (git is the byte-level history, ADR-7a).

PROV-O stamping of the commit activity is P3 (:mod:`cds.mcp.provenance`).
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field

from rdflib import RDF, Graph, Literal, URIRef

from cds.core.authoring import (
    mark_superseded,
    merge_subject_graph,
    project_graph,
    retract_record,
)
from cds.core.namespaces import CDS
from cds.core.verify import verify
from cds.core.view import current_view
from cds.core.workspace import Project

APPROVER_ROLE = "cds-reviewer"


class CommitBlockedError(RuntimeError):
    """The merged record would carry unwaived T1 violations — the gate refuses."""


@dataclass(frozen=True)
class ChangePlan:
    """Every change one commit would make, enumerated for the approver."""

    adds: tuple[URIRef, ...] = ()
    revisions: tuple[URIRef, ...] = ()
    supersessions: tuple[tuple[URIRef, URIRef], ...] = ()  # (old, new)
    retractions: tuple[URIRef, ...] = ()
    held: tuple[URIRef, ...] = ()  # X7: excluded from this commit, surfaced
    content_hash: str = ""
    approver: str | None = field(default=None, compare=False)

    @property
    def empty(self) -> bool:
        return not (self.adds or self.revisions or self.supersessions or self.retractions)


def _staging_hash(staged: Graph) -> str:
    """Deterministic content hash of the staging graph (sorted N-Triples; prefix-free)."""
    lines = sorted(staged.serialize(format="nt").splitlines())
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def filter_held_out(graph: Graph) -> tuple[Graph, tuple[URIRef, ...]]:
    """X7 — hold out records citing an in-graph ``cds:Source`` with no verification.

    A cited source *present in the graph* and lacking ``cds:wasVerifiedBy`` marks its citing
    records as held: excluded from the commit (surfaced, never fabricated around, never
    failing the rest). External citations the graph knows nothing about pass through — the
    verbatim-in-M SHACL guard governs those.
    """
    held: set[URIRef] = set()
    pending_sources: set[URIRef] = set()
    for record in graph.subjects(RDF.type, CDS.Instance):
        if not isinstance(record, URIRef):
            continue
        for source in graph.objects(record, CDS.cites):
            if isinstance(source, URIRef) and (source, RDF.type, CDS.Source) in graph \
                    and (source, CDS.wasVerifiedBy, None) not in graph:
                held.add(record)
                pending_sources.add(source)  # the pending source rides with its records
    dropped = held | pending_sources
    kept = Graph()
    for s, p, o in graph:
        if s not in dropped:
            kept.add((s, p, o))
    return kept, tuple(sorted(held, key=str))


def _subject_triples(graph: Graph, subject: URIRef) -> frozenset[tuple[str, str]]:
    return frozenset((str(p), str(o)) for _s, p, o in graph.triples((subject, None, None)))


def plan_commit(staging: Project, canonical: Project) -> ChangePlan:
    """Diff the staging overlay against the canonical record into a :class:`ChangePlan`."""
    from cds.mcp.staging import union_graph

    staged_full = project_graph(staging)
    canon = project_graph(canonical)
    _kept, held = filter_held_out(union_graph(staging, canonical))
    held_in_staging = tuple(h for h in held if (h, None, None) in staged_full)

    adds: list[URIRef] = []
    revisions: list[URIRef] = []
    supersessions: list[tuple[URIRef, URIRef]] = []
    retractions: list[URIRef] = []

    subjects = set(staged_full.subjects(RDF.type, CDS.Instance))
    subjects |= set(staged_full.subjects(RDF.type, CDS.Synthesis))
    for s in sorted(subjects, key=str):
        if not isinstance(s, URIRef) or s in held_in_staging:
            continue
        in_canon = (s, None, None) in canon
        if (s, CDS.retracted, Literal(True)) in staged_full and in_canon:
            if (s, CDS.retracted, Literal(True)) not in canon:
                retractions.append(s)
            continue
        for old in staged_full.objects(s, CDS.supersedes):
            if isinstance(old, URIRef) and (old, None, None) in canon \
                    and (old, CDS.supersededBy, s) not in canon:
                supersessions.append((old, s))
        if not in_canon:
            adds.append(s)
        elif _subject_triples(staged_full, s) != _subject_triples(canon, s):
            revisions.append(s)

    return ChangePlan(
        adds=tuple(adds), revisions=tuple(revisions),
        supersessions=tuple(supersessions), retractions=tuple(retractions),
        held=held_in_staging, content_hash=_staging_hash(staged_full),
    )


def render_plan(plan: ChangePlan) -> str:
    """The plan as a deterministic artifact — what the approver confirmed, on the record."""
    def names(items: tuple[URIRef, ...]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "- (none)"

    supers = "\n".join(f"- {old} → {new}" for old, new in plan.supersessions) or "- (none)"
    return (
        "# Change plan\n\n"
        f"content-hash: `{plan.content_hash}`\n\n"
        f"approver: {plan.approver or '(unrecorded)'}\n\n"
        f"## Adds\n{names(plan.adds)}\n\n"
        f"## Revisions (approver-confirmed, same IRI; prior bytes preserved by git)\n"
        f"{names(plan.revisions)}\n\n"
        f"## Supersessions (old → new; inverse marker appended)\n{supers}\n\n"
        f"## Retractions (append-only markers)\n{names(plan.retractions)}\n\n"
        f"## Held out (X7 — cited source not verified; excluded, not fabricated around)\n"
        f"{names(plan.held)}\n"
    )


def commit(
    staging_project: object,
    canonical: Project | None = None,
    *,
    approver_roles: frozenset[str],
    approver: str | None = None,
    plan: ChangePlan | None = None,
) -> ChangePlan:
    """Merge staging → canonical through the K2 gate; returns the executed plan."""
    if APPROVER_ROLE not in approver_roles:
        raise PermissionError(
            "committing requires the cds-reviewer role (K2: validation is human). "
            "Your staged candidates are preserved — ask a cds-reviewer to review and commit."
        )
    if canonical is None or not isinstance(staging_project, Project):
        raise ValueError("commit needs a staging Project and a canonical Project")

    fresh = plan_commit(staging_project, canonical)
    if plan is not None and plan.content_hash != fresh.content_hash:
        raise PermissionError(
            "stale change plan: staging changed after approval "
            f"(approved {plan.content_hash[:12]}, now {fresh.content_hash[:12]}) — re-review"
        )
    executed = ChangePlan(
        adds=fresh.adds, revisions=fresh.revisions, supersessions=fresh.supersessions,
        retractions=fresh.retractions, held=fresh.held,
        content_hash=fresh.content_hash, approver=approver,
    )

    # full verify on the would-be merged current view (the commit is the assertion, §6.4).
    # OVERLAY union — the staged shadow wins per subject; a naive graph sum would give a
    # revised record two labels and falsely trip maxCount shapes (LARP#3 H-1).
    from cds.mcp.staging import union_graph

    staged_full = project_graph(staging_project)
    kept_staged, _ = filter_held_out(union_graph(staging_project, canonical))
    merged_preview = current_view(kept_staged)
    result = verify(merged_preview, check_conflicts=True)
    if not result.conforms:
        details = "; ".join(f"{f.rule} on {f.focus}" for f in result.violations[:5])
        raise CommitBlockedError(f"unwaived T1 violations block the commit: {details}")

    # the plan is an artifact, not a screen — written unconditionally, named by its hash
    plans_dir = canonical.root / "concept-definition" / "changeplans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    (plans_dir / f"{executed.content_hash[:12]}.md").write_text(
        render_plan(executed), encoding="utf-8")

    # apply — composes R2 primitives; appends only
    for s in executed.adds + executed.revisions:
        merge_subject_graph(canonical, s, staged_full)
    for old, new in executed.supersessions:
        rel = str(old)[len(canonical.base_iri):]
        kind, _, slug = rel.partition("/")
        mark_superseded(canonical, kind, slug, by=new)
    for s in executed.retractions:
        rel = str(s)[len(canonical.base_iri):]
        kind, _, slug = rel.partition("/")
        reason = staged_full.value(s, CDS.retractionReason)
        retract_record(canonical, kind, slug,
                       reason=str(reason) if reason is not None else None)

    _git_commit(canonical, executed)
    return executed


def _git_commit(canonical: Project, plan: ChangePlan) -> None:
    """Record the commit in git when the canonical root is a repo (ADR-7a); else no-op."""
    if not (canonical.root / ".git").exists() or plan.empty:
        return
    try:
        subprocess.run(["git", "-C", str(canonical.root), "add",
                        "concept-definition"], check=True, capture_output=True, timeout=30)
        subprocess.run(
            ["git", "-C", str(canonical.root), "commit", "-q",
             "-m", f"cds commit {plan.content_hash[:12]} "
                   f"(+{len(plan.adds)} ~{len(plan.revisions)} "
                   f"^{len(plan.supersessions)} -{len(plan.retractions)})"],
            check=True, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        # git recording is best-effort here; the deterministic TTL is already written
        return
