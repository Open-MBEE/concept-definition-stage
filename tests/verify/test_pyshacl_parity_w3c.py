"""VB.1 — the backend parity harness (spec §8.2 / ADR-7c): closes the P0 gap.

Every registered :class:`~cds.core.verify.VerifierBackend` must produce the SAME verdicts on
the SAME conformance cases before it is trusted for any shape. Today the only backend is
``PyShaclBackend`` (the reference); when a second engine registers in ``BACKENDS``, this file
becomes the differential gate *by construction* — no new tests needed, spec §11 D1.

Two layers:

1. **Local conformance cases** (below) — deterministic, offline, vendored; modeled on the
   W3C data-shapes test-suite structure (data graph + shapes graph + expected verdict) and
   covering the constraint components cds's shapes actually use: class/datatype/minCount,
   the three severity levels (T1/T2/T3 mapping), ``sh:sparql`` with ``sh:prefixes``
   (``advanced=True``), and targeted validation (``focus``).
2. **Full W3C suite** (``test_full_w3c_suite``) — skip-unless-fetched; the suite is NOT
   vendored (network-gated, same discipline as the canon PDFs). Fetch with::

       git clone --depth 1 https://github.com/w3c/data-shapes tests/verify/w3c-data-shapes

Differential rule: for each case, every backend's ``(conforms, sorted finding severities)``
must equal the expected verdict AND the reference backend's actual output.
"""
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import SH

from cds.core.verify import PyShaclBackend, RawReport, VerifierBackend

# The registry: a future Rust/SPARQL-on-Oxigraph engine registers here (and ONLY here).
BACKENDS: dict[str, VerifierBackend] = {
    "pyshacl": PyShaclBackend(),  # reference implementation
}
REFERENCE = "pyshacl"

_PREFIXES = """\
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""

# case: (name, data ttl, shapes ttl, expected conforms, expected severity multiset)
CASES: list[tuple[str, str, str, bool, tuple[str, ...]]] = [
    (
        "class-violation-is-T1",
        _PREFIXES + """
ex:bob a ex:Person ; ex:knows ex:notAPerson .
""",
        _PREFIXES + """
ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:property [ sh:path ex:knows ; sh:class ex:Person ;
                  sh:message "knows must point at a Person" ] .
""",
        False,
        (str(SH.Violation),),
    ),
    (
        "min-count-missing-required",
        _PREFIXES + """
ex:bob a ex:Person .
""",
        _PREFIXES + """
ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:property [ sh:path ex:name ; sh:minCount 1 ; sh:datatype xsd:string ] .
""",
        False,
        (str(SH.Violation),),
    ),
    (
        "datatype-conforming",
        _PREFIXES + """
ex:bob a ex:Person ; ex:name "Bob" .
""",
        _PREFIXES + """
ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:property [ sh:path ex:name ; sh:minCount 1 ; sh:datatype xsd:string ] .
""",
        True,
        (),
    ),
    (
        "warning-severity-does-not-fail",
        _PREFIXES + """
ex:bob a ex:Person .
""",
        _PREFIXES + """
ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:property [ sh:path ex:nickname ; sh:minCount 1 ; sh:severity sh:Warning ;
                  sh:message "nickname is recommended" ] .
""",
        True,  # warnings never touch conforms (allow_warnings) — the T2 doctrine
        (str(SH.Warning),),
    ),
    (
        "info-severity-does-not-fail",
        _PREFIXES + """
ex:bob a ex:Person .
""",
        _PREFIXES + """
ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:property [ sh:path ex:bio ; sh:minCount 1 ; sh:severity sh:Info ] .
""",
        True,
        (str(SH.Info),),
    ),
    (
        "sparql-constraint-advanced-mode",
        _PREFIXES + """
ex:bob a ex:Person ; ex:start "2020-01-01"^^xsd:date ; ex:end "2019-01-01"^^xsd:date .
""",
        _PREFIXES + """
