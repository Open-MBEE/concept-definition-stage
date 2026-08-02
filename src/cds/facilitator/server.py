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
from typing import Any, get_type_hints

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from cds.core.workspace import Project
from cds.mcp import server as mcp_server
from cds.mcp import tools as mcp_tools


def _kind_specific_fields() -> dict[str, tuple[Any, Any]]:
    """The union of per-kind record fields beyond the route's positional args — declared
    explicitly so the OpenAPI contract never lies by omission (LARP F-1)."""
    from pydantic_core import PydanticUndefined

    from cds.core.model.instances import KIND_TERM, model_for_kind

    handled = {"slug", "kind", "label", "description", "synthesis"}
    out: dict[str, tuple[Any, Any]] = {}
    for kind in sorted(KIND_TERM):
        for fname, finfo in model_for_kind(kind).model_fields.items():
            if fname in handled or fname in out:
                continue
            default = None if finfo.default is PydanticUndefined else finfo.default
            out[fname] = (finfo.annotation, default)
    return out


def _request_model(spec: mcp_tools.ToolSpec) -> type[BaseModel]:
    """Derive the route's request model from the tool's signature (minus ``project``)."""
    hints = get_type_hints(spec.fn)
    fields: dict[str, Any] = {}
    open_extras = False
    for name, param in inspect.signature(spec.fn).parameters.items():
        if name == "project":
            continue
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            open_extras = True  # cds_new/cds_edit kind-specific fields
            continue
        annotation = hints.get(name, object)
        default = ... if param.default is inspect.Parameter.empty else param.default
        fields[name] = (annotation, default)
    if open_extras:
        fields.update(_kind_specific_fields())
    config = ConfigDict(extra="allow" if open_extras else "forbid")
    return create_model(f"{spec.name}_args", __config__=config, **fields)


def _jsonable(result: object) -> Any:
    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)
    if result is None or isinstance(result, str | int | float | bool | list | tuple | dict):
        return result
    return str(result)


def build_app(project: Project) -> Any:
    """Build the FastAPI app over the registry for one session project (lazy import)."""
    from fastapi import FastAPI, HTTPException

    served = mcp_server.list_tools()  # manifest drift guard — same refusal as cds-mcp
    app = FastAPI(
        title="cds facilitator",
        description="Correct-by-construction authoring over the K1 tool whitelist: "
                    "Pydantic-gated candidate writes into session staging; advisory "
                    "verification while composing; the commit gate (K2, human) blocks.",
        version="0.1.0",
    )

    def _register(spec: mcp_tools.ToolSpec) -> None:
        model = _request_model(spec)

        def endpoint(payload: BaseModel) -> Any:
            try:
                result = spec.fn(project, **payload.model_dump())
            except PermissionError as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            except NotImplementedError as exc:
                raise HTTPException(status_code=501, detail=str(exc)) from exc
            except ValidationError as exc:
                errors = exc.errors(include_url=False, include_context=False,
                                    include_input=False)
                raise HTTPException(status_code=422, detail=errors) from exc
            except (ValueError, KeyError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            return _jsonable(result)

        # Postponed annotations would leave the payload annotation as a string FastAPI
        # cannot resolve to this dynamic model — stamp the real class on at runtime.
        endpoint.__annotations__["payload"] = model
        app.post(f"/tools/{spec.name}", name=spec.name, description=spec.description,
                 operation_id=spec.name)(endpoint)

    for name in sorted(mcp_tools.TOOLS):  # sorted → deterministic OpenAPI
        _register(mcp_tools.TOOLS[name])

    @app.get("/manifest")
    def manifest() -> dict[str, list[str]]:
        return {"tools": served}

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def main() -> None:
    import argparse
    from pathlib import Path

    import uvicorn

    from cds.core.workspace import load_project

    ap = argparse.ArgumentParser(
        prog="cds-serve",
        description="cds facilitation API — the K1 whitelist as HTTP routes over a session "
                    "staging project; writes are candidates, the commit gate is human.",
    )
    ap.add_argument("--project", type=Path, default=None,
                    help="Staging project root (default: CDS_PROJECT / cwd discovery).")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind address (loopback by default; authn arrives at P6).")
    ap.add_argument("--port", type=int, default=8800)
    args = ap.parse_args()
    uvicorn.run(build_app(load_project(explicit=args.project)),
                host=args.host, port=args.port)
