"""The conformance-oracle FastAPI app — stateless ``/verify`` over the model family.

FastAPI is imported lazily inside :func:`build_app`/:func:`main` so this module imports (for
autodoc, tests, and lean installs) without the ``oracle`` extra. The oracle consults
:class:`cds.contracts.InProcessOracle` — the same seam every in-process consumer uses — and
never authors or stores anything.
"""

from typing import Any

from pydantic import BaseModel

from cds.contracts import InProcessOracle
from cds.core.verify import Finding, VerifyResult


class VerifyRequest(BaseModel):
    """One model instance to check: Turtle text + whether to run cross-record checks."""

    turtle: str
    check_conflicts: bool = True


def _finding_json(f: Finding) -> dict[str, str]:
    return {"tier": f.tier, "severity": f.severity.value, "rule": f.rule,
            "focus": f.focus, "message": f.message}


def _result_json(result: VerifyResult) -> dict[str, Any]:
    return {"conforms": result.conforms,
            "findings": [_finding_json(f) for f in result.findings]}


def _rule_names() -> list[str]:
    """The named shapes — the stable ``rule`` identities findings refer to (remediation
    cross-reference), plus the cross-record conflict checks not expressible per-record."""
    from rdflib import RDF
    from rdflib.namespace import SH

    from cds.core.verify import load_shapes

    shapes = load_shapes()
    named = {str(s).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
             for s in shapes.subjects(RDF.type, SH.NodeShape)}
    conflict_checks = {"NeedFormShall", "NeedWithoutStakeholder", "NeedServesNoGoal",
                       "DuplicateStatement", "SynthesisWithoutNeeds", "DanglingReference"}
    return sorted(named | conflict_checks)


def build_app() -> Any:
    """Build the FastAPI app (lazy import; stateless — no project binding)."""
    from fastapi import FastAPI, HTTPException
    from rdflib import Graph

    app = FastAPI(
        title="cds conformance oracle",
        description="Model-instance conformance against the cds model family: verdict + "
                    "granular tri-severity findings (rule/focus/message) for remediation. "
                    "Verification only — validation (fitness for purpose) is human.",
        version="0.1.0",
    )
    oracle = InProcessOracle()
    rules = _rule_names()  # warm — shapes parsed once at build

    @app.post("/verify")
    def verify_instance(req: VerifyRequest) -> dict[str, Any]:
        g = Graph()
        try:
            g.parse(data=req.turtle, format="turtle")
        except Exception as exc:  # granular remediation starts at syntax
            raise HTTPException(status_code=400, detail=f"turtle parse error: {exc}") from exc
        return _result_json(oracle.check(g, check_conflicts=req.check_conflicts))

    @app.get("/rules")
    def list_rules() -> dict[str, list[str]]:
        return {"rules": rules}

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def main() -> None:
    import argparse

    import uvicorn

    ap = argparse.ArgumentParser(
        prog="cds-oracle",
        description="cds model-conformance oracle — stateless /verify, /rules, /healthz.",
    )
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind address (loopback by default; authn arrives at P6).")
    ap.add_argument("--port", type=int, default=8801)
    args = ap.parse_args()
    uvicorn.run(build_app(), host=args.host, port=args.port)