ex:sparqlPrefixes sh:declare [ sh:prefix "ex" ; sh:namespace "http://example.org/"^^xsd:anyURI ] .
ex:IntervalShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:sparql [ a sh:SPARQLConstraint ;
        sh:message "end must not precede start" ;
        sh:prefixes ex:sparqlPrefixes ;
        sh:select \"\"\"SELECT $this
            WHERE { $this ex:start ?s ; ex:end ?e . FILTER (?e < ?s) }\"\"\" ] .
""",
        False,  # requires advanced=True — a backend without sh:sparql support fails here
        (str(SH.Violation),),
    ),
]


def _severities(report: Graph) -> tuple[str, ...]:
    return tuple(sorted(str(o) for o in report.objects(None, SH.resultSeverity)))


@pytest.mark.parametrize("backend_name", sorted(BACKENDS))
@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_backend_conformance_case(
    backend_name: str, case: tuple[str, str, str, bool, tuple[str, ...]]
) -> None:
    name, data_ttl, shapes_ttl, want_conforms, want_severities = case
    backend = BACKENDS[backend_name]
    raw = backend.validate(Graph().parse(data=data_ttl, format="turtle"),
                           Graph().parse(data=shapes_ttl, format="turtle"))
    assert isinstance(raw, RawReport)
    assert raw.conforms is want_conforms, f"{backend_name} disagrees on {name}"
    assert _severities(raw.report) == tuple(sorted(want_severities))


@pytest.mark.parametrize("backend_name", sorted(set(BACKENDS) - {REFERENCE}))
@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_backend_differential_vs_reference(
    backend_name: str, case: tuple[str, str, str, bool, tuple[str, ...]]
) -> None:
    """Every non-reference backend must match pyshacl's canonicalized output exactly.

    Collected only when a second backend registers — the drop-in gate of spec §11 D1.
    """
    name, data_ttl, shapes_ttl, _, _ = case
    data, shapes = (Graph().parse(data=data_ttl, format="turtle"),
                    Graph().parse(data=shapes_ttl, format="turtle"))
    ref = BACKENDS[REFERENCE].validate(data, shapes)
    got = BACKENDS[backend_name].validate(data, shapes)
    assert (got.conforms, _severities(got.report)) == (ref.conforms, _severities(ref.report)), (
        f"{backend_name} diverges from {REFERENCE} on {name}"
    )


def test_targeted_focus_validation() -> None:
    """The targeting seam P2's staging-delta verify relies on: focus limits the check."""
    data = Graph().parse(data=_PREFIXES + """
ex:bob a ex:Person .
ex:alice a ex:Person ; ex:name "Alice" .
""", format="turtle")
    shapes = Graph().parse(data=_PREFIXES + """
ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:property [ sh:path ex:name ; sh:minCount 1 ] .
""", format="turtle")
    backend = BACKENDS[REFERENCE]
    assert backend.validate(data, shapes).conforms is False  # bob fails globally
    focused = backend.validate(data, shapes, focus=["http://example.org/alice"])
    assert focused.conforms is True  # alice alone conforms — bob out of focus


W3C_SUITE = Path(__file__).parent / "w3c-data-shapes"


@pytest.mark.skipif(not W3C_SUITE.exists(), reason=(
    "full W3C data-shapes suite not fetched (network-gated, not vendored): "
    "git clone --depth 1 https://github.com/w3c/data-shapes tests/verify/w3c-data-shapes"
))
def test_full_w3c_suite() -> None:  # pragma: no cover — opt-in, network-fetched
    manifests = list(W3C_SUITE.glob("data-shapes-test-suite/tests/**/manifest.ttl"))
    assert manifests, "suite fetched but no manifests found — layout changed?"
    # Full manifest-driven execution lands with the first non-reference backend (D1);
    # presence + parse of the manifests is the P0-gap-closing hook.
    for m in manifests[:5]:
        Graph().parse(m, format="turtle")
