"""Typed wrappers over cds.core (authoring/verify/explain/compile) — the K1 tool boundary.

Each tool maps to one real cds function and produces CANDIDATES only (never canonical state):
every write goes through ``cds.core.authoring`` into the session staging ``Project`` passed as
the tool's first argument. ``cds_commit`` — the sole path to canonical state — refuses until the
K2 commit gate lands (P2).

This module is the **transport-neutral registry** (see docs/architecture/factoring.md): it is
mounted by both the MCP server (``cds.mcp.server``, stdio) and the facilitator service
(``cds.facilitator.server``, HTTP) and must never import a transport SDK (``mcp``,
``fastapi``) — that rule is enforced by ``tests/unit/test_factoring.py``.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from rdflib import RDF, RDFS, Graph

from cds.contracts import ConformanceOracle, InProcessOracle
from cds.core import compile as compile_mod
from cds.core import explain as explain_mod
from cds.core.authoring import (
    RecordExistsError,
    RecordNotFoundError,
    create_parked,
    create_queue_item,
    create_record,
    create_synthesis,
    create_tension,
    edit_record,
    merge_subject_graph,
    project_graph,
    set_queue_status,
    set_tension_status,
    show_record,
    upsert_record,
)
from cds.core.model.instances import (
    Record,
    Synthesis,
    model_for_kind,
    record_iri,
    type_iri_for_kind,
)
from cds.core.model.notes import (
    ParkedItem,
    RetrievalItem,
    RetrievalStatus,
    Tension,
    TensionStatus,
)
from cds.core.namespaces import CDS, DCTERMS, PROV
from cds.core.serialize import canonical_turtle
from cds.core.verify import (
    Finding,
    Severity,
    VerifyResult,
    Waiver,
    rule_severities,
    waiver_to_graph,
)
from cds.core.workspace import Project


class ToolMode(StrEnum):
    """The deontic mode of a tool (ADR-9) — served in the manifest.

    READ observes; SCRATCH mutates the working copy (create/edit/discard — nothing durable);
    APPEND expresses durable-record intent by only ever adding triples (retract, waive);
    COMMIT is the sole scratch→durable boundary.
    """

    READ = "read"
    SCRATCH = "scratch"
    APPEND = "append"
    COMMIT = "commit"


@dataclass(frozen=True)
class ToolSpec:
    """One whitelisted tool: its name, callable, human description, and deontic mode."""

    name: str
    fn: Callable[..., object]
    description: str
    mode: ToolMode

    @property
    def writes(self) -> bool:
        """Back-compat effect flag: anything other than READ writes somewhere."""
        return self.mode is not ToolMode.READ


TOOLS: dict[str, ToolSpec] = {}


def _tool(
    name: str, description: str, *, mode: ToolMode = ToolMode.READ
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    def register(fn: Callable[..., object]) -> Callable[..., object]:
        @functools.wraps(fn)  # preserves signature/annotations for schema derivation
        def audited(project: Project, *args: object, **kwargs: object) -> object:
            # K4 at the REGISTRY, not the transport (auditor finding K-5): every
            # invocation path — HTTP, MCP, in-process — lands in the session's
            # hash-chained audit log, refusals included.
            from cds.mcp.provenance import AuditLog

            log = AuditLog(project.root / "audit.jsonl")
            try:
                result = fn(project, *args, **kwargs)
            except Exception as exc:
                log.append({"action": "tool", "tool": name,
                            "status": type(exc).__name__})
                raise
            log.append({"action": "tool", "tool": name, "status": "ok"})
            return result

        audited.__signature__ = inspect.signature(fn)  # type: ignore[attr-defined]
        TOOLS[name] = ToolSpec(name=name, fn=audited, description=description, mode=mode)
        return fn

    return register


def registered() -> tuple[str, ...]:
    """The names this registry actually holds — the served manifest derives from this."""
    return tuple(TOOLS)


@dataclass
class SessionContext:
    """Operator-bound session state (P2): the canonical target, the caller's roles, and
    the approver IRI. Set at server start (``--canonical``/``--role``/``--approver``) —
    NEVER from tool arguments (roles are not caller-claimable, K2)."""

    canonical: Project | None = None
    roles: frozenset[str] = frozenset()
    approver: str | None = None


SESSION = SessionContext()


def _staging_graph(project: Project) -> Graph:
    """The session read model: staging over the canonical current view (sparse overlay)."""
    from cds.mcp.staging import union_graph

    return union_graph(project, SESSION.canonical)


def _in_canonical_current(kind: str, slug: str) -> bool:
    canon = SESSION.canonical
    if canon is None:
        return False
    from cds.core.view import is_current

    g = project_graph(canon)
    s = record_iri(canon.base_iri, kind, slug)
    return (s, None, None) in g and is_current(g, s)


# The verification seam (spec §8.3): tools consult the oracle via its contract, so the check
# can move out-of-process (cds-oracle service, D8) without touching this module.
_ORACLE: ConformanceOracle = InProcessOracle()


# ---------------------------------------------------------------------------- read / preview


@_tool("cds_explain", "Explain a cds concept or record kind (read-only guidance).")
def cds_explain(project: Project, name: str) -> list[str]:
    lines = explain_mod.explain(name)
    if lines is not None:
        return lines
    # F-11: never a bare null — teach what IS explainable
    return [f"unknown term {name!r} — explainable names:"] + explain_mod.glossary()


@_tool("cds_list", "List records of a kind visible to this session — staged candidates "
                   "overlaid on the canonical current view (slug, label).")
def cds_list(project: Project, kind: str) -> list[tuple[str, str]]:
    from cds.core.model.instances import AUTHORABLE_KINDS

    if kind not in AUTHORABLE_KINDS:
        # F-6: the error teaches the vocabulary instead of leaking a KeyError
        raise ValueError(
            f"unknown kind {kind!r}; expected one of {', '.join(AUTHORABLE_KINDS)}"
        )
    from cds.core.view import is_current

    g = _staging_graph(project)
    return sorted(
        (str(s).rsplit("/", 1)[-1], str(g.value(s, RDFS.label) or ""))
        for s in g.subjects(RDF.type, type_iri_for_kind(kind))
        if is_current(g, s)  # uniform current-view filtering (LARP#3 H-3)
    )


@_tool("cds_show", "Show one record visible to this session (staged copy wins).")
def cds_show(project: Project, kind: str, slug: str) -> list[str] | None:
    lines = show_record(project, kind, slug)
    if lines is None and SESSION.canonical is not None:
        lines = show_record(SESSION.canonical, kind, slug)
    return lines


@_tool("cds_verify", "Verify the staging graph — tri-severity findings; preview only.")
def cds_verify(project: Project, check_conflicts: bool = True) -> VerifyResult:
    return _ORACLE.check(_staging_graph(project), check_conflicts=check_conflicts)


@_tool("cds_compile", "Compile the staging graph to a Markdown brief; preview only. "
                      "Scope to one mapping with synthesis=<slug>; include_history adds "
                      "the superseded/retracted appendix.")
def cds_compile(project: Project, synthesis: str | None = None,
                include_history: bool = False) -> str:
    return compile_mod.compile_brief(_staging_graph(project), base=project.base_iri,
                                     synthesis=synthesis, include_history=include_history)


# ------------------------------------------------------------------- candidate writes (staging)


def _validated_record(kind: str, slug: str, label: str, description: str,
                      synthesis: str, fields: dict[str, object]) -> Record:
    """Pydantic (``model_for_kind``) is the structural guardrail — bad args raise an error."""
    payload: dict[str, object] = {"slug": slug, "kind": kind, "label": label,
                                  "description": description, "synthesis": synthesis, **fields}
    return model_for_kind(kind).model_validate(payload)


@_tool("cds_synthesis", "Create/update the Synthesis (candidate into staging).",
       mode=ToolMode.SCRATCH)
def cds_synthesis(project: Project, slug: str, title: str, description: str = "") -> str:
    return str(create_synthesis(project, Synthesis(slug=slug, title=title,
                                                   description=description)))


@_tool("cds_new", "Create a NEW record of a kind (candidate into staging); refuses an "
                  "existing slug — use cds_edit to change one.", mode=ToolMode.SCRATCH)
def cds_new(project: Project, kind: str, slug: str, label: str, description: str,
            synthesis: str, **fields: object) -> str:
    rec = _validated_record(kind, slug, label, description, synthesis, fields)
    if _in_canonical_current(kind, slug):  # existence consults the overlay union (P2-a)
        raise RecordExistsError(
            f"{kind} {slug!r} already exists in the canonical record — use cds_edit to "
            f"revise it, or a new slug with supersedes={slug!r} to replace it"
        )
    return str(create_record(project, rec))


@_tool("cds_edit", "Edit an EXISTING record (scratch mode; copies a canonical record on "
                   "write). REPLACES the whole record — restate every field you want to "
                   "keep, including links. Refuses an absent slug.", mode=ToolMode.SCRATCH)
def cds_edit(project: Project, kind: str, slug: str, label: str, description: str,
             synthesis: str, **fields: object) -> str:
    rec = _validated_record(kind, slug, label, description, synthesis, fields)
    try:
        return str(edit_record(project, rec))
    except RecordNotFoundError:
        if _in_canonical_current(kind, slug):
            # copy-on-write: the edited version becomes the staged shadow of the
            # canonical record; canonical is untouched until the commit gate (K2)
            return str(upsert_record(project, rec))
        raise


@_tool("cds_discard", "Delete a staged candidate or ledger item from the working copy — "
                      "scratch only, can never touch canonical state.", mode=ToolMode.SCRATCH)
def cds_discard(project: Project, kind: str, slug: str) -> dict[str, object]:
    from cds.core.authoring import (
        find_referrers,
        remove_parked,
        remove_queue_item,
        remove_record,
        remove_tension,
    )
    from cds.core.model.instances import record_iri

    if kind == "parked":
        removed = remove_parked(project, slug)
        referrers: list[str] = []
    elif kind == "queue":
        removed = remove_queue_item(project, slug)
        referrers = []
    elif kind == "tension":
        removed = remove_tension(project, slug)
        referrers = []
    else:
        target = record_iri(project.base_iri, kind, slug)
        referrers = [str(r) for r in find_referrers(project, target) if r != target]
        removed = remove_record(project, kind, slug)
    if not removed:
        raise KeyError(f"no {kind} {slug!r} to discard")
    return {"discarded": slug, "referrers": referrers}


@_tool("cds_retract", "Stage an append-only retraction (ADR-9): the record leaves the "
                      "current view; its content and history are preserved.",
       mode=ToolMode.APPEND)
def cds_retract(project: Project, kind: str, slug: str,
                reason: str | None = None) -> dict[str, object]:
    from cds.core.authoring import find_referrers, retract_record

    try:
        iri = retract_record(project, kind, slug, reason=reason)
    except RecordNotFoundError:
        if not _in_canonical_current(kind, slug):
            raise
        # copy-on-write: pull the canonical subject into staging, then stage the
        # retraction intent — canonical gets the marker only at the commit gate
        assert SESSION.canonical is not None
        target = record_iri(project.base_iri, kind, slug)
        merge_subject_graph(project, target, project_graph(SESSION.canonical))
        iri = retract_record(project, kind, slug, reason=reason)
    referrers = [str(r) for r in find_referrers(project, iri) if r != iri]
    return {"retracted": str(iri), "referrers": referrers}


# --------------------------------------------------------------------------- session ledgers


@_tool("cds_queue_add", "File a retrieval item — the mandated dead-end on unsecured canon.",
       mode=ToolMode.SCRATCH)
def cds_queue_add(project: Project, slug: str, question: str, description: str = "") -> str:
    return str(create_queue_item(project, RetrievalItem(slug=slug, question=question,
                                                        description=description)))


@_tool("cds_queue_set", "Advance a retrieval item's status (pending/provided/verified).",
       mode=ToolMode.SCRATCH)
def cds_queue_set(project: Project, slug: str, status: str,
                  locator: str | None = None) -> None:
    set_queue_status(project, slug, RetrievalStatus(status), locator=locator)


@_tool("cds_park_add", "Park an out-of-scope idea (kept, not dropped).", mode=ToolMode.SCRATCH)
def cds_park_add(project: Project, slug: str, label: str, description: str = "",
                 note: str = "") -> str:
    return str(create_parked(project, ParkedItem(slug=slug, label=label,
                                                 description=description, note=note)))


@_tool("cds_tension_add", "Record a named tension between records (surfaced, not hidden).",
       mode=ToolMode.SCRATCH)
def cds_tension_add(project: Project, slug: str, label: str, description: str = "",
                    between: list[str] | None = None) -> str:
    return str(create_tension(project, Tension(slug=slug, label=label, description=description,
                                               between=between or [])))


@_tool("cds_tension_resolve", "Mark a tension resolved.", mode=ToolMode.SCRATCH)
def cds_tension_resolve(project: Project, slug: str) -> None:
    set_tension_status(project, slug, TensionStatus.RESOLVED)


# ------------------------------------------------------------------ waivers + the commit gate


def refuse_if_waives_t1(findings: Sequence[Finding], *, rule: str, focus: str | None) -> None:
    """T1 is never waivable — refuse any waiver that would select a live Violation."""
    for f in findings:
        if (f.severity is Severity.VIOLATION and f.rule == rule
                and (focus is None or focus == f.focus)):
            raise PermissionError(f"T1 is never waivable: {rule} on {f.focus}")


_WAIVER_PREFIXES: dict[str, str] = {
    "cds": str(CDS),
    "dcterms": str(DCTERMS),
    "prov": str(PROV),
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def _append_waiver(project: Project, addition: Graph) -> None:
    """Append-only waiver ledger: parse existing, merge, rewrite deterministically."""
    target = project.instances_dir / "waivers.ttl"
    g = Graph()
    if target.exists():
        g.parse(target, format="turtle")
    for triple in addition:
        g.add(triple)
    target.write_text(canonical_turtle(g, prefixes=_WAIVER_PREFIXES), encoding="utf-8")


@_tool("cds_waive", "Waive a T2/T3 finding with a reason (append-only; T1 refused).",
       mode=ToolMode.APPEND)
def cds_waive(project: Project, waiver_id: str, rule: str, reason: str,
              focus: str | None = None, by: str | None = None) -> str:
    known = rule_severities()
    if rule not in known:  # F-3: no dead waivers in an append-only ledger
        raise ValueError(f"unknown rule {rule!r} — known rules: {', '.join(sorted(known))}")
    if known[rule] is Severity.VIOLATION:  # F-3: T1-class refused even without a live finding
        raise PermissionError(f"T1 is never waivable: {rule} is a Violation-class rule")
    result = _ORACLE.check(_staging_graph(project), check_conflicts=True)
    refuse_if_waives_t1(result.findings, rule=rule, focus=focus)
    w = Waiver(id=waiver_id, rule=rule, reason=reason, focus=focus, by=by)
    _append_waiver(project, waiver_to_graph(w))
    return waiver_id


@_tool("cds_commit", "Merge staging into canonical through the K2 gate (requires the "
                     "cds-reviewer role bound at server start); returns the executed "
                     "change plan.", mode=ToolMode.COMMIT)
def cds_commit(project: Project) -> dict[str, object]:
    if SESSION.canonical is None:
        raise PermissionError(  # F-7: the refusal speaks to the user, not the roadmap
            "committing requires the cds-reviewer role and a canonical record bound at "
            "server start (--canonical); neither is configured here. Your candidates "
            "remain safely in session staging — nothing is lost."
        )
    # Lazy import — the K2 gate lives in the app tier (cds.app); module-level sibling
    # imports are forbidden by the factoring DAG, and this call-time seam is the
    # sanctioned crossing (same pattern as the transport SDKs).
    from cds.app.commit_gate import CommitBlockedError, commit

    try:
        plan = commit(project, SESSION.canonical,
                      approver_roles=SESSION.roles, approver=SESSION.approver)
    except CommitBlockedError as exc:
        # a verification-blocked commit is a teachable client-state error (H-1/H-7),
        # never an unmapped internal error
        raise ValueError(str(exc)) from exc
    return {
        "committed": not plan.empty,
        "content_hash": plan.content_hash,
        "adds": [str(s) for s in plan.adds],
        "revisions": [str(s) for s in plan.revisions],
        "supersessions": [[str(old), str(new)] for old, new in plan.supersessions],
        "retractions": [str(s) for s in plan.retractions],
        "held": [str(s) for s in plan.held],
    }
