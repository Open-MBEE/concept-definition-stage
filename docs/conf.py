"""Sphinx configuration for the cds documentation site.

Scientific-Python norms (NumFOCUS/OpenMBEE): MyST Markdown sources, the pydata-sphinx-theme, and
autodoc-driven API reference. Build locally with:

    uv pip install -e ".[docs]"
    sphinx-build -b html docs docs/_build/html
"""

from __future__ import annotations

from importlib.metadata import version as _pkg_version

project = "cds — Concept Definition Stage"
author = "Michael Zargham and cds contributors"
project_copyright = "2026, Open-MBEE"

try:
    release = _pkg_version("cds")
except Exception:  # pragma: no cover - docs may build before install
    release = "0.1.0"
version = release

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

myst_enable_extensions = ["colon_fence", "deflist", "linkify"]
autosummary_generate = True
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "testing/**"]

html_theme = "pydata_sphinx_theme"
html_title = "cds"
html_theme_options = {
    "github_url": "https://github.com/Open-MBEE/concept-definition-stage",
    "show_prev_next": False,
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "rdflib": ("https://rdflib.readthedocs.io/en/stable/", None),
}

# MyST: treat .md as the primary source; keep .rst working too.
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
