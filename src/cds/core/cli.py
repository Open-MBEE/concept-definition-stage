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

    from cds.core.verify import VerifyResult

app = typer.Typer(
    name="cds",
    help="Concept Definition Stage — commit SEBoK/INCOSE Concept Definition canon to RDF.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def init(
    path: Annotated[
        Path | None,
        typer.Argument(help="Project directory to scaffold; defaults to the current directory."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option(help="Project name recorded in cds.toml; defaults to the directory name."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(help="Overwrite existing scaffolded files."),
    ] = False,
) -> None:
    """Scaffold a CDS data root here — cds.toml, data dirs, and the model-facing assets."""
    from cds.core.init import init_project

    result = init_project(path, name=name, force=force)
    for rel in result.created:
        typer.secho(f"  + {rel}", fg=typer.colors.GREEN)
    for rel in result.skipped:
        typer.secho(f"  · {rel} (exists, skipped)", fg=typer.colors.YELLOW)
    typer.secho(
        f"cds project ready at {result.root} "
        f"({len(result.created)} created, {len(result.skipped)} skipped).",
        fg=typer.colors.GREEN,
    )


@app.command()
def build() -> None:
    """Compile YAML term sources into the canonical ``concept-definition.ttl`` (deterministic)."""
    from cds.core.verify import verify as run_verify
    from cds.stages.concept_definition.build import (
        build_concept_definition_graph,
        write_concept_definition_ttl,
    )

    graph = build_concept_definition_graph()
    out = write_concept_definition_ttl(graph)
    typer.secho(f"built {out} ({len(graph)} triples)", fg=typer.colors.GREEN)

    # parsimony accounting (reference-vs-materialize). No external caches are configured (SysML is
    # anchored by equivalence axioms, not MIREOT-sliced), so every invoked external IRI is
    # reference-only; the budget/report wiring stays live for a future PROV-O/SKOS cache.
    from cds.core.parsimony import build_extracts

    _extracts, report = build_extracts(graph, sources={}, budgets={})
    budget = "within budget" if report.within_budget else "OVER BUDGET"
    typer.secho(
        f"parsimony: {len(report.referenced_only)} external IRIs referenced, "
        f"{len(report.materialized_iris)} materialized ({budget}).",
        fg=typer.colors.BLUE,
    )
    _report_and_exit(run_verify(graph))


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
    from cds.core.verify import SHAPES_DIR
    from cds.core.verify import verify as run_verify

    data = _load_turtle(graph) if graph is not None else _seed_graph()
    # waivers are first-class RDF — merge the operator's waiver graph into the data being verified
    waivers_path = waivers if waivers is not None else SHAPES_DIR.parent / "waivers.ttl"
    if waivers_path.exists():
        data.parse(waivers_path, format="turtle")
    _report_and_exit(run_verify(data))


def _report_and_exit(result: VerifyResult) -> None:
    """Print tri-severity findings and exit non-zero iff the gate failed (any unwaived T1)."""
    colour = {"T1": typer.colors.RED, "T2": typer.colors.YELLOW, "T3": typer.colors.BLUE}
    for f in result.findings:
        typer.secho(f"  [{f.tier}] {f.focus} — {f.message}", fg=colour[f.tier], err=True)
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
def render(
    text_license: Annotated[
        str,
        typer.Option(help="Report text license; non-SEBoK-compatible -> cite-only (no verbatim)."),
    ] = "CC-BY-NC-SA-4.0",
) -> None:
    """Render the scheme to a deterministic Typst -> PDF reference document (license-keyed View)."""
    from cds.core.render.typst import render_pdf, typst_document
    from cds.core.render.view import scheme_view
    from cds.core.workspace import find_data_root
    from cds.stages.concept_definition.build import build_concept_definition_graph

    view = scheme_view(
        build_concept_definition_graph(),
        title="Concept Definition Vocabulary",
        text_license=text_license,
    )
    # Write into the user's project when one is resolvable; otherwise the CDS repo (maintainer use).
    project = find_data_root()
    repo_views = Path(__file__).resolve().parents[3] / "views"
    views_dir = (project / "views") if project is not None else repo_views
    views_dir.mkdir(parents=True, exist_ok=True)
    typ = views_dir / "concept-definition.typ"
    typ.write_text(typst_document(view))
    pdf = render_pdf(view, views_dir / "concept-definition.pdf")
    mode = "verbatim canon" if view.renders_restricted_canon else "cite-only"
    typer.secho(f"rendered {pdf} ({mode}; text license {view.text_license})", fg=typer.colors.GREEN)


def _not_yet(command: str, slice_: str) -> int:
    typer.secho(
        f"`cds {command}` is not implemented yet (planned for {slice_}).",
        fg=typer.colors.YELLOW,
        err=True,
    )
    return 1


if __name__ == "__main__":
    app()
