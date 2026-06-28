"""Slice 1 smoke tests: the package imports and the CLI is wired."""

from __future__ import annotations

from typer.testing import CliRunner

import cds
from cds.core.cli import app

runner = CliRunner()


def test_version_present() -> None:
    assert cds.__version__ == "0.1.0"


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Concept Definition Stage" in result.output


def test_core_commands_are_registered() -> None:
    # build (slice 6), verify (slice 4), render (slice 8) are all implemented now
    help_output = runner.invoke(app, ["--help"]).output
    for command in ("build", "verify", "render"):
        assert command in help_output
