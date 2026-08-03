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
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cds.mcp.provenance import AuditLog

from rdflib import RDF, Graph, Literal, URIRef

from cds.core.authoring import (
    mark_superseded,
    merge_subject_graph,
    project_graph,
    retract_record,
)
from cds.core.namespaces import CDS, PROV
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
    # S1 (live-QA 2026-08-02): unresolved-citation records, held until the source is
    # secured or the approver includes them explicitly (include_unverified)
    held_unverified: tuple[URIRef, ...] = ()
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


def _matches_include(subject: URIRef, include: Sequence[str]) -> bool:
    """An approver names a record by full IRI or by its ``kind/slug`` tail."""
    text = str(subject)
    return any(text == inc or text.endswith("/" + inc.lstrip("/")) for inc in include)


def plan_commit(staging: Project, canonical: Project, *,
                include_unverified: Sequence[str] = ()) -> ChangePlan:
    """Diff the staging overlay against the canonical record into a :class:`ChangePlan`.

    Records with unresolved citations are moved to ``held_unverified`` (S1): they enter
    the record only when the source is secured or the approver names them in
    ``include_unverified`` — an explicit, audited act.
    """
    from cds.core.verify import unresolved_citations
    from cds.mcp.staging import union_graph

    staged_full = project_graph(staging)
    canon = project_graph(canonical)
    union = union_graph(staging, canonical)
    _kept, held = filter_held_out(union)
    held_in_staging = tuple(h for h in held if (h, None, None) in staged_full)
    unverified = tuple(sorted(
        {subj for subj, _cited in unresolved_citations(staged_full, union)
         if not _matches_include(subj, include_unverified)}, key=str))

    adds: list[URIRef] = []
    revisions: list[URIRef] = []
    supersessions: list[tuple[URIRef, URIRef]] = []
    retractions: list[URIRef] = []

    subjects = set(staged_full.subjects(RDF.type, CDS.Instance))
    subjects |= set(staged_full.subjects(RDF.type, CDS.Synthesis))
    for s in sorted(subjects, key=str):
        if not isinstance(s, URIRef) or s in held_in_staging or s in unverified:
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
        held=held_in_staging, held_unverified=unverified,
        content_hash=_staging_hash(staged_full),
    )


