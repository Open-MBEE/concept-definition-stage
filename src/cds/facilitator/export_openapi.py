"""Export the facilitator's OpenAPI spec — committed at ``docs/services/openapi-facilitator.json``.

Deterministic (sorted keys, sorted tool routes, indent 2, trailing newline);
``tests/unit/test_facilitator_api.py`` fails on drift. Regenerate with::

    uv run python -m cds.facilitator.export_openapi
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


def openapi_json() -> str:
    from cds.core.workspace import Project
    from cds.facilitator.server import build_app

    # The spec depends only on the registry, never on project contents — an ephemeral
    # scratch root keeps generation deterministic and side-effect free.
    with tempfile.TemporaryDirectory() as tmp:
        proj = Project(root=Path(tmp), base_iri="https://cds.example/spec/")
        proj.instances_dir.mkdir(parents=True)
        return json.dumps(build_app(proj).openapi(), sort_keys=True, indent=2) + "\n"


def main() -> None:
    repo_root = Path(__file__).parents[3]  # src/cds/facilitator/ -> repo
    out = repo_root / "docs" / "services" / "openapi-facilitator.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(openapi_json(), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
