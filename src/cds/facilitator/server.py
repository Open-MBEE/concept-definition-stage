"""`cds-serve` — the facilitation (correct-by-construction authoring) API (spec §6.0 C3).

The facilitator service *creates* conforming models, where the oracle only checks them: it
mounts the transport-neutral K1 tool registry (``cds.mcp.tools``) as HTTP routes over a bound
session staging :class:`~cds.core.workspace.Project`. The posture is "e-bike-style"
facilitation — the human steers, the service assists:

* every write is Pydantic-gated and lands as a **candidate** in staging (never canonical);
* verification is **advisory while composing** (graded strictness) — only the commit gate
  blocks, and ``cds_commit`` refuses until P2's human-validated K2 gate;
* ``cds_queue_add`` is the mandated dead-end on unsecured canon (escalate, never invent).

The P4 AICC/LLM sidecar is a UX affordance layered over this same API. FastAPI/uvicorn (and
P4's LLM deps) are imported lazily so this module imports without the ``facilitator`` extra.
"""

from __future__ import annotations

import inspect
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, get_type_hints

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from cds.core import usertext
from cds.core.authoring import (
    AlreadyRetractedError,
    RecordExistsError,
    RecordNotFoundError,
)
from cds.core.workspace import Project
from cds.mcp import server as mcp_server
from cds.mcp import tools as mcp_tools

#: Per-field schema descriptions (LARP#2: the contract should be self-serve).
_FIELD_DESCRIPTIONS: dict[str, str] = {
    "kind": "Record kind: mission, goal, objective, driver, constraint, moe, problem, "
            "opportunity, stakeholder, need, or position.",
    "slug": "Short kebab-case id for this record (e.g. 'reach-a-human').",
    "label": "Short human name.",
    "description": "The content statement (for a position: the stance rationale).",
    "synthesis": "Slug of the parent mapping ('mapping' and 'synthesis' name the same "
                 "container; create it first with cds_synthesis).",
    "title": "Human title of the mapping.",
    "cites": "Source IRIs for provenance.",
    "supersedes": "Record(s) this one replaces in the durable record: bare slug "
                  "(same kind) or full IRI; the old record is marked superseded, not deleted.",
    "for_stakeholder": "need → stakeholder slug(s).",
    "serves_goal": "need → goal slug(s).",
    "refines": "objective → goal slug(s).",
    "addresses": "goal → problem/opportunity slug(s).",
    "segment": "stakeholder segment/perspective.",
    "interest": "stakeholder interest.",
    "influence": "stakeholder influence.",
    "characterizes": "position → '<kind>/<slug>' of the record this stance reads "
                     "(e.g. 'objective/coverage').",
    "held_by": "position → stakeholder slug holding the stance.",
    "stance": "position → one of: supports, opposes, prioritizes, constrains, reads-as.",
    "invariance": "position → what this reading holds constant.",
    "reason": "Why (recorded verbatim, append-only).",
    "question": "The open question to resolve later.",
    "status": "Retrieval status: pending, provided, or verified.",
    "locator": "Where the answer was found.",
    "note": "Free-form note.",
    "between": "IRIs of the records in tension.",
    "waiver_id": "IRI identifying this waiver (append-only ledger entry).",
    "rule": "The verify rule (check name) being waived. Pass an unknown name to list "
            "the valid ones; the separate conformance-oracle service describes each "
            "rule at its /rules endpoint.",
    "focus": "Optional focus node the waiver is scoped to.",
    "by": "Operator IRI accepting the waiver.",
    "check_conflicts": "Also run the cross-record consistency checks.",
    "include_history": "Append the 'Superseded & retracted' section (off by default).",
}


def _request_model(spec: mcp_tools.ToolSpec) -> type[BaseModel]:
    """Derive the route's request model from the tool's signature (minus ``project``).

    Every field — including the per-kind record fields — is an explicit named parameter
    on the tool itself (B1, live-QA 2026-08-02), so the OpenAPI contract never lies by
    omission (LARP F-1) and MCP/HTTP schemas derive from the one signature."""
    hints = get_type_hints(spec.fn)
    fields: dict[str, Any] = {}
    for name, param in inspect.signature(spec.fn).parameters.items():
        if name == "project":
            continue
        annotation = hints.get(name, object)
        default = ... if param.default is inspect.Parameter.empty else param.default
        fields[name] = (annotation,
                        Field(default, description=_FIELD_DESCRIPTIONS.get(name)))
    return create_model(f"{spec.name}_args", __config__=ConfigDict(extra="forbid"),
                        **fields)


def _jsonable(result: object) -> Any:
    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)
    if result is None or isinstance(result, str | int | float | bool | list | tuple | dict):
        return result
    return str(result)


class ChatRequest(BaseModel):
    """One user message to the AICC facilitator (P4)."""

    message: str


