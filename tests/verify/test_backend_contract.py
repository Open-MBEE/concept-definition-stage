"""ADR-7c — the verify() contract is frozen; pyshacl is the reference backend."""
import inspect

from cds.core import verify


def test_verify_signature_is_frozen_contract() -> None:
    params = list(inspect.signature(verify.verify).parameters)
    assert params[0] == "data"
    assert {"shapes", "waivers", "check_conflicts"}.issubset(params)


def test_pyshacl_backend_is_defined() -> None:
    # VB.1: swappable VerifierBackend Protocol + PyShaclBackend default (P0/P1). Red until refactor.
    from cds.core.verify import PyShaclBackend  # noqa: F401
