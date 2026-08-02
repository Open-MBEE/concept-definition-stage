"""Session staging — candidates land in a scratch DATA_ROOT, never canonical (ADR-5/ADR-9).

Staging is a **sparse overlay**: the scratch root starts empty, so absence-in-staging is
never a signal, and no prior session's records bleed in (LARP F-5). The session's read
model is :func:`union_graph` — the canonical **current view** with the staging graph laid
over it, staging winning per subject (copy-on-write shadowing). Canonical files are never
touched by any staging operation; the only crossing is the commit gate
(:mod:`cds.app.commit_gate`, K2).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from rdflib import Graph

from cds.core.authoring import project_graph
from cds.core.view import current_view
from cds.core.workspace import Project


def new_session_project(base_iri: str, *, root: Path | None = None) -> Project:
    """Create an EMPTY scratch :class:`Project` (temp DATA_ROOT) for one session.

    ``root`` overrides the location (tests); default is a fresh temp dir per session.
    """
    if root is None:
        root = Path(tempfile.mkdtemp(prefix="cds-session-"))
    root.mkdir(parents=True, exist_ok=True)
    project = Project(root=root, base_iri=base_iri)
    project.instances_dir.mkdir(parents=True, exist_ok=True)
    marker = project.config_path
    if not marker.exists():
        marker.write_text(
            f'[project]\nbase_iri = "{base_iri}"\n\n'
            "# scratch session staging (ADR-5): candidates only, never canonical\n",
            encoding="utf-8",
        )
    return project


def union_graph(staging: Project, canonical: Project | None) -> Graph:
    """The session read model: ``current_view(canonical) ∪ staging``, staging winning.

    A subject present in staging shadows the canonical subject entirely (its staged copy
    is the working truth); canonical history (superseded/retracted) stays out.
    """
    out = Graph()
    staged = project_graph(staging)
    staged_subjects = set(staged.subjects())
    if canonical is not None:
        for s, p, o in current_view(project_graph(canonical)):
            if s not in staged_subjects:
                out.add((s, p, o))
    for triple in staged:
        out.add(triple)
    return out
