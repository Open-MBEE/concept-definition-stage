"""Typer CLI surface for ``cds``.

The C (Controller) layer: tightly constrained authoring. Commands are skeletons in slice 1
and are implemented across later slices (build/verify/render). Pydantic write-scope
guardrails live in ``cds.core.model``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from rdflib import Graph

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
def verify(
    graph: Annotated[
        Path | None,
        typer.Argument(help="Turtle file to validate; defaults to the v0.1 seed ASoT graph."),
    ] = None,
    waivers: Annotated[
        Path | None,
        typer.Option(help="Turtle waivers graph (cds:Waiver); defaults to ontology/waivers.ttl."),
    ] = None,
) -> None:
    """Run the SHACL tri-severity + construction-order checks; non-zero exit on Tier-1."""
    from cds.core.verify import SHAPES_DIR, Finding
    from cds.core.verify import verify as run_verify

    data = _load_turtle(graph) if graph is not None else _seed_graph()
    # waivers are first-class RDF — merge the operator's waiver graph into the data being verified
    waivers_path = waivers if waivers is not None else SHAPES_DIR.parent / "waivers.ttl"
    if waivers_path.exists():
        data.parse(waivers_path, format="turtle")
    result = run_verify(data)

    def _emit(f: Finding) -> None:
        colour = {"T1": typer.colors.RED, "T2": typer.colors.YELLOW, "T3": typer.colors.BLUE}
        typer.secho(f"  [{f.tier}] {f.focus} — {f.message}", fg=colour[f.tier], err=True)

    for finding in result.findings:
        _emit(finding)
    if result.passed:
        typer.secho(
            f"verify OK — {len(result.warnings)} warning(s), {len(result.infos)} lint.",
            fg=typer.colors.GREEN,
        )
        raise typer.Exit(0)
    typer.secho(
        f"verify FAILED — {len(result.violations)} Tier-1 violation(s).", fg=typer.colors.RED
    )
    raise typer.Exit(1)


def _load_turtle(path: Path) -> Graph:
    from rdflib import Graph

    g = Graph()
    g.parse(path, format="turtle")
    return g


def _seed_graph() -> Graph:
    """The v0.1 seed ASoT graph (registered authorities + held boundary objects)."""
    from cds.core.asot.rdf import to_graph
    from cds.stages.concept_definition.seed import seed_authorities, seed_sources

    return to_graph(authorities=seed_authorities(), sources=seed_sources())


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
