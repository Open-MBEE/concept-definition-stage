"""Live OpenMBEE Flexo SysML v2 service smoke (roadmap T9 scaffold).

Auto-skips unless `FLEXO_SYSMLV2_URL` / `FLEXO_SYSMLV2_TOKEN` are set (see `.env.example`) AND the
Open-MBEE `sysmlv2-python-client` is installed. To run:

    pip install git+https://github.com/Open-MBEE/sysmlv2-python-client
    uv run --env-file .env pytest tests/interop/test_flexo_sysmlv2.py

The full T9 work — loading a SysML v2 corpus and joining it to the cds scheme via the equivalence
axioms — builds on this connectivity smoke.
"""

from __future__ import annotations

import os

import pytest


def _creds() -> tuple[str | None, str | None]:
    return os.environ.get("FLEXO_SYSMLV2_URL"), os.environ.get("FLEXO_SYSMLV2_TOKEN")


@pytest.mark.skipif(not all(_creds()), reason="FLEXO_SYSMLV2_* not set (see .env.example)")
def test_flexo_sysmlv2_service_is_reachable() -> None:
    sysmlv2_client = pytest.importorskip(
        "sysmlv2_client", reason="install the Open-MBEE sysmlv2-python-client (roadmap T9)"
    )
    url, token = _creds()
    assert url and token
    bearer = token if token.startswith("Bearer") else f"Bearer {token}"
    client = sysmlv2_client.SysMLV2Client(base_url=url, bearer_token=bearer)
    projects = client.get_projects()
    assert isinstance(projects, list)
