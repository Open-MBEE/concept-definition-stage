"""Typer CLI surface for ``cds``.

The C (Controller) layer: tightly constrained authoring. Commands are skeletons in slice 1
and are implemented across later slices (build/verify/render). Pydantic write-scope
guardrails live in ``cds.core.model``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypeVar

import typer

_T = TypeVar("_T")

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
def synthesis(
    slug: Annotated[str, typer.Argument(help="Short id for the mapping (kebab-case).")],
    title: Annotated[str, typer.Option(help="Human title of the concept-definition mapping.")],
    description: Annotated[str, typer.Option(help="One-line description of the mapping.")] = "",
) -> None:
    """Create (or update) the mapping container — a ``cds:Synthesis`` (the integrated set)."""
    from cds.core.authoring import create_synthesis
    from cds.core.model.instances import Synthesis
    from cds.core.workspace import load_project

    project = load_project()
    syn = _validated(lambda: Synthesis(slug=slug, title=title, description=description))
    iri = create_synthesis(project, syn)
    typer.secho(f"synthesis {iri}", fg=typer.colors.GREEN)


@app.command()
def new(
    kind: Annotated[str, typer.Argument(help="Record kind (mission, goal, stakeholder, need, …).")],
    slug: Annotated[str, typer.Argument(help="Short id for this record (kebab-case).")],
    synthesis: Annotated[
        str | None, typer.Option(help="Slug of the parent mapping (cds:Synthesis).")
    ] = None,
    label: Annotated[str | None, typer.Option(help="Short name.")] = None,
    description: Annotated[str | None, typer.Option(help="The content statement.")] = None,
    for_stakeholder: Annotated[
        list[str] | None, typer.Option(help="need → stakeholder slug(s).")
    ] = None,
    serves_goal: Annotated[list[str] | None, typer.Option(help="need → goal slug(s).")] = None,
    refines: Annotated[list[str] | None, typer.Option(help="objective → goal slug(s).")] = None,
    addresses: Annotated[
        list[str] | None, typer.Option(help="goal → problem/opportunity slug(s).")
    ] = None,
    segment: Annotated[str | None, typer.Option(help="stakeholder segment/perspective.")] = None,
    interest: Annotated[str | None, typer.Option(help="stakeholder interest.")] = None,
    influence: Annotated[str | None, typer.Option(help="stakeholder influence.")] = None,
    cites: Annotated[list[str] | None, typer.Option(help="Source IRI(s) for provenance.")] = None,
    supersedes: Annotated[
        list[str] | None,
        typer.Option(help="Slug (same kind) or IRI of a record this one replaces."),
    ] = None,
    interactive: Annotated[
        bool, typer.Option(help="Prompt for label/description if omitted.")
    ] = False,
) -> None:
    """Author one instance record (typed by its vocabulary term) into the project."""
    from cds.core.model.instances import KIND_TERM, model_for_kind
    from cds.core.workspace import load_project

    if kind not in KIND_TERM:
        typer.secho(
            f"unknown kind {kind!r}; expected one of {', '.join(KIND_TERM)}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    if interactive:
        synthesis = synthesis or typer.prompt("synthesis (mapping slug)")
        label = label or typer.prompt("label (short name)")
        description = description or typer.prompt("description (the statement)")
    if synthesis is None:
        typer.secho("--synthesis is required (or use --interactive)",
                    fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    if label is None or description is None:
        typer.secho("--label and --description are required (or use --interactive)",
                    fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    project = load_project()
    fields: dict[str, object] = {
        "slug": slug,
        "kind": kind,
        "label": label,
        "description": description,
        "synthesis": synthesis,
        "cites": cites or [],
        "supersedes": [_resolve_ref(project.base_iri, kind, v) for v in (supersedes or [])],
        "for_stakeholder": for_stakeholder or [],
        "serves_goal": serves_goal or [],
        "refines": refines or [],
        "addresses": addresses or [],
        "segment": segment,
        "interest": interest,
        "influence": influence,
    }
    model = model_for_kind(kind)
    from cds.core.authoring import create_record

    rec = _validated(lambda: model.model_validate(fields))
    iri = create_record(project, rec)
    # echo the stored fields so an upsert/correction is visible (not just the IRI)
    typer.secho(f"{kind} {rec.slug} — {rec.label}", fg=typer.colors.GREEN)
    typer.echo(f"  {rec.description}")
    typer.echo(f"  {iri}")


park_app = typer.Typer(help="Parking-lot: capture out-of-scope ideas without derailing.",
                       no_args_is_help=True, add_completion=False)
queue_app = typer.Typer(help="Retrieval queue: track open unknowns (pending→provided→verified).",
                        no_args_is_help=True, add_completion=False)
app.add_typer(park_app, name="park")
app.add_typer(queue_app, name="queue")


@park_app.command("add")
def park_add(
    slug: Annotated[str, typer.Argument(help="Short id for the parked idea.")],
    label: Annotated[str, typer.Option(help="Short name of the idea.")],
    description: Annotated[str, typer.Option(help="What the idea is.")] = "",
    note: Annotated[str | None, typer.Option(help="Why it's parked / when to revisit.")] = None,
) -> None:
    """Park an out-of-scope idea so it isn't lost."""
    from cds.core.authoring import create_parked
    from cds.core.model.notes import ParkedItem
    from cds.core.workspace import load_project

    item = _validated(
        lambda: ParkedItem(slug=slug, label=label, description=description, note=note)
    )
    iri = create_parked(load_project(), item)
    typer.secho(f"parked {iri}", fg=typer.colors.GREEN)


