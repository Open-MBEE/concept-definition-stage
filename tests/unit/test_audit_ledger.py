"""D2 (live-QA 2026-08-02 @ bb2d4a7): the human-readable audit ledger.

The formal guarantee (hash chain, ``verify_chain()``) is machine-checkable but not
human-scannable: "most humans need a dashboard or a report." The ledger renders the
chain as a table, one row per event, each row carrying its own chain verdict, under an
overall banner, so scanning shows integrity at a glance.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cds.core.cli import app
from cds.mcp.provenance import AuditLog, render_ledger

runner = CliRunner()


def _log(tmp_path: Path) -> AuditLog:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append({"action": "tool", "tool": "cds_new", "status": "ok"})
    log.append({"action": "commit", "content_hash": "a" * 64,
                "approver": "https://example.org/z", "adds": 6, "revisions": 0,
                "supersessions": 0, "retractions": 0, "held": 0})
    log.append({"action": "commit", "content_hash": "a" * 64,
                "approver": "https://example.org/z", "adds": 0, "revisions": 0,
                "supersessions": 0, "retractions": 0, "held": 0})
    return log


def test_entries_carry_per_row_chain_verdicts(tmp_path: Path) -> None:
    entries = _log(tmp_path).entries()
    assert [e["seq"] for e in entries] == [0, 1, 2]
    assert all(e["chain_ok"] for e in entries)


def test_ledger_renders_intact_chain(tmp_path: Path) -> None:
    text = render_ledger(_log(tmp_path))
    assert "chain intact" in text.lower()
    assert "cds_new" in text and "aaaaaaaaaaaa" in text
    assert "+6" in text  # the change counts are scannable
    assert "—" not in text  # house style (U2)


def test_ledger_annotates_repeat_hash_rows(tmp_path: Path) -> None:
    """B2 follow-through: a no-op re-commit shares its hash with the real commit; the
    ledger says so instead of leaving a reader to wonder."""
    text = render_ledger(_log(tmp_path))
    assert "repeat" in text.lower()


def test_tampered_line_fails_its_row_and_the_banner(tmp_path: Path) -> None:
    log = _log(tmp_path)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    doctored = json.loads(lines[1])
    doctored["event"]["adds"] = 999
    lines[1] = json.dumps(doctored, sort_keys=True)
    log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    entries = log.entries()
    assert not entries[2]["chain_ok"]  # the successor's prev no longer matches
    text = render_ledger(log)
    assert "broken" in text.lower() or "fail" in text.lower()


def test_csv_export(tmp_path: Path) -> None:
    import csv
    import io

    text = render_ledger(_log(tmp_path), fmt="csv")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0][0] == "seq" and len(rows) == 4


def test_cli_audit_command(tmp_path: Path, monkeypatch: object) -> None:
    from cds.core.init import init_project

    init_project(tmp_path, name="demo")
    log = AuditLog(tmp_path / "concept-definition" / "audit.jsonl")
    log.append({"action": "commit", "content_hash": "b" * 64, "approver": "z",
                "adds": 1, "revisions": 0, "supersessions": 0, "retractions": 0,
                "held": 0})
    import os

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "chain intact" in result.output.lower()
        csv_out = runner.invoke(app, ["audit", "--format", "csv"])
        assert csv_out.exit_code == 0 and csv_out.output.startswith("seq")
    finally:
        os.chdir(cwd)


def test_cli_audit_without_a_ledger_says_so(tmp_path: Path) -> None:
    from cds.core.init import init_project

    init_project(tmp_path, name="demo")
    import os

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "no audit" in result.output.lower()
    finally:
        os.chdir(cwd)
