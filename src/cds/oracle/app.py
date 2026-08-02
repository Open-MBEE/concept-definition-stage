"""The conformance-oracle FastAPI app — stateless ``/verify`` over the model family.

FastAPI is imported lazily inside :func:`build_app`/:func:`main` so this module imports (for
autodoc, tests, and lean installs) without the ``oracle`` extra. The oracle consults
:class:`cds.contracts.InProcessOracle` — the same seam every in-process consumer uses — and
never authors or stores anything.
"""

from typing import Any

from pydantic import BaseModel

from cds.contracts import InProcessOracle
from cds.core.verify import Finding, Severity, VerifyResult


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


_CONFLICT_MESSAGES: dict[str, str] = {
    "NeedFormShall": "a need uses 'shall' — write it in need-form (requirements come later)",
    "NeedWithoutStakeholder": "a need is not linked to any stakeholder (orphan need)",
    "NeedServesNoGoal": "a need serves no goal it advances",
    "DuplicateStatement": "two current records share a semantic type and normalized statement",
    "SynthesisWithoutNeeds": "a mapping has no needs yet (integrated set is empty)",
    "DanglingReference": "a link points at a record that doesn't exist",
    "ReferenceToRetracted": "a current record references a retracted one",
    "DivergingPositions": "stakeholder positions on the same subject diverge "
                          "(all retained; divergence is valid)",
}


def _rules() -> list[dict[str, str]]:
    """Every known rule with its tier and message — the remediation cross-reference (G-8).

    Named SHACL shapes carry their authored ``sh:message``; the cross-record conflict
    checks carry the short descriptions above. Tier comes from
    :func:`cds.core.verify.rule_severities`.
    """
    from rdflib import RDF, URIRef
    from rdflib.namespace import SH

    from cds.core.verify import load_shapes, rule_severities

    shapes = load_shapes()
    messages: dict[str, str] = dict(_CONFLICT_MESSAGES)
    for cls in (SH.NodeShape, SH.PropertyShape):
        for s in shapes.subjects(RDF.type, cls):
            if not isinstance(s, URIRef):
                continue
            name = str(s).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            msg = shapes.value(s, SH.message)
            messages.setdefault(name, str(msg) if msg is not None else "")
    tier = {Severity.VIOLATION: "T1", Severity.WARNING: "T2", Severity.INFO: "T3"}
    return sorted(
        ({"rule": name, "tier": tier[sev], "message": messages.get(name, "")}
         for name, sev in rule_severities(shapes).items()),
        key=lambda r: r["rule"],
    )


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
    rules = _rules()  # warm — shapes parsed once at build

    @app.post("/verify")
    def verify_instance(req: VerifyRequest) -> dict[str, Any]:
        g = Graph()
        try:
            g.parse(data=req.turtle, format="turtle")
        except Exception as exc:  # granular remediation starts at syntax
            raise HTTPException(status_code=400, detail=f"turtle parse error: {exc}") from exc
        return _result_json(oracle.check(g, check_conflicts=req.check_conflicts))

    @app.get("/rules")
    def list_rules() -> dict[str, list[dict[str, str]]]:
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
