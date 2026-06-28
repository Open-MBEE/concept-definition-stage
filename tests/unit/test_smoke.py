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


def test_unimplemented_commands_exit_nonzero() -> None:
    for command in ("build", "render"):  # verify is implemented in slice 4
        result = runner.invoke(app, [command])
        assert result.exit_code == 1
