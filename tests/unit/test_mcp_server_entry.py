"""cds-mcp entrypoint: the manifest guard runs before serving; the SDK import is lazy.

``cds.mcp.server`` must import (and its manifest must check) without the ``mcp`` extra
installed — the SDK is loaded only inside ``build_server()``/``main()``.
"""
from pathlib import Path

import pytest

from cds.core.workspace import Project
from cds.mcp import server


def _staging(tmp_path: Path) -> Project:
    proj = Project(root=tmp_path / "session", base_iri="https://cds.example/p1/")
    proj.instances_dir.mkdir(parents=True)
    return proj


def test_module_imports_without_mcp_sdk() -> None:
    # Importing cds.mcp.server (done above) must not require the mcp SDK; the manifest
    # guard is pure-python and already enforceable.
    assert server.list_tools() == sorted(server.WHITELIST)


def test_build_server_serves_exactly_the_whitelist(tmp_path: Path) -> None:
    pytest.importorskip("mcp", reason="mcp extra not installed — lazy import verified")
    import anyio

    srv = server.build_server(_staging(tmp_path))
    served = {t.name for t in anyio.run(srv.list_tools)}
    assert served == set(server.WHITELIST)
