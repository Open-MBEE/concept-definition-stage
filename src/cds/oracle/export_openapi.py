"""Export the oracle's OpenAPI spec — committed at ``docs/services/openapi-oracle.json``.

Deterministic (sorted keys, indent 2, trailing newline); ``tests/unit/test_oracle_api.py``
fails on drift, the same discipline as the TTL determinism gate. Regenerate with::

    uv run python -m cds.oracle.export_openapi
"""

from __future__ import annotations

import json
from pathlib import Path


def openapi_json() -> str:
    from cds.oracle.app import build_app

    return json.dumps(build_app().openapi(), sort_keys=True, indent=2) + "\n"


def main() -> None:
    repo_root = Path(__file__).parents[3]  # src/cds/oracle/ -> repo
    out = repo_root / "docs" / "services" / "openapi-oracle.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(openapi_json(), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
