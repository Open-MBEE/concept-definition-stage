"""Workspace roots — the two-root split that lets ``cds`` write into a *user's* repo.

CDS ships as a package a user installs (editable, via ``uv``) into their own project. Two distinct
roots follow from that, and conflating them is the coupling this module removes:

* **TOOL_ROOT** — the read-only *canon* that ships **inside the package** (SHACL shapes, the
  compiled ``cds-core`` / ``concept-definition`` vocabularies, waivers). Resolved via the installed
  ``cds`` package location, so it works under both an editable install (source tree) and a built
  wheel. Never written to at author-time.
* **DATA_ROOT** — the user's *ledger*: where their concept-definition mapping (instances + briefs)
  accumulates. This is the user's own repo, discovered from a ``cds.toml`` marker (or the
  ``CDS_PROJECT`` env var / an explicit path), **not** the CDS clone.

Every graph read/write funnels through the helpers here — the single I/O choke point reserved for a
future remote (Flexo/MMS) backend and an eventual pyoxigraph store (see ROADMAP: performance).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import cds

#: Marker file that identifies a user's CDS project (written by ``cds init``).
DATA_MARKER = "cds.toml"
#: Environment override for the data root (absolute path to a project dir).
DATA_ROOT_ENV = "CDS_PROJECT"


# --------------------------------------------------------------------------- TOOL_ROOT (canon)


@cache
def package_dir() -> Path:
    """The installed ``cds`` package directory (``src/cds`` under an editable install)."""
    return Path(cds.__file__).resolve().parent


def canon_dir() -> Path:
    """The packaged, read-only canon directory (shipped ontology + shapes)."""
    return package_dir() / "ontology"


def shapes_dir() -> Path:
    """The packaged SHACL shapes directory (used by ``cds verify``)."""
    return canon_dir() / "shapes"


def core_ttl_path() -> Path:
    """The committed ``cds-core.ttl`` vocabulary artifact (packaged)."""
    return canon_dir() / "cds-core.ttl"


def concept_definition_ttl_path() -> Path:
    """The committed ``concept-definition.ttl`` vocabulary artifact (packaged)."""
    return canon_dir() / "concept-definition.ttl"


def waivers_path() -> Path:
    """The packaged default waivers graph."""
    return canon_dir() / "waivers.ttl"


# --------------------------------------------------------------------------- DATA_ROOT (user repo)


class CdsProjectNotFound(RuntimeError):
    """Raised when no ``cds.toml`` data root can be resolved — the user must run ``cds init``."""


def find_data_root(start: Path | None = None) -> Path | None:
    """Resolve the user's project root, or ``None`` if there isn't one.

    Precedence: ``CDS_PROJECT`` env var → nearest ancestor containing ``cds.toml`` (from ``start``,
    defaulting to the current working directory).
    """
    env = os.environ.get(DATA_ROOT_ENV)
    if env:
        return Path(env).expanduser().resolve()
    cur = (start or Path.cwd()).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / DATA_MARKER).is_file():
            return candidate
    return None


def data_root(explicit: Path | None = None, *, start: Path | None = None) -> Path:
    """The user's project root; raises :class:`CdsProjectNotFound` if none is resolvable."""
    if explicit is not None:
        return explicit.expanduser().resolve()
    root = find_data_root(start=start)
    if root is None:
        raise CdsProjectNotFound(
            f"no {DATA_MARKER} found in the current directory or any parent. "
            "Run `cds init` in your project first."
        )
    return root


@dataclass(frozen=True)
class Project:
    """A resolved user project: its root and the layout read from ``cds.toml``.

    Paths are derived, not stored, so a moved/renamed project stays consistent.
    """

    root: Path
    base_iri: str = "https://cds.example/project/"
    instances_subdir: str = "concept-definition/instances"
    briefs_subdir: str = "concept-definition/briefs"

    @property
    def instances_dir(self) -> Path:
        return self.root / self.instances_subdir

    @property
    def briefs_dir(self) -> Path:
        return self.root / self.briefs_subdir

    @property
    def config_path(self) -> Path:
        return self.root / DATA_MARKER


def load_project(explicit: Path | None = None, *, start: Path | None = None) -> Project:
    """Resolve the user's project and read its ``cds.toml`` layout (falling back to defaults)."""
    root = data_root(explicit, start=start)
    cfg: dict[str, object] = {}
    marker = root / DATA_MARKER
    if marker.is_file():
        cfg = tomllib.loads(marker.read_text(encoding="utf-8"))
    raw_layout = cfg.get("layout")
    layout: dict[str, object] = raw_layout if isinstance(raw_layout, dict) else {}
    raw_project = cfg.get("project")
    project_cfg: dict[str, object] = raw_project if isinstance(raw_project, dict) else {}
    default_base = f"https://cds.example/{root.name}/"
    return Project(
        root=root,
        base_iri=str(project_cfg.get("base_iri", default_base)),
        instances_subdir=str(layout.get("instances", "concept-definition/instances")),
        briefs_subdir=str(layout.get("briefs", "concept-definition/briefs")),
    )
