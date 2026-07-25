"""``cds init`` — scaffold a CDS data root in the *user's* repo.

This is the inversion of the old repo-coupling: instead of analysis accumulating inside the CDS
install, ``init`` lays a ``cds.toml`` marker + data directories into the user's own project and
vendors the model-facing assets (the ``CLAUDE.md`` contract, Claude settings, and any elicitation
skills) so an in-IDE model can act as Player 2. Nothing here touches the CDS install.

Idempotent: existing files are left untouched unless ``force=True``, and every action is reported so
the caller can show the user exactly what happened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cds.core.workspace import DATA_MARKER, package_dir


def _assets_dir() -> Path:
    return package_dir() / "assets"


#: (source under assets/, destination relative to project root); skills are globbed separately.
_VENDORED: tuple[tuple[str, str], ...] = (
    ("claude/CLAUDE.md", "CLAUDE.md"),
    ("claude/settings.json", ".claude/settings.json"),
)


@dataclass
class InitResult:
    """What ``init`` did, for transparent reporting."""

    root: Path
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def note(self, path: Path, *, existed: bool) -> None:
        rel = _rel(path, self.root)
        (self.skipped if existed else self.created).append(rel)


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _write(dest: Path, text: str, result: InitResult, *, force: bool) -> None:
    if dest.exists() and not force:
        result.note(dest, existed=True)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    result.note(dest, existed=False)


def _keep_dir(path: Path, result: InitResult, *, force: bool) -> None:
    gitkeep = path / ".gitkeep"
    _write(gitkeep, "", result, force=force)


def init_project(
    target: Path | None = None,
    *,
    name: str | None = None,
    force: bool = False,
) -> InitResult:
    """Scaffold a CDS data root at ``target`` (default cwd); returns a created/skipped report."""
    root = (target or Path.cwd()).resolve()
    root.mkdir(parents=True, exist_ok=True)
    result = InitResult(root=root)
    project_name = name or root.name

    # 1) the cds.toml marker (from the shipped template)
    template = (_assets_dir() / "scaffold" / "cds.toml").read_text(encoding="utf-8")
    _write(root / DATA_MARKER, template.format(name=project_name), result, force=force)

    # 2) data directories (instances + briefs), kept in git via .gitkeep
    _keep_dir(root / "concept-definition" / "instances", result, force=force)
    _keep_dir(root / "concept-definition" / "briefs", result, force=force)

    # 3) vendor the model-facing assets (contract, settings, skills)
    assets = _assets_dir()
    for src_rel, dest_rel in _VENDORED:
        src = assets / src_rel
        if src.is_file():
            _write(root / dest_rel, src.read_text(encoding="utf-8"), result, force=force)
    skills_src = assets / "claude" / "skills"
    if skills_src.is_dir():
        for skill in sorted(skills_src.glob("*.md")):
            _write(
                root / ".claude" / "skills" / skill.name,
                skill.read_text(encoding="utf-8"),
                result,
                force=force,
            )

    return result
