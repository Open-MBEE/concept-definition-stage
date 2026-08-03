"""Splittability contract — import-direction + transport-neutrality guards.

The DAG (docs/architecture/factoring.md): ``core ← contracts ← {mcp, oracle}``;
``mcp ← facilitator``; siblings otherwise couple only via ``cds.contracts``. Transport SDKs
(``mcp``, ``fastapi``, ``uvicorn``) and LLM SDKs are lazy, in-function imports — module
level is forbidden so every subpackage imports (and autodocs) on a lean install, and each
could become its own distribution without code motion.

Only MODULE-LEVEL imports are checked; lazy in-function imports are the sanctioned seam.
"""
import ast
from pathlib import Path

SRC = Path(__file__).parents[2] / "src"

# rule key: path prefix (or exact file) under src/ -> forbidden import prefixes
RULES: dict[str, list[str]] = {
    "cds/core": ["cds.contracts", "cds.mcp", "cds.oracle", "cds.facilitator", "cds.app"],
    "cds/contracts": ["cds.mcp", "cds.oracle", "cds.facilitator", "cds.app",
                      "mcp", "fastapi", "uvicorn"],
    "cds/mcp/tools.py": ["mcp", "fastapi", "uvicorn", "cds.oracle", "cds.facilitator",
                         "cds.app"],
    "cds/mcp": ["fastapi", "uvicorn", "cds.oracle", "cds.facilitator", "cds.app"],
    "cds/oracle": ["mcp", "fastapi", "uvicorn", "cds.mcp", "cds.facilitator", "cds.app"],
    "cds/facilitator": ["mcp", "fastapi", "uvicorn", "anthropic", "instructor",
                        "cds.oracle", "cds.app"],
    "cds/app": [],  # P5 — no rules yet
}


def _module_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in tree.body:  # top level only — nested (lazy) imports are the seam
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def _forbidden(imported: str, prefix: str) -> bool:
    return imported == prefix or imported.startswith(prefix + ".")


def test_import_direction_dag() -> None:
    violations: list[str] = []
    for py in sorted(SRC.glob("cds/**/*.py")):
        rel = py.relative_to(SRC).as_posix()
        # most-specific rule wins (file rule over package rule)
        rules = [forbid for key, forbid in RULES.items()
                 if rel == key or rel.startswith(key + "/")]
        if rel in RULES:
            rules = [RULES[rel]]
        for forbid in rules:
            for imported in _module_level_imports(py):
                for prefix in forbid:
                    if _forbidden(imported, prefix):
                        violations.append(
                            f"{rel}: module-level import {imported!r} breaks the "
                            f"factoring rule forbidding {prefix!r}")
    assert not violations, "\n".join(violations)


def test_typechecking_imports_are_exempt_but_scoped() -> None:
    # TYPE_CHECKING blocks are allowed to reference siblings for annotations only;
    # they are not module-level ast.Import nodes in tree.body, so the guard above
    # naturally exempts them. This test pins that assumption.
    server = SRC / "cds/mcp/server.py"
    assert "TYPE_CHECKING" in server.read_text(encoding="utf-8")
    assert not any(_forbidden(i, "mcp") for i in _module_level_imports(server))