def build_app(project: Project, llm: Any = None) -> Any:
    """Build the FastAPI app over the registry for one session project (lazy import).

    ``llm`` is an optional :class:`~cds.facilitator.decode.LLMBackend`; when absent the
    ``/chat`` route answers 503 with the ADR-8 configuration hint (the tool routes are
    fully usable either way — the LLM is an affordance, not the substance).
    """
    from fastapi import FastAPI, HTTPException

    served = mcp_server.list_tools()  # manifest drift guard — same refusal as cds-mcp
    app = FastAPI(
        title=usertext.FACILITATOR_TITLE,
        description=usertext.FACILITATOR_DESCRIPTION,
        version="0.1.0",
    )

    def _invoke(spec: mcp_tools.ToolSpec, payload: BaseModel) -> Any:
        try:
            return spec.fn(project, **payload.model_dump())
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (RecordExistsError, AlreadyRetractedError) as exc:  # conflicts
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except RecordNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except ValidationError as exc:
            errors = exc.errors(include_url=False, include_context=False,
                                include_input=False)
            raise HTTPException(status_code=422, detail=errors) from exc
        except KeyError as exc:  # absent target (e.g. discard/queue on a missing slug)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:  # last resort: structured, never a bare 500 (H-7)
            raise HTTPException(
                status_code=500,
                detail=f"internal error ({type(exc).__name__}): {exc}",
            ) from exc

    def _register(spec: mcp_tools.ToolSpec) -> None:
        model = _request_model(spec)

        # tool-call auditing happens at the REGISTRY (cds.mcp.tools), so every
        # invocation path is logged identically — the transport adds nothing here
        def endpoint(payload: BaseModel) -> Any:
            return _jsonable(_invoke(spec, payload))

        # Postponed annotations would leave the payload annotation as a string FastAPI
        # cannot resolve to this dynamic model — stamp the real class on at runtime.
        endpoint.__annotations__["payload"] = model
        app.post(f"/tools/{spec.name}", name=spec.name, description=spec.description,
                 operation_id=spec.name)(endpoint)

    for name in sorted(mcp_tools.TOOLS):  # sorted → deterministic OpenAPI
        _register(mcp_tools.TOOLS[name])

    chat_history: list[dict[str, Any]] = []

    @app.post("/chat")
    def chat(req: ChatRequest) -> dict[str, Any]:
        if llm is None:
            raise HTTPException(
                status_code=503,
                detail="no model is connected to this chat. Everything else works "
                       "without one; ask whoever runs this service to connect a model. "
                       "The /tools/* routes "
                       "work without one",
            )
        from cds.facilitator.aicc import run_turn

        result = run_turn(req.message, project=project, backend=llm,
                          history=list(chat_history))
        chat_history.append({"role": "user", "content": req.message})
        chat_history.append({"role": "assistant", "content": result.reply})
        return {
            "reply": result.reply,
            "executed": [{"tool": c.name, "arguments": c.arguments}
                         for c in result.executed],
            "refused": [{"tool": c.name, "reason": c.reason} for c in result.refused],
            "escalated": result.escalated,
        }

    @app.get("/manifest")
    def manifest() -> dict[str, Any]:
        # staged_count: drafts are in-memory-session-only until a reviewer commits
        # (live-QA 2026-08-02, Step 2) — a UI shows "N staged" so nobody assumes
        # in-progress work is persisted.
        from rdflib import RDF

        from cds.core.authoring import project_graph
        from cds.core.namespaces import CDS

        g = project_graph(project)
        staged = set(g.subjects(RDF.type, CDS.Instance))
        staged |= set(g.subjects(RDF.type, CDS.Synthesis))
        return {"tools": served, "staged_count": len(staged),
                "staging_note": usertext.STAGED_COUNT_NOTE}

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def resolve_session(project: Path | None, canonical: Path | None,
                    roles: list[str] | None, approver: str | None) -> Project:
    """Bind the session (P2): explicit scratch root, or a fresh overlay session over
    ``--canonical``, or plain cwd discovery. Roles/approver are OPERATOR configuration —
    never caller-claimable (K2)."""
    from cds.core.workspace import load_project
    from cds.mcp import staging, tools

    canon = load_project(explicit=canonical) if canonical is not None else None
    tools.SESSION.canonical = canon
    tools.SESSION.roles = frozenset(roles or ())
    tools.SESSION.approver = approver
    if project is not None:
        return load_project(explicit=project)
    if canon is not None:
        return staging.new_session_project(canon.base_iri)  # fresh isolated session (F-5)
    return load_project()


def main() -> None:
    import argparse

    import uvicorn

    ap = argparse.ArgumentParser(
        prog="cds-serve",
        description="cds facilitation API: the fixed cds tool set as HTTP routes over a "
                    "session staging project; writes are candidates, the commit gate is human.",
    )
    ap.add_argument("--project", type=Path, default=None,
                    help="Explicit staging root (default: fresh session when --canonical "
                         "is given, else CDS_PROJECT / cwd discovery).")
    ap.add_argument("--canonical", type=Path, default=None,
                    help="Canonical record root; enables the overlay read model and the "
                         "commit gate.")
    ap.add_argument("--role", action="append", default=None,
                    help="Grant a role to this session (repeatable), e.g. cds-reviewer. "
                         "Operator configuration until P6 auth.")
    ap.add_argument("--approver", default=None,
                    help="Approver IRI recorded on committed change plans.")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind address (loopback by default; authn arrives at P6).")
    ap.add_argument("--port", type=int, default=8800)
    args = ap.parse_args()
    session = resolve_session(args.project, args.canonical, args.role, args.approver)
    from cds.facilitator.decode import LLMConfig, OpenAICompatBackend
    from cds.mcp import tools as _tools

    cfg = LLMConfig.from_env()
    backend = OpenAICompatBackend(cfg) if cfg is not None else None
    if cfg is not None:
        _tools.SESSION.model = cfg.model  # provenance: commits record the mediating model
    uvicorn.run(build_app(session, llm=backend), host=args.host, port=args.port)