def render_plan(plan: ChangePlan) -> str:
    """The plan as a deterministic artifact — what the approver confirmed, on the record."""
    def names(items: tuple[URIRef, ...]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "- (none)"

    supers = "\n".join(f"- {old} → {new}" for old, new in plan.supersessions) or "- (none)"
    return (
        "# Change plan\n\n"
        f"content-hash: `{plan.content_hash}`\n"
        "(preimage: SHA-256 over the staging graph serialized as sorted N-Triples — "
        "recomputable by any auditor from the staged instance files)\n\n"
        f"approver: {plan.approver or '(unrecorded)'}\n\n"
        f"## Adds\n{names(plan.adds)}\n\n"
        f"## Revisions (approver-confirmed, same IRI; prior bytes preserved by git)\n"
        f"{names(plan.revisions)}\n\n"
        f"## Supersessions (old → new; inverse marker appended)\n{supers}\n\n"
        f"## Retractions (append-only markers)\n{names(plan.retractions)}\n\n"
        f"## Held out (X7 — cited source not verified; excluded, not fabricated around)\n"
        f"{names(plan.held)}\n\n"
        f"## Unverified sources (held — secure the source, or include explicitly with "
        f"include_unverified)\n{names(plan.held_unverified)}\n"
    )


def commit(
    staging_project: object,
    canonical: Project | None = None,
    *,
    approver_roles: frozenset[str],
    approver: str | None = None,
    plan: ChangePlan | None = None,
    model: str | None = None,
    include_unverified: Sequence[str] = (),
) -> ChangePlan:
    """Merge staging → canonical through the K2 gate; returns the executed plan.

    ``include_unverified`` names unresolved-citation records (full IRI or ``kind/slug``)
    the approver explicitly accepts despite the unsecured source (S1) — the override is
    recorded in the audit event.
    """
    if APPROVER_ROLE not in approver_roles:
        raise PermissionError(
            "committing requires the cds-reviewer role (K2: validation is human). "
            "Your staged candidates are preserved — ask a cds-reviewer to review and commit."
        )
    if canonical is None or not isinstance(staging_project, Project):
        raise ValueError("commit needs a staging Project and a canonical Project")

    fresh = plan_commit(staging_project, canonical,
                        include_unverified=include_unverified)
    if plan is not None and plan.content_hash != fresh.content_hash:
        raise PermissionError(
            "stale change plan: staging changed after approval "
            f"(approved {plan.content_hash[:12]}, now {fresh.content_hash[:12]}) — re-review"
        )
    executed = ChangePlan(
        adds=fresh.adds, revisions=fresh.revisions, supersessions=fresh.supersessions,
        retractions=fresh.retractions, held=fresh.held,
        held_unverified=fresh.held_unverified,
        content_hash=fresh.content_hash, approver=approver,
    )

    # full verify on the would-be merged current view (the commit is the assertion, §6.4).
    # OVERLAY union — the staged shadow wins per subject; a naive graph sum would give a
    # revised record two labels and falsely trip maxCount shapes (LARP#3 H-1).
    from cds.mcp.staging import union_graph

    staged_full = project_graph(staging_project)
    kept_staged, _ = filter_held_out(union_graph(staging_project, canonical))
    for subj in executed.held_unverified:  # held records are not part of this assertion
        kept_staged.remove((subj, None, None))
    merged_preview = current_view(kept_staged)
    result = verify(merged_preview, check_conflicts=True)
    if not result.conforms:
        details = "; ".join(f"{f.rule} on {f.focus}" for f in result.violations[:5])
        raise CommitBlockedError(f"unwaived T1 violations block the commit: {details}")

    # the plan is an artifact, not a screen — the write is attempted on every commit, but
    # the FIRST plan recorded for a content hash is the record (B2, live-QA 2026-08-02:
    # a no-op re-commit shares the hash and would clobber the real plan with empty
    # buckets, leaving the human-readable trail contradicting git/audit/provenance).
    plans_dir = canonical.root / "concept-definition" / "changeplans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plans_dir / f"{executed.content_hash[:12]}.md"
    if not plan_path.exists():  # append-only, same guard as the provenance record
        plan_path.write_text(render_plan(executed), encoding="utf-8")

    if not executed.empty:
        _write_provenance(canonical, staging_project, executed, model=model)

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

    event: dict[str, object] = {
        "action": "commit", "content_hash": executed.content_hash,
        "approver": approver or "urn:cds:agent:unattributed",
        "adds": len(executed.adds), "revisions": len(executed.revisions),
        "supersessions": len(executed.supersessions),
        "retractions": len(executed.retractions), "held": len(executed.held),
        "held_unverified": len(executed.held_unverified),
    }
    if include_unverified:  # S1: the approver's override is itself on the record
        event["include_unverified"] = sorted(include_unverified)
    _audit(canonical).append(event)
    _git_commit(canonical, executed)
    return executed


def _audit(canonical: Project) -> AuditLog:
    from cds.mcp.provenance import AuditLog as _AuditLog

    return _AuditLog(canonical.root / "concept-definition" / "audit.jsonl")


def _write_provenance(canonical: Project, staging: Project, plan: ChangePlan,
                      *, model: str | None) -> None:
    """One append-only PROV file per commit (K4.1) — activity keyed on the plan hash."""
    from cds import __version__
    from cds.core.serialize import canonical_turtle
    from cds.mcp.provenance import stamp

    activity_iri = f"{canonical.base_iri}activity/commit-{plan.content_hash[:12]}"
    generated = list(plan.adds) + list(plan.revisions)
    g = stamp(
        generated,
        user=plan.approver or "urn:cds:agent:unattributed",
        session=staging.root.name,
        model=model,
        version=__version__,
        activity_iri=activity_iri,
    )
    activity = URIRef(activity_iri)
    g.add((activity, CDS.changePlanHash, Literal(plan.content_hash)))
    for s in plan.retractions:
        g.add((s, PROV.wasInvalidatedBy, activity))
    for old, new in plan.supersessions:
        g.add((new, PROV.wasRevisionOf, old))
    prov_dir = canonical.root / "concept-definition" / "provenance"
    prov_dir.mkdir(parents=True, exist_ok=True)
    out = prov_dir / f"{plan.content_hash[:12]}.ttl"
    if out.exists():  # append-only: a provenance record is never rewritten
        return
    out.write_text(canonical_turtle(g, prefixes=_PROV_PREFIXES), encoding="utf-8")


_PROV_PREFIXES: dict[str, str] = {
    "cds": str(CDS),
    "prov": str(PROV),
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


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
