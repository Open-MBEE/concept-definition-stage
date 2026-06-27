"""Typer CLI surface for ``cds``.

The C (Controller) layer: tightly constrained authoring. Commands are skeletons in slice 1
and are implemented across later slices (build/verify/render). Pydantic write-scope
guardrails live in ``cds.core.model``.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="cds",
    help="Concept Definition Stage — commit SEBoK/INCOSE Concept Definition canon to RDF.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def build() -> None:
    """Compile YAML term sources into the canonical ``concept-definition.ttl`` (deterministic)."""
    raise typer.Exit(_not_yet("build", "slice 6"))


@app.command()
def verify() -> None:
    """Run the SHACL tri-severity + construction-order checks; non-zero exit on Tier-1."""
    raise typer.Exit(_not_yet("verify", "slice 4"))


@app.command()
def render() -> None:
    """Render the synthesis to a deterministic Typst -> PDF reference document."""
    raise typer.Exit(_not_yet("render", "slice 8"))


def _not_yet(command: str, slice_: str) -> int:
    typer.secho(
        f"`cds {command}` is not implemented yet (planned for {slice_}).",
        fg=typer.colors.YELLOW,
        err=True,
    )
    return 1


if __name__ == "__main__":
    app()
