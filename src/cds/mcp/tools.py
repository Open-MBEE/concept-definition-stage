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

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from rdflib import Graph

from cds.contracts import ConformanceOracle, InProcessOracle
from cds.core import compile as compile_mod
from cds.core import explain as explain_mod
from cds.core.authoring import (
    create_parked,
    create_queue_item,
    create_record,
    create_synthesis,
    create_tension,
    edit_record,
    list_records,
    project_graph,
    set_queue_status,
    set_tension_status,
    show_record,
)
from cds.core.model.instances import Record, Synthesis, model_for_kind
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
        TOOLS[name] = ToolSpec(name=name, fn=fn, description=description, mode=mode)
        return fn

    return register


def registered() -> tuple[str, ...]:
    """The names this registry actually holds — the served manifest derives from this."""
    return tuple(TOOLS)


def _staging_graph(project: Project) -> Graph:
    return project_graph(project)


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


@_tool("cds_list", "List records of a kind in the session staging project (slug, label).")
def cds_list(project: Project, kind: str) -> list[tuple[str, str]]:
    from cds.core.model.instances import AUTHORABLE_KINDS

    if kind not in AUTHORABLE_KINDS:
        # F-6: the error teaches the vocabulary instead of leaking a KeyError
        raise ValueError(
            f"unknown kind {kind!r}; expected one of {', '.join(AUTHORABLE_KINDS)}"
        )
    return list_records(project, kind)


@_tool("cds_show", "Show one staged record by kind and slug.")
def cds_show(project: Project, kind: str, slug: str) -> list[str] | None:
    return show_record(project, kind, slug)


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
    return str(create_record(project, rec))


@_tool("cds_edit", "Edit an EXISTING staged record in place (scratch mode); refuses an "
                   "absent slug — use cds_new to create one.", mode=ToolMode.SCRATCH)
def cds_edit(project: Project, kind: str, slug: str, label: str, description: str,
             synthesis: str, **fields: object) -> str:
    rec = _validated_record(kind, slug, label, description, synthesis, fields)
    return str(edit_record(project, rec))


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


@_tool("cds_commit", "Merge staging into canonical (K2 gate; requires cds-reviewer).",
       mode=ToolMode.COMMIT)
def cds_commit(project: Project) -> None:
    # The sole path to canonical state. Registered (it is in the K1 whitelist) but the
    # approver-gated merge + full verify is P2's commit gate — until then it refuses.
    raise PermissionError(  # F-7: the refusal speaks to the user, not the roadmap
        "committing requires the cds-reviewer role and an approved change plan; the commit "
        "gate is not enabled in this build. Your candidates remain safely in session "
        "staging — nothing is lost. Ask a reviewer to commit once the gate is available."
    )