@park_app.command("list")
def park_list() -> None:
    """List parked ideas."""
    from cds.core.authoring import list_parked
    from cds.core.workspace import load_project

    items = list_parked(load_project())
    if not items:
        typer.secho("(parking-lot empty)", fg=typer.colors.YELLOW)
    for slug, label in items:
        typer.echo(f"  {slug}: {label}")


@queue_app.command("add")
def queue_add(
    slug: Annotated[str, typer.Argument(help="Short id for the open unknown.")],
    question: Annotated[str, typer.Option(help="The open question to resolve later.")],
    description: Annotated[str, typer.Option(help="Context on the unknown.")] = "",
) -> None:
    """Add an open unknown to the retrieval queue (status starts 'pending')."""
    from cds.core.authoring import create_queue_item
    from cds.core.model.notes import RetrievalItem
    from cds.core.workspace import load_project

    item = _validated(
        lambda: RetrievalItem(slug=slug, question=question, description=description)
    )
    iri = create_queue_item(load_project(), item)
    typer.secho(f"queued {iri} (pending)", fg=typer.colors.GREEN)


@queue_app.command("set")
def queue_set(
    slug: Annotated[str, typer.Argument(help="Queue item id.")],
    status: Annotated[str, typer.Option(help="pending | provided | verified.")],
    locator: Annotated[str | None, typer.Option(help="Where the answer was found.")] = None,
) -> None:
    """Advance a queue item's status."""
    from cds.core.authoring import set_queue_status
    from cds.core.model.notes import RetrievalStatus
    from cds.core.workspace import load_project

    try:
        parsed = RetrievalStatus(status)
    except ValueError:
        typer.secho("status must be pending, provided, or verified", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from None
    try:
        set_queue_status(load_project(), slug, parsed, locator=locator)
    except KeyError:
        typer.secho(f"no queue item {slug!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from None
    typer.secho(f"{slug} → {parsed.value}", fg=typer.colors.GREEN)


@queue_app.command("list")
def queue_list() -> None:
    """List open unknowns and their status."""
    from cds.core.authoring import list_queue
    from cds.core.workspace import load_project

    items = list_queue(load_project())
    if not items:
        typer.secho("(retrieval queue empty)", fg=typer.colors.YELLOW)
    for slug, status, question in items:
        typer.echo(f"  [{status}] {slug}: {question}")


tension_app = typer.Typer(help="Record named conflicts between records (surfaced, not hidden).",
                          no_args_is_help=True, add_completion=False)
app.add_typer(tension_app, name="tension")


@tension_app.command("add")
def tension_add(
    slug: Annotated[str, typer.Argument(help="Short id for the tension.")],
    label: Annotated[str, typer.Option(help="Short name of the conflict.")],
    description: Annotated[str, typer.Option(help="What pulls against what, and why.")] = "",
    between: Annotated[
        list[str] | None, typer.Option(help="IRIs of the records in tension (repeatable).")
    ] = None,
) -> None:
    """Record a named tension between records (e.g. two needs that conflict)."""
    from cds.core.authoring import create_tension
    from cds.core.model.notes import Tension
    from cds.core.workspace import load_project

    item = _validated(
        lambda: Tension(slug=slug, label=label, description=description, between=between or [])
    )
    iri = create_tension(load_project(), item)
    typer.secho(f"tension {iri}", fg=typer.colors.GREEN)


@tension_app.command("resolve")
def tension_resolve(
    slug: Annotated[str, typer.Argument(help="Tension id to mark resolved.")],
) -> None:
    """Mark a tension resolved — it drops out of the compiled brief."""
    from cds.core.authoring import set_tension_status
    from cds.core.model.notes import TensionStatus
    from cds.core.workspace import load_project

    try:
        set_tension_status(load_project(), slug, TensionStatus.RESOLVED)
    except KeyError:
        typer.secho(f"no tension {slug!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from None
    typer.secho(f"{slug} → resolved", fg=typer.colors.GREEN)


@tension_app.command("rm")
def tension_rm(slug: Annotated[str, typer.Argument(help="Tension id to delete.")]) -> None:
    """Delete a tension."""
    from cds.core.authoring import remove_tension
    from cds.core.workspace import load_project

    _rm_or_exit(remove_tension(load_project(), slug), "tension", slug)


@park_app.command("rm")
def park_rm(slug: Annotated[str, typer.Argument(help="Parked-idea id to delete.")]) -> None:
    """Delete a parked idea."""
    from cds.core.authoring import remove_parked
    from cds.core.workspace import load_project

    _rm_or_exit(remove_parked(load_project(), slug), "parked", slug)


@queue_app.command("rm")
def queue_rm(slug: Annotated[str, typer.Argument(help="Queue-item id to delete.")]) -> None:
    """Delete a retrieval-queue item."""
    from cds.core.authoring import remove_queue_item
    from cds.core.workspace import load_project

    _rm_or_exit(remove_queue_item(load_project(), slug), "queue", slug)


def _rm_or_exit(removed: bool, kind: str, slug: str) -> None:
    if removed:
        typer.secho(f"removed {kind} {slug}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"no {kind} {slug!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)


@app.command(name="list")
def list_(
    kind: Annotated[str, typer.Argument(help="Record kind to list (mission, goal, need, …).")],
) -> None:
    """List the records of a kind (slug — label), for reviewing what's captured."""
    from cds.core.authoring import list_records
    from cds.core.model.instances import KIND_TERM
    from cds.core.workspace import load_project

    if kind not in KIND_TERM:
        typer.secho(f"unknown kind {kind!r}; expected one of {', '.join(KIND_TERM)}",
                    fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    items = list_records(load_project(), kind)
    if not items:
        typer.secho(f"(no {kind} records yet)", fg=typer.colors.YELLOW)
    for slug, label in items:
        typer.echo(f"  {slug}: {label}")


@app.command()
def show(
    kind: Annotated[str, typer.Argument(help="Record kind.")],
    slug: Annotated[str, typer.Argument(help="Record slug.")],
) -> None:
    """Show one record's stored fields — read-back for reflecting content to the human."""
    from cds.core.authoring import show_record
    from cds.core.workspace import load_project

    lines = show_record(load_project(), kind, slug)
    if lines is None:
        typer.secho(f"no {kind} {slug!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    for line in lines:
        typer.echo(line)


@app.command()
def rm(
    kind: Annotated[str, typer.Argument(help="Record kind.")],
    slug: Annotated[str, typer.Argument(help="Record slug.")],
) -> None:
    """Delete a record — the sanctioned way to retract, alongside re-authoring to correct."""
    from cds.core.authoring import remove_record
    from cds.core.workspace import load_project

    if remove_record(load_project(), kind, slug):
        typer.secho(f"removed {kind} {slug}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"no {kind} {slug!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)


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
    from cds.core.workspace import find_data_root

    in_project = False
    if graph is not None:
        data = _load_turtle(graph)
    elif find_data_root() is not None:
        # inside a user project: validate their authored instance graph + run conflict checks
        from cds.core.authoring import project_graph
        from cds.core.workspace import load_project

        data = project_graph(load_project())
        in_project = True
    else:
        data = _seed_graph()
    # waivers are first-class RDF — merge the operator's waiver graph into the data being verified
    waivers_path = waivers if waivers is not None else SHAPES_DIR.parent / "waivers.ttl"
    if waivers_path.exists():
        data.parse(waivers_path, format="turtle")
    _report_and_exit(run_verify(data, check_conflicts=in_project))


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


def _validated(factory: Callable[[], _T]) -> _T:
    """Build a Pydantic model, turning a validation error (e.g. a bad slug) into a clean exit."""
    from pydantic import ValidationError

    try:
        return factory()
    except ValidationError as exc:
        msg = exc.errors()[0].get("msg", str(exc))
        typer.secho(str(msg), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from None


def _resolve_ref(base: str, kind: str, value: str) -> str:
    """Resolve a supersedes reference: a full IRI as-is, else a same-kind slug under the project."""
    from cds.core.model.instances import record_iri

    return value if "://" in value else str(record_iri(base, kind, value))


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


@app.command()
def compile(
    output: Annotated[
        Path | None,
        typer.Option(help="Output path; defaults to <briefs>/concept-definition.md."),
    ] = None,
) -> None:
    """Compile the mapping to a deterministic, human-readable Markdown brief."""
    from cds.core.authoring import project_graph
    from cds.core.compile import compile_brief
    from cds.core.workspace import load_project

    project = load_project()
    md = compile_brief(project_graph(project), base=project.base_iri)
    out = output if output is not None else project.briefs_dir / "concept-definition.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    typer.secho(f"compiled {out}", fg=typer.colors.GREEN)


def main() -> None:
    """Console entry point — turns a missing-project error into a clean message, not a traceback."""
    from cds.core.workspace import CdsProjectNotFound

    try:
        app()
    except CdsProjectNotFound as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
