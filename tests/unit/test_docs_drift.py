"""Committed generated docs must regenerate byte-identically (determinism discipline).

The OpenAPI drift gates live with their services (`test_oracle_api.py`,
`test_facilitator_api.py`); this file gates the MCP manifest doc.
"""
from pathlib import Path

from cds.mcp import manifest_doc, server

DOCS = Path(__file__).parents[2] / "docs" / "services"


def test_mcp_manifest_doc_is_current() -> None:
    committed = (DOCS / "mcp-manifest.md").read_text(encoding="utf-8")
    assert committed == manifest_doc.manifest_markdown()


def test_manifest_doc_covers_whitelist() -> None:
    text = manifest_doc.manifest_markdown()
    assert all(f"`{name}`" in text for name in server.WHITELIST)
