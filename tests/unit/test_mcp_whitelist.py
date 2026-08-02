"""REQ-K1.1 / REQ-K1.2 — the MCP server serves ONLY the whitelist; no exec tool. (P1, red)"""
from cds.mcp import server


def test_manifest_equals_whitelist():
    assert sorted(server.list_tools()) == sorted(server.WHITELIST)


def test_no_exec_tool_present():
    assert server.FORBIDDEN.isdisjoint(set(server.list_tools()))
